from datetime import datetime, timedelta
from typing import Optional
import random
import string
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db, settings
from models import User, EmailVerification
from scheduler import send_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, email: str, password: str) -> User:
    hashed_password = get_password_hash(password)
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def generate_verification_code(length: int = 6) -> str:
    """生成指定长度的随机验证码"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


def send_verification_email(email: str, code: str) -> None:
    """发送验证码邮件"""
    subject = "📧 Daily Digest 邮箱验证码"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h1 style="color: #2563eb;">Daily Digest 注册验证码</h1>
        <p>您好，</p>
        <p>感谢您注册 Daily Digest！</p>
        <p>您的验证码是：<strong style="font-size: 24px; color: #2563eb;">{code}</strong></p>
        <p>验证码有效期为 <strong>5分钟</strong>，请尽快完成验证。</p>
        <p>如果您没有请求此验证码，请忽略此邮件。</p>
        <br>
        <p>祝您使用愉快！</p>
        <p>Daily Digest Team</p>
    </body>
    </html>
    """
    send_email(email, subject, html_body)


def create_verification_code(db: Session, email: str) -> str:
    """创建并发送验证码"""
    # 检查是否已有验证码记录
    existing = db.query(EmailVerification).filter(EmailVerification.email == email).first()
    if existing:
        # 删除旧验证码
        db.delete(existing)
        db.commit()
    
    # 生成新验证码
    code = generate_verification_code()
    
    # 计算过期时间（5分钟后）
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # 创建新的验证码记录
    verification = EmailVerification(
        email=email,
        verification_code=code,
        expires_at=expires_at
    )
    
    db.add(verification)
    db.commit()
    
    # 发送验证码邮件
    send_verification_email(email, code)
    
    return code


def verify_verification_code(db: Session, email: str, code: str) -> bool:
    """验证验证码是否有效"""
    # 查找验证码记录
    verification = db.query(EmailVerification).filter(EmailVerification.email == email).first()
    
    if not verification:
        return False
    
    # 检查验证码是否过期
    if datetime.utcnow() > verification.expires_at:
        # 删除过期的验证码
        db.delete(verification)
        db.commit()
        return False
    
    # 检查验证码是否匹配
    if verification.verification_code == code:
        # 验证成功，删除验证码
        db.delete(verification)
        db.commit()
        return True
    
    return False


def send_reset_password_email(email: str, code: str) -> None:
    """发送重置密码验证码邮件"""
    subject = "🔒 Daily Digest 密码重置验证码"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h1 style="color: #2563eb;">Daily Digest 密码重置</h1>
        <p>您好，</p>
        <p>您请求重置 Daily Digest 账号的密码。</p>
        <p>您的重置密码验证码是：<strong style="font-size: 24px; color: #2563eb;">{code}</strong></p>
        <p>验证码有效期为 <strong>5分钟</strong>，请尽快完成密码重置。</p>
        <p>如果您没有请求此验证码，请忽略此邮件，您的账号安全不会受到影响。</p>
        <br>
        <p>祝您使用愉快！</p>
        <p>Daily Digest Team</p>
    </body>
    </html>
    """
    send_email(email, subject, html_body)


def create_reset_password_code(db: Session, email: str) -> str:
    """创建并发送重置密码验证码"""
    # 检查用户是否存在
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered"
        )
    
    # 检查是否已有验证码记录
    existing = db.query(EmailVerification).filter(EmailVerification.email == email).first()
    if existing:
        # 删除旧验证码
        db.delete(existing)
        db.commit()
    
    # 生成新验证码
    code = generate_verification_code()
    
    # 计算过期时间（5分钟后）
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # 创建新的验证码记录
    verification = EmailVerification(
        email=email,
        verification_code=code,
        expires_at=expires_at
    )
    
    db.add(verification)
    db.commit()
    
    # 发送验证码邮件
    send_reset_password_email(email, code)
    
    return code


def update_user_password(db: Session, email: str, new_password: str) -> User:
    """更新用户密码"""
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 更新密码
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(user)
    
    return user

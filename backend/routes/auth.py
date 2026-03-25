from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from models import UserCreate, UserLogin, UserResponse, Token
from models import EmailVerification
from auth import (
    create_user, 
    authenticate_user, 
    create_access_token, 
    get_user_by_email,
    get_current_active_user,
    create_verification_code,
    verify_verification_code,
    create_reset_password_code,
    update_user_password
)
from models import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Pydantic models for verification code
class VerificationRequest(BaseModel):
    email: str


class VerificationCodeVerify(BaseModel):
    email: str
    code: str
    
    # 使用模型配置允许额外字段
    class Config:
        extra = "allow"  # 允许额外字段


# Pydantic models for password reset
class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
    verification_code: str = None  # 兼容前端的字段名（别名）
    
    def __init__(self, **data):
        super().__init__(**data)
        # 如果提供了 verification_code 但没有 code，则使用 verification_code
        if self.verification_code and not self.code:
            self.code = self.verification_code


@router.post("/send-verification-code")
async def send_verification_code(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """Send verification code to email"""
    # Check if user already exists
    existing_user = get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create and send verification code
    try:
        create_verification_code(db, request.email)
        return {"message": "Verification code sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification code: {str(e)}"
        )


@router.post("/verify-code")
async def verify_code(
    request: VerificationCodeVerify,
    db: Session = Depends(get_db)
):
    """Verify email verification code"""
    # Check if user already exists
    existing_user = get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verify code
    is_valid = verify_verification_code(db, request.email, request.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    return {"message": "Verification successful"}


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Note: Email verification should be done before registration
    # The /verify-code endpoint removes the verification record upon success
    # So if we reach here, the email should already be verified
    # We don't need to check verification record here as it's already deleted after verification
    
    # Create new user
    user = create_user(db, user_data.email, user_data.password)
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    from datetime import datetime
    
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.put("/me/email-notifications")
async def update_email_notifications(
    enabled: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Toggle email notifications"""
    current_user.email_notifications = enabled
    db.commit()
    return {"email_notifications": enabled}


@router.post("/send-reset-password-code")
async def send_reset_password_code(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """Send reset password verification code"""
    try:
        create_reset_password_code(db, request.email)
        return {"message": "Reset password code sent successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send reset password code: {str(e)}"
        )


@router.post("/verify-reset-password-code")
async def verify_reset_password_code(
    request: VerificationCodeVerify,
    db: Session = Depends(get_db)
):
    """Verify reset password code"""
    # Verify code - the create_reset_password_code function already checks if user exists
    # and we just need to verify the code is valid
    is_valid = verify_verification_code(db, request.email, request.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    return {"message": "Verification successful"}


@router.post("/reset-password")
async def reset_password(
    request: Request,
    db: Session = Depends(get_db)
):
    """Reset user password（兼容 verification_code 字段）"""
    # 手动解析 JSON 请求体，支持 verification_code 字段
    try:
        body = await request.json()
        email = body.get("email")
        code = body.get("code") or body.get("verification_code")
        new_password = body.get("new_password")
        
        if not email or not code or not new_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="email, code (or verification_code), and new_password are required"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request body: {str(e)}"
        )
    
    # Verify code - this will also ensure the user exists and the code is valid
    is_valid = verify_verification_code(db, email, code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Reset password
    try:
        update_user_password(db, email, new_password)
        # Generate access token for automatic login
        access_token = create_access_token(data={"sub": email})
        return {"message": "Password reset successfully", "access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )


# ==================== 前端兼容路由（别名）====================

@router.post("/resend-verification")
async def resend_verification_alias(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """重发注册验证码（/send-verification-code 的别名，用于已注册但未验证的用户）"""
    # 对于已注册但未验证的用户，不检查用户是否存在
    try:
        create_verification_code(db, request.email)
        return {"message": "Verification code sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification code: {str(e)}"
        )


@router.post("/verify-email")
async def verify_email_alias(
    request: Request,
    db: Session = Depends(get_db)
):
    """验证邮箱（/verify-code 的别名，兼容 verification_code 字段）"""
    # 手动解析 JSON 请求体，支持 verification_code 字段
    try:
        body = await request.json()
        email = body.get("email")
        code = body.get("code") or body.get("verification_code")
        
        if not email or not code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="email and code (or verification_code) are required"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request body: {str(e)}"
        )
    
    # Check if user already exists
    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verify code
    is_valid = verify_verification_code(db, email, code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    return {"message": "Verification successful"}


@router.post("/forgot-password")
async def forgot_password_alias(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """忘记密码（/send-reset-password-code 的别名）"""
    return await send_reset_password_code(request, db)


@router.put("/profile")
async def update_profile(
    enabled: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户配置（目前仅支持 email_notifications 开关）"""
    return await update_email_notifications(enabled, current_user, db)

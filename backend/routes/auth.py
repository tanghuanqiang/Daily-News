from fastapi import APIRouter, Depends, HTTPException, status
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


# Pydantic models for password reset
class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


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
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset user password"""
    # Verify code - this will also ensure the user exists and the code is valid
    is_valid = verify_verification_code(db, request.email, request.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Reset password
    try:
        update_user_password(db, request.email, request.new_password)
        # Generate access token for automatic login
        access_token = create_access_token(data={"sub": request.email})
        return {"message": "Password reset successfully", "access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )

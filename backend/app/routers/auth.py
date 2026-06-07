"""
Authentication and email verification API.

8주차 최종 기능에서 TMI/제보 등록은 인증된 사용자만 가능.
JWT 발급, 이메일 인증, 관리자 권한 판별의 기준점.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import EmailVerification, User
from app.schemas.auth import (
    AuthTokenResponse,
    EmailVerificationCheckRequest,
    EmailVerificationCheckResponse,
    EmailVerificationRequest,
    EmailVerificationRequestResponse,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.users import UserResponse
from app.security import (
    create_access_token,
    decode_access_token,
    expires_at_text,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    is_dankook_email,
    is_expired,
    new_id,
    utc_now_text,
    verify_code_hash,
    verify_password,
)
from app.services.email_sender import send_verification_email


router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # 모든 보호 API는 JWT의 sub 값을 user_id로 해석해 현재 사용자 복원.
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"errorCode": "INVALID_TOKEN", "message": "유효하지 않은 인증 토큰입니다."},
        )
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"errorCode": "USER_NOT_FOUND", "message": "사용자를 찾을 수 없습니다."},
        )
    return user


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # 관리자 이메일은 환경변수 ADMIN_EMAILS로만 승격. 클라이언트 요청값으로 role을 받지 않음.
    email = request.email.lower()
    if settings.enforce_dankook_email and not is_dankook_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errorCode": "DANKOOK_EMAIL_REQUIRED", "message": "단국대 이메일만 가입할 수 있습니다."},
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"errorCode": "EMAIL_ALREADY_REGISTERED", "message": "이미 가입된 이메일입니다."},
        )

    user = User(
        user_id=new_id("USER"),
        email=email,
        password_hash=hash_password(request.password),
        nickname=request.nickname,
        email_verified=False,
        role="ADMIN" if email in settings.admin_email_set else "USER",
        created_at=utc_now_text(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.user_id)
    return AuthTokenResponse(accessToken=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthTokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"errorCode": "INVALID_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다."},
        )

    token = create_access_token(user.user_id)
    return AuthTokenResponse(accessToken=token, user=UserResponse.model_validate(user))


@router.post("/email/request", response_model=EmailVerificationRequestResponse)
def request_email_verification(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    # 인증코드는 원문을 DB에 저장하지 않고 hash만 저장.
    # SMTP 설정이 없으면 개발 편의를 위해 console delivery로 code를 응답에 포함.
    email = request.email.lower()
    if settings.enforce_dankook_email and not is_dankook_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errorCode": "DANKOOK_EMAIL_REQUIRED", "message": "단국대 이메일만 인증할 수 있습니다."},
        )

    code = generate_verification_code()
    verification = EmailVerification(
        verification_id=new_id("EMAIL"),
        email=email,
        code_hash=hash_verification_code(email, code),
        expires_at=expires_at_text(settings.email_verification_expire_minutes),
        verified_at=None,
        attempt_count=0,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)

    delivery = send_verification_email(email, code, settings.email_verification_expire_minutes)
    dev_code = code if delivery.delivery_mode == "console" else None
    return EmailVerificationRequestResponse(
        verificationId=verification.verification_id,
        email=email,
        expiresAt=verification.expires_at,
        deliveryMode=delivery.delivery_mode,
        devCode=dev_code,
    )


@router.post("/email/verify", response_model=EmailVerificationCheckResponse)
def verify_email(request: EmailVerificationCheckRequest, db: Session = Depends(get_db)):
    # 가장 최근의 미검증 인증 요청만 검사. 오래된 인증코드 재사용 방지 흐름.
    email = request.email.lower()
    verification = (
        db.query(EmailVerification)
        .filter(EmailVerification.email == email, EmailVerification.verified_at.is_(None))
        .order_by(EmailVerification.expires_at.desc())
        .first()
    )
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "VERIFICATION_NOT_FOUND", "message": "인증 요청을 찾을 수 없습니다."},
        )
    if is_expired(verification.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errorCode": "VERIFICATION_EXPIRED", "message": "인증 코드가 만료되었습니다."},
        )
    if verification.attempt_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"errorCode": "TOO_MANY_ATTEMPTS", "message": "인증 시도 횟수를 초과했습니다."},
        )

    verification.attempt_count += 1
    if not verify_code_hash(email, request.code, verification.code_hash):
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errorCode": "INVALID_VERIFICATION_CODE", "message": "인증 코드가 올바르지 않습니다."},
        )

    verification.verified_at = utc_now_text()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.email_verified = True
    db.commit()
    if user:
        db.refresh(user)

    return EmailVerificationCheckResponse(
        email=email,
        verified=True,
        user=UserResponse.model_validate(user) if user else None,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(_get_current_user)):
    return UserResponse.model_validate(current_user)


def get_current_user(current_user: User = Depends(_get_current_user)) -> User:
    return current_user


def require_verified_user(current_user: User = Depends(_get_current_user)) -> User:
    # TMI/제보 데이터 품질을 위해 이메일 인증 통과 사용자만 등록 허용.
    if not current_user.email_verified and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"errorCode": "EMAIL_VERIFICATION_REQUIRED", "message": "이메일 인증 후 사용할 수 있습니다."},
        )
    return current_user


def require_admin_user(current_user: User = Depends(_get_current_user)) -> User:
    # 관리자 API는 승인/반려 상태를 바꾸므로 role 명시 검사.
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"errorCode": "ADMIN_REQUIRED", "message": "관리자 권한이 필요합니다."},
        )
    return current_user

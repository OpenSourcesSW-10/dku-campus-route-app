"""
Authentication API.

8주차 최종 기능에서 TMI/제보 등록은 인증된 사용자만 가능.
JWT 발급, 현재 사용자 조회, 관리자 권한 판별의 기준점.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.users import UserResponse
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_id,
    utc_now_text,
    verify_password,
)


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


def _normalize_student_id(student_id: str) -> str:
    # 프론트는 숫자만 입력하도록 제한하지만, 백엔드에서도 한 번 더 정규화.
    return "".join(char for char in student_id.strip() if char.isdigit())


def _student_email(student_id: str) -> str:
    # 기존 users.email NOT NULL/UNIQUE 구조와 호환하기 위한 내부용 가상 이메일.
    return f"{student_id}@student.dku.local"


def _to_user_response(user: User) -> UserResponse:
    # Pydantic field명은 프론트 계약에 맞춰 studentId 유지.
    return UserResponse(
        user_id=user.user_id,
        studentId=user.student_id,
        nickname=user.nickname,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # 프론트 회원가입 폼 기준: 학번 + 비밀번호만 받음.
    student_id = _normalize_student_id(request.studentId)
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errorCode": "INVALID_STUDENT_ID", "message": "학번은 숫자만 입력할 수 있습니다."},
        )

    email = _student_email(student_id)
    existing_user = db.query(User).filter((User.student_id == student_id) | (User.email == email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"errorCode": "STUDENT_ID_ALREADY_REGISTERED", "message": "이미 가입된 학번입니다."},
        )

    user = User(
        user_id=new_id("USER"),
        student_id=student_id,
        email=email,
        password_hash=hash_password(request.password),
        nickname=student_id,
        role="ADMIN" if student_id in settings.admin_student_id_set else "USER",
        created_at=utc_now_text(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.user_id)
    return AuthTokenResponse(accessToken=token, user=_to_user_response(user))


@router.post("/login", response_model=AuthTokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    student_id = _normalize_student_id(request.studentId)
    user = db.query(User).filter(User.student_id == student_id).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"errorCode": "INVALID_CREDENTIALS", "message": "학번 또는 비밀번호가 올바르지 않습니다."},
        )

    token = create_access_token(user.user_id)
    return AuthTokenResponse(accessToken=token, user=_to_user_response(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(_get_current_user)):
    return _to_user_response(current_user)


def get_current_user(current_user: User = Depends(_get_current_user)) -> User:
    return current_user


def require_authenticated_user(current_user: User = Depends(_get_current_user)) -> User:
    # 추가 인증 절차 없음. JWT가 유효한 로그인 사용자면 등록 API 사용 가능.
    return current_user


def require_admin_user(current_user: User = Depends(_get_current_user)) -> User:
    # 관리자 API는 승인/반려 상태를 바꾸므로 role 명시 검사.
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"errorCode": "ADMIN_REQUIRED", "message": "관리자 권한이 필요합니다."},
        )
    return current_user

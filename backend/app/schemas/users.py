from app.schemas.common import OrmModel


class UserResponse(OrmModel):
    # 사용자 공개 정보 응답이다.
    user_id: str
    email: str
    nickname: str
    email_verified: bool
    role: str
    created_at: str | None = None


class EmailVerificationResponse(OrmModel):
    # 이메일 인증 요청/검증 상태 응답이다.
    verification_id: str
    email: str
    expires_at: str
    verified_at: str | None = None
    attempt_count: int

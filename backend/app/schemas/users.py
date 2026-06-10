from app.schemas.common import OrmModel


class UserResponse(OrmModel):
    # 사용자 공개 정보 응답.
    user_id: str
    studentId: str | None = None
    nickname: str
    role: str
    created_at: str | None = None

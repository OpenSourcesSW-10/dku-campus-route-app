from pydantic import BaseModel, Field

from app.schemas.users import UserResponse


class RegisterRequest(BaseModel):
    studentId: str = Field(min_length=1, max_length=20, pattern=r"^\d+$")
    password: str = Field(min_length=8, max_length=20)


class LoginRequest(BaseModel):
    studentId: str = Field(min_length=1, max_length=20, pattern=r"^\d+$")
    password: str = Field(min_length=8, max_length=20)


class AuthTokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: UserResponse

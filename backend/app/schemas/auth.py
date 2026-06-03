from pydantic import BaseModel, EmailStr, Field

from app.schemas.users import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nickname: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationCheckRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class AuthTokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: UserResponse


class EmailVerificationRequestResponse(BaseModel):
    verificationId: str
    email: EmailStr
    expiresAt: str
    deliveryMode: str
    devCode: str | None = None


class EmailVerificationCheckResponse(BaseModel):
    email: EmailStr
    verified: bool
    user: UserResponse | None = None

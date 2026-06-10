from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # 원문 비밀번호는 저장하지 않고 bcrypt 해시만 DB에 저장.
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    # 로그인 시 입력 비밀번호가 저장된 bcrypt 해시와 일치하는지 확인.
    return password_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    # JWT payload의 sub에는 사용자 ID 저장. 이후 인증된 사용자 조회에 사용.
    expires_at = utc_now() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    # 유효한 JWT이면 사용자 ID 반환, 만료/변조된 토큰이면 None 반환.
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def new_id(prefix: str) -> str:
    # 테이블별 ID를 읽기 쉽게 prefix와 UUID 조합으로 생성.
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat()

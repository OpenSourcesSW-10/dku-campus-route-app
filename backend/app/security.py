from datetime import datetime, timedelta, timezone
from secrets import randbelow
from uuid import uuid4
import hashlib
import hmac

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def is_dankook_email(email: str) -> bool:
    # 7주차 회원가입 기능에서 단국대 이메일만 허용하기 위한 검사이다.
    return email.lower().endswith("@dankook.ac.kr")


def hash_password(password: str) -> str:
    # 원문 비밀번호는 저장하지 않고 bcrypt 해시만 DB에 저장한다.
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    # 로그인 시 입력 비밀번호가 저장된 bcrypt 해시와 일치하는지 확인한다.
    return password_context.verify(password, password_hash)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    # JWT payload의 sub에는 사용자 ID를 넣어 이후 인증된 사용자 조회에 사용한다.
    expires_at = utc_now() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    # 유효한 JWT이면 사용자 ID를 반환하고, 만료/변조된 토큰이면 None을 반환한다.
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def generate_verification_code() -> str:
    # 이메일 인증코드는 사용자가 입력하기 쉽게 6자리 숫자로 만든다.
    return f"{randbelow(1_000_000):06d}"


def hash_verification_code(email: str, code: str) -> str:
    # 인증코드도 원문을 저장하지 않도록 이메일, 코드, 서버 비밀키를 함께 해시한다.
    message = f"{email.lower()}:{code}".encode("utf-8")
    return hmac.new(settings.jwt_secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_code_hash(email: str, code: str, code_hash: str) -> bool:
    # 타이밍 공격을 줄이기 위해 compare_digest로 해시 문자열을 비교한다.
    expected = hash_verification_code(email, code)
    return hmac.compare_digest(expected, code_hash)


def new_id(prefix: str) -> str:
    # 테이블별 ID를 읽기 쉽게 prefix와 UUID 조합으로 만든다.
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat()


def expires_at_text(minutes: int) -> str:
    return (utc_now() + timedelta(minutes=minutes)).isoformat()


def is_expired(expires_at: str) -> bool:
    try:
        expires = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < utc_now()

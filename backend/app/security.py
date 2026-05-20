"""
Week 3 security placeholder.

Authentication, email verification, password hashing, and JWT issuance are
planned for week 7. This file exists now so later auth code has a stable home.
"""


def is_dankook_email(email: str) -> bool:
    # 7주차 회원가입 기능에서 단국대 이메일만 허용하기 위한 검사이다.
    return email.lower().endswith("@dankook.ac.kr")

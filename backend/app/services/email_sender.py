from email.message import EmailMessage
import smtplib

from app.config import settings


class EmailSendResult:
    def __init__(self, delivery_mode: str, delivered: bool) -> None:
        self.delivery_mode = delivery_mode
        self.delivered = delivered


def send_verification_email(to_email: str, code: str, expires_minutes: int) -> EmailSendResult:
    # SMTP 설정이 없으면 로컬/시연 환경에서 콘솔 출력 방식으로 인증코드 확인.
    if not _smtp_enabled():
        print(f"[DKU MAP EMAIL VERIFICATION] to={to_email} code={code} expires={expires_minutes}m")
        return EmailSendResult(delivery_mode="console", delivered=False)

    message = EmailMessage()
    message["Subject"] = "[DKU MAP] 이메일 인증 코드"
    message["From"] = settings.smtp_from_email or settings.smtp_username
    message["To"] = to_email
    message.set_content(
        "\n".join(
            [
                "단국맵 이메일 인증 코드입니다.",
                "",
                f"인증 코드: {code}",
                f"만료 시간: {expires_minutes}분",
                "",
                "본인이 요청하지 않았다면 이 메일을 무시해 주세요.",
            ]
        )
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

    return EmailSendResult(delivery_mode="smtp", delivered=True)


def _smtp_enabled() -> bool:
    return (
        settings.email_delivery_mode.lower() == "smtp"
        and bool(settings.smtp_host)
        and bool(settings.smtp_from_email or settings.smtp_username)
    )

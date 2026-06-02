import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from config.settings import (
    PASSWORD_RESET_URL,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)


def build_password_reset_url(token):
    parts = urlsplit(PASSWORD_RESET_URL)
    query = dict(parse_qsl(parts.query))
    query["reset_token"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def send_password_reset_email(recipient, token):
    reset_url = build_password_reset_url(token)
    message = EmailMessage()
    message["Subject"] = "Redefinicao de senha - VamoAli"
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = recipient
    message.set_content(
        "Recebemos uma solicitacao para redefinir sua senha no VamoAli.\n\n"
        f"Use este link nos proximos minutos:\n{reset_url}\n\n"
        "Se voce nao solicitou a troca, ignore este email."
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)

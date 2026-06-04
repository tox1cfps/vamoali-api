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


def send_email(recipient, subject, body, attachment=None):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = recipient
    message.set_content(body)
    if attachment:
        filename, content = attachment
        message.add_attachment(content, maintype="application", subtype="octet-stream", filename=filename)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)


def send_password_reset_email(recipient, token):
    reset_url = build_password_reset_url(token)
    send_email(
        recipient,
        "Redefinicao de senha - VamoAli",
        "Recebemos uma solicitacao para redefinir sua senha no VamoAli.\n\n"
        f"Use este link nos proximos minutos:\n{reset_url}\n\n"
        "Se voce nao solicitou a troca, ignore este email.",
    )


def send_welcome_email(recipient, username):
    send_email(
        recipient,
        "Boas-vindas ao VamoAli",
        f"Ola, {username}!\n\nSua conta no VamoAli foi criada. Comece adicionando um lugar para conhecer.",
    )

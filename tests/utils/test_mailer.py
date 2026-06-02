from unittest.mock import Mock

import utils.mailer as mailer


def test_build_password_reset_url_preserves_existing_query():
    assert mailer.build_password_reset_url("token") == "http://localhost:5000/auth.html?reset_token=token"


def test_send_password_reset_email_uses_tls_and_smtp_credentials(monkeypatch):
    smtp = Mock()
    smtp.__enter__ = Mock(return_value=smtp)
    smtp.__exit__ = Mock(return_value=None)
    factory = Mock(return_value=smtp)
    monkeypatch.setattr(mailer.smtplib, "SMTP", factory)
    monkeypatch.setattr(mailer.ssl, "create_default_context", lambda: "tls-context")

    mailer.send_password_reset_email("ana@example.com", "raw-token")

    factory.assert_called_once_with(mailer.SMTP_HOST, mailer.SMTP_PORT, timeout=10)
    smtp.starttls.assert_called_once_with(context="tls-context")
    smtp.login.assert_called_once_with(mailer.SMTP_USER, mailer.SMTP_PASSWORD)
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "ana@example.com"
    assert "reset_token=raw-token" in message.get_content()

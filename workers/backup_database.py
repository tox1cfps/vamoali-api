import csv
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import select

from config.settings import BACKUP_DIR, BACKUP_EMAIL, BACKUP_ENCRYPTION_KEY
from database import session_scope
from models import EmailJob, Group, GroupInvite, GroupMember, PasswordResetToken, Place, User
from utils.mailer import send_email

TABLES = {
    "users": User,
    "places": Place,
    "groups": Group,
    "group_members": GroupMember,
    "group_invites": GroupInvite,
    "password_reset_tokens": PasswordResetToken,
    "email_jobs": EmailJob,
}


def build_backup():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        with session_scope() as session:
            for table_name, model in TABLES.items():
                text = io.StringIO(newline="")
                columns = [column.name for column in model.__table__.columns]
                writer = csv.writer(text)
                writer.writerow(columns)
                for row in session.scalars(select(model)).all():
                    writer.writerow(
                        [getattr(row, column) if getattr(row, column) is not None else "" for column in columns]
                    )
                archive.writestr(f"{table_name}.csv", text.getvalue())
    return output.getvalue()


def run_backup():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"vamoali-backup-{timestamp}.zip"
    content = build_backup()

    if BACKUP_EMAIL:
        content = Fernet(BACKUP_ENCRYPTION_KEY.encode()).encrypt(content)
        filename += ".fernet"
        send_email(
            BACKUP_EMAIL,
            f"Backup VamoAli - {timestamp}",
            "Backup diario criptografado do PostgreSQL em arquivos CSV anexado.",
            (filename, content),
        )
        return f"enviado para {BACKUP_EMAIL}"

    directory = Path(BACKUP_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_bytes(content)
    return str(path)


if __name__ == "__main__":
    print(run_backup())

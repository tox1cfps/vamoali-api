from cryptography.fernet import Fernet

from config.settings import FERNET_KEY

if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY não configurada no ambiente")


fernet = Fernet(FERNET_KEY.encode())


def encrypt(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()

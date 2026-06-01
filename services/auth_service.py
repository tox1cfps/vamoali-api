from repositories.user_repository import UserRepository
import bcrypt
import jwt
import random
import secrets
from datetime import datetime, timedelta, timezone
from config.settings import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS


class AuthService:
    _reset_tokens = {}
    _reset_questions = [
        {"question": "Quanto é PI ao quadrado? (arredonde para 2 casas)", "answer": "9.87"},
        {"question": "Quanto é a raiz quadrada de 144?", "answer": "12"},
        {"question": "Quanto é 7 elevado a 3?", "answer": "343"},
        {"question": "Quantos segundos tem uma hora?", "answer": "3600"},
        {"question": "Quanto é 13 vezes 13?", "answer": "169"},
    ]
    _punitive_messages = [
        "Resposta errada. Você tropeçou na conta e caiu com estilo.",
        "Nada feito. A matemática deu risada e foi embora.",
        "Resposta incorreta. Seu cérebro pediu recesso nessa rodada.",
        "Falhou bonito. Volte para o ringue dos números.",
        "Errou a conta. A planilha sentiu vergonha alheia.",
    ]

    def __init__(self):
        self.user_repo = UserRepository()

    @classmethod
    def _cleanup_reset_tokens(cls):
        now = datetime.now(timezone.utc)
        expired = [token for token, data in cls._reset_tokens.items() if data["expires_at"] <= now]

        for token in expired:
            cls._reset_tokens.pop(token, None)

    @staticmethod
    def _validate_password_strength(password):
        if not password or len(password) < 8:
            raise ValueError("A senha precisa ter no mínimo 8 caracteres")

        if not any(char.isupper() for char in password):
            raise ValueError("A senha precisa ter pelo menos uma letra maiúscula")

        if not any(char.isdigit() for char in password):
            raise ValueError("A senha precisa ter pelo menos um número")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in password):
            raise ValueError("A senha precisa ter pelo menos um caractere especial")

    @classmethod
    def _create_reset_challenge(cls, email=None):
        cls._cleanup_reset_tokens()
        challenge = random.choice(cls._reset_questions)
        token = secrets.token_hex(16)

        cls._reset_tokens[token] = {
            "answer": challenge["answer"],
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
            "email": email,
        }

        return {"token": token, "question": challenge["question"]}

    def request_reset_password(self, email=None):
        return self._create_reset_challenge(email)

    def reset_password(self, token, answer, new_password, email=None):
        self.__class__._cleanup_reset_tokens()

        token_data = self.__class__._reset_tokens.get(token)
        if token_data is None:
            raise ValueError("Token inválido ou expirado")

        stored_email = token_data.get("email")
        final_email = email or stored_email

        if stored_email and email and stored_email != email:
            raise ValueError("E-mail não confere com este token")

        if final_email is None:
            raise ValueError("E-mail obrigatório para redefinir a senha")

        if str(answer).strip() != token_data["answer"]:
            raise ValueError(random.choice(self._punitive_messages))

        self._validate_password_strength(new_password)

        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        updated = self.user_repo.update_password(final_email, password_hash)

        if not updated:
            raise LookupError("Usuário não encontrado")

        self.__class__._reset_tokens.pop(token, None)
        return {"success": True, "message": "Senha atualizada com sucesso"}

    def _generate_token(self, user_id):
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
        }        

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token):
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    def register_user(self, username, email, password):
        check_email = self.user_repo.find_by_email(email)

        if check_email is not None:
            raise ValueError("E-mail já cadastrado")

        self._validate_password_strength(password)
        
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        user = self.user_repo.create_user(username, email, password_hash)

        token = self._generate_token(user["id"])
        return {"user": user, "token": token}

    def login_user(self, email, password):
        check_email = self.user_repo.find_by_email(email)
        
        if check_email is None:
            raise ValueError("Credenciais Inválidas")
        
        password_match = bcrypt.checkpw(password.encode("utf-8"), check_email["password_hash"].encode("utf-8"))
        
        if not password_match:
            raise ValueError("Credenciais Inválidas")

        user = {"id": check_email["id"], "username": check_email["username"]}
        token = self._generate_token(check_email["id"])
        return {"user": user, "token": token}
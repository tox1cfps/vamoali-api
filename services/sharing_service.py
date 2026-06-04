import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone

from config.settings import JWT_SECRET, SHARING_INVITE_EXPIRATION_HOURS
from repositories.group_invite_repository import GroupInviteRepository
from repositories.group_member_repository import GroupMemberRepository
from repositories.group_repository import GroupRepository
from repositories.user_repository import UserRepository


class SharingService:
    CODE_ALPHABET = string.ascii_uppercase + string.digits

    def __init__(self):
        self.group_repo = GroupRepository()
        self.member_repo = GroupMemberRepository()
        self.invite_repo = GroupInviteRepository()
        self.user_repo = UserRepository()

    @staticmethod
    def _has_value(value):
        return isinstance(value, str) and bool(value.strip())

    def _find_invite(self, code=None, token=None):
        has_code = self._has_value(code)
        has_token = self._has_value(token)

        if has_code == has_token:
            raise ValueError("Informe somente codigo ou token")

        if has_code:
            normalized_code = code.strip().upper()
            invite = self.invite_repo.find_by_code_hash(self._hash_secret(normalized_code))
        else:
            normalized_token = token.strip()
            invite = self.invite_repo.find_by_token_hash(self._hash_secret(normalized_token))

        if invite is None:
            raise LookupError("Convite nao encontrado")

        return invite

    @staticmethod
    def _validate_invite(invite, user_id):
        if invite.get("accepted_at") not in (None, ""):
            raise ValueError("Convite ja utilizado")

        if invite.get("revoked_at") not in (None, ""):
            raise ValueError("Convite revogado")

        if invite["created_by"] == user_id:
            raise ValueError("Voce nao pode aceitar seu proprio convite")

        try:
            expires_at = datetime.fromisoformat(invite["expires_at"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("Convite invalido") from exc

        if expires_at.tzinfo is None:
            raise ValueError("Convite invalido")

        if expires_at <= datetime.now(timezone.utc):
            raise ValueError("Convite expirado")

    def accept_invite(self, user_id, code=None, token=None):
        invite = self._find_invite(code=code, token=token)
        self._validate_invite(invite, user_id)

        group = self.group_repo.find_by_id(invite["group_id"])
        if group is None:
            raise LookupError("Grupo nao encontrado")

        current_membership = self.member_repo.find_active_by_user(user_id)
        if current_membership is not None:
            if current_membership["group_id"] == invite["group_id"]:
                raise ValueError("Voce ja participa deste grupo")

            raise ValueError("Voce ja participa de outro grupo")

        member = self.member_repo.create_member(
            invite["group_id"],
            user_id,
        )

        accepted_at = datetime.now(timezone.utc).isoformat()
        updated_invite = self.invite_repo.update_invite(
            invite["id"],
            {
                "accepted_at": accepted_at,
                "accepted_by": user_id,
            },
        )
        if updated_invite is None:
            raise LookupError("Convite nao encontrado")

        return {
            "group_id": invite["group_id"],
            "member": member,
        }

    def get_visible_user_ids(self, user_id):
        membership = self.member_repo.find_active_by_user(user_id)

        if membership is None:
            return [user_id]

        group = self.group_repo.find_by_id(membership["group_id"])
        if group is None:
            raise LookupError("Grupo nao encontrado")

        members = self.member_repo.find_active_by_group(group["id"])
        visible_user_ids = [member["user_id"] for member in members]

        if user_id not in visible_user_ids:
            raise LookupError("Participacao no grupo nao encontrada")

        return visible_user_ids

    def get_group(self, user_id):
        membership = self.member_repo.find_active_by_user(user_id)
        if membership is None:
            raise LookupError("Grupo nao encontrado")

        group = self.group_repo.find_by_id(membership["group_id"])
        if group is None:
            raise LookupError("Grupo nao encontrado")

        memberships = self.member_repo.find_active_by_group(group["id"])
        users_by_id = self.user_repo.find_by_ids(group_membership["user_id"] for group_membership in memberships)
        members = []

        for group_membership in memberships:
            member_user_id = group_membership["user_id"]
            user = users_by_id.get(member_user_id)
            if user is None:
                raise LookupError("Usuario do grupo nao encontrado")

            members.append(
                {
                    "id": member_user_id,
                    "username": user["username"],
                    "joined_at": group_membership.get("joined_at", ""),
                    "is_current_user": member_user_id == user_id,
                    "is_creator": member_user_id == group["created_by"],
                }
            )

        if not any(member["is_current_user"] for member in members):
            raise LookupError("Participacao no grupo nao encontrada")

        return {
            "id": group["id"],
            "created_by": group["created_by"],
            "created_at": group.get("created_at", ""),
            "members": members,
        }

    def remove_member(self, user_id, member_user_id):
        membership = self.member_repo.find_active_by_user(user_id)
        if membership is None:
            raise LookupError("Grupo nao encontrado")

        group = self.group_repo.find_by_id(membership["group_id"])
        if group is None:
            raise LookupError("Grupo nao encontrado")

        members = self.member_repo.find_active_by_group(group["id"])
        member_user_ids = {member["user_id"] for member in members}
        if member_user_id not in member_user_ids:
            raise LookupError("Membro nao encontrado")

        if member_user_id == user_id:
            if group["created_by"] == user_id and len(members) > 1:
                raise ValueError("Remova os outros membros antes de sair do grupo")
        elif group["created_by"] != user_id:
            raise PermissionError("Somente o criador pode remover outro membro")

        removed = self.member_repo.deactivate_member(group["id"], member_user_id)
        if removed is None:
            raise LookupError("Membro nao encontrado")

        return {
            "success": True,
            "group_id": group["id"],
            "removed_user_id": member_user_id,
        }

    def revoke_invite(self, user_id, invite_id):
        invite = self.invite_repo.find_by_id(invite_id)
        if invite is None:
            raise LookupError("Convite nao encontrado")

        membership = self.member_repo.find_active_by_user(user_id)
        if membership is None or membership["group_id"] != invite["group_id"]:
            raise LookupError("Convite nao encontrado")

        group = self.group_repo.find_by_id(invite["group_id"])
        if group is None:
            raise LookupError("Grupo nao encontrado")

        if invite["created_by"] != user_id and group["created_by"] != user_id:
            raise PermissionError("Sem permissao para revogar este convite")

        if invite.get("accepted_at") not in (None, ""):
            raise ValueError("Convite ja utilizado")

        if invite.get("revoked_at") not in (None, ""):
            raise ValueError("Convite ja revogado")

        revoked_at = datetime.now(timezone.utc).isoformat()
        updated_invite = self.invite_repo.update_invite(
            invite_id,
            {"revoked_at": revoked_at},
        )
        if updated_invite is None:
            raise LookupError("Convite nao encontrado")

        return {
            "success": True,
            "invite_id": invite_id,
            "revoked_at": revoked_at,
        }

    @staticmethod
    def _hash_secret(value):
        if not isinstance(value, str) or not value:
            raise ValueError("Codigo ou token invalido")

        return hmac.new(
            JWT_SECRET.encode("utf-8"),
            value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def _generate_code(cls):
        suffix = "".join(secrets.choice(cls.CODE_ALPHABET) for _ in range(6))
        return f"VAMO-{suffix}"

    def _find_or_create_group(self, user_id):
        membership = self.member_repo.find_active_by_user(user_id)

        if membership is not None:
            group = self.group_repo.find_by_id(membership["group_id"])
            if group is None:
                raise LookupError("Grupo nao encontrado")

            return group

        group = self.group_repo.create_group(user_id)
        self.member_repo.create_member(group["id"], user_id)
        return group

    def create_invite(self, user_id):
        group = self._find_or_create_group(user_id)

        code = self._generate_code()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=SHARING_INVITE_EXPIRATION_HOURS)

        invite = self.invite_repo.create_invite(
            group["id"],
            user_id,
            self._hash_secret(code),
            self._hash_secret(token),
            expires_at.isoformat(),
        )

        return {
            "id": invite["id"],
            "code": code,
            "token": token,
            "expires_at": invite["expires_at"],
        }

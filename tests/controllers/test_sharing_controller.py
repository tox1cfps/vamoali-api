from unittest.mock import Mock

import controllers.sharing_controller as controller


def test_get_group_requires_authentication(client):
    assert client.get("/sharing/group").status_code == 401


def test_get_group_returns_service_payload(authenticated_client, monkeypatch):
    service = Mock()
    service.get_group.return_value = {
        "id": "group-1",
        "members": [{"id": "user-1", "username": "Ana"}],
    }
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.get("/sharing/group")

    assert response.status_code == 200
    assert response.get_json()["id"] == "group-1"
    service.get_group.assert_called_once_with("user-1")


def test_get_group_converts_missing_group_to_404(authenticated_client, monkeypatch):
    service = Mock()
    service.get_group.side_effect = LookupError("Grupo nao encontrado")
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.get("/sharing/group")

    assert response.status_code == 404
    assert response.get_json()["message"] == "Grupo nao encontrado"


def test_remove_member_returns_service_payload(authenticated_client, monkeypatch):
    service = Mock()
    service.remove_member.return_value = {
        "success": True,
        "removed_user_id": "user-2",
    }
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.delete("/sharing/group/members/user-2")

    assert response.status_code == 200
    service.remove_member.assert_called_once_with("user-1", "user-2")


def test_remove_member_converts_permission_error_to_403(authenticated_client, monkeypatch):
    service = Mock()
    service.remove_member.side_effect = PermissionError("Sem permissao")
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.delete("/sharing/group/members/user-2")

    assert response.status_code == 403


def test_create_invite_requires_authentication(client):
    assert client.post("/sharing/invites").status_code == 401


def test_create_invite_returns_created_payload(
    authenticated_client,
    monkeypatch,
):
    service = Mock()
    service.create_invite.return_value = {
        "id": "invite-1",
        "code": "VAMO-ABC123",
        "token": "raw-token",
        "expires_at": "expires",
    }
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.post("/sharing/invites")

    assert response.status_code == 201
    assert response.get_json()["code"] == "VAMO-ABC123"
    service.create_invite.assert_called_once_with("user-1")


def test_accept_invite_requires_json_body(authenticated_client):
    response = authenticated_client.post(
        "/sharing/invites/accept",
        json=None,
    )

    assert response.status_code == 400


def test_accept_invite_forwards_code(
    authenticated_client,
    monkeypatch,
):
    service = Mock()
    service.accept_invite.return_value = {
        "group_id": "group-1",
        "member": {"user_id": "user-1"},
    }
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.post(
        "/sharing/invites/accept",
        json={"code": "VAMO-ABC123"},
    )

    assert response.status_code == 200
    service.accept_invite.assert_called_once_with(
        "user-1",
        code="VAMO-ABC123",
        token=None,
    )


def test_accept_invite_converts_validation_error_to_400(
    authenticated_client,
    monkeypatch,
):
    service = Mock()
    service.accept_invite.side_effect = ValueError("Convite expirado")
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.post(
        "/sharing/invites/accept",
        json={"token": "expired"},
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "Convite expirado"


def test_accept_invite_converts_missing_invite_to_404(
    authenticated_client,
    monkeypatch,
):
    service = Mock()
    service.accept_invite.side_effect = LookupError("Convite nao encontrado")
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.post(
        "/sharing/invites/accept",
        json={"code": "VAMO-MISSING"},
    )

    assert response.status_code == 404


def test_revoke_invite_returns_service_payload(authenticated_client, monkeypatch):
    service = Mock()
    service.revoke_invite.return_value = {
        "success": True,
        "invite_id": "invite-1",
    }
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.delete("/sharing/invites/invite-1")

    assert response.status_code == 200
    service.revoke_invite.assert_called_once_with("user-1", "invite-1")


def test_revoke_invite_converts_used_invite_to_400(authenticated_client, monkeypatch):
    service = Mock()
    service.revoke_invite.side_effect = ValueError("Convite ja utilizado")
    monkeypatch.setattr(controller, "sharing_service", service)

    response = authenticated_client.delete("/sharing/invites/invite-1")

    assert response.status_code == 400

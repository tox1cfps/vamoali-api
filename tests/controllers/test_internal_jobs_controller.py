from unittest.mock import Mock

import pytest

import controllers.internal_jobs_controller as controller


@pytest.fixture
def authorized_client(client, monkeypatch):
    monkeypatch.setattr(controller, "ADMIN_JOB_SECRET", "secret")
    client.environ_base["HTTP_X_ADMIN_JOB_SECRET"] = "secret"
    return client


def test_internal_jobs_are_hidden_without_secret(client, monkeypatch):
    monkeypatch.setattr(controller, "ADMIN_JOB_SECRET", "secret")

    assert client.post("/internal/jobs/process-emails").status_code == 404


def test_process_emails(authorized_client, monkeypatch):
    process_pending = Mock(return_value=3)
    monkeypatch.setattr(controller, "process_pending", process_pending)

    response = authorized_client.post("/internal/jobs/process-emails")

    assert response.get_json()["processed"] == 3


def test_daily_maintenance(authorized_client, monkeypatch):
    monkeypatch.setattr(controller, "schedule_reminders", Mock(return_value=2))
    monkeypatch.setattr(controller, "process_pending", Mock(return_value=2))
    monkeypatch.setattr(controller, "sync_report", Mock(return_value={"users": 1}))
    monkeypatch.setattr(controller, "run_backup", Mock(return_value="sent"))

    response = authorized_client.post("/internal/jobs/daily-maintenance")

    assert response.status_code == 200
    assert response.get_json()["backup"] == "sent"
    assert response.get_json()["processed_emails"] == 2


def test_migration_and_status(authorized_client, monkeypatch):
    create_all = Mock()
    monkeypatch.setattr(controller.Base.metadata, "create_all", create_all)
    monkeypatch.setattr(controller, "import_all", Mock(return_value={"users": 1}))
    monkeypatch.setattr(controller, "migration_status", Mock(return_value={"matches": True}))

    migrated = authorized_client.post("/internal/jobs/migrate-sheets")
    status = authorized_client.get("/internal/jobs/migration-status")

    assert migrated.get_json()["imported"] == {"users": 1}
    assert status.get_json()["status"] == {"matches": True}
    create_all.assert_called_once_with(controller.engine)

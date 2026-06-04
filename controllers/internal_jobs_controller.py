import hmac

from flask import Blueprint, jsonify, request

from config.settings import ADMIN_JOB_SECRET, EMAIL_JOB_BATCH_SIZE
from workers.backup_database import run_backup
from workers.email_worker import process_pending
from workers.schedule_unvisited_reminders import schedule_reminders
from workers.sync_sheets_report import sync_report

bp = Blueprint("internal_jobs", __name__, url_prefix="/internal/jobs")


def import_all():
    from scripts.import_sheets_to_postgres import import_all as run_import

    return run_import()


def migration_status():
    from scripts.import_sheets_to_postgres import migration_status as get_status

    return get_status()


@bp.before_request
def protect_internal_jobs():
    provided = request.headers.get("X-Admin-Job-Secret", "")
    authorized = bool(ADMIN_JOB_SECRET) and hmac.compare_digest(provided, ADMIN_JOB_SECRET)
    if not authorized:
        return jsonify({"success": False, "message": "Nao encontrado"}), 404
    return None


@bp.post("/process-emails")
def process_emails():
    return jsonify({"success": True, "processed": process_pending(EMAIL_JOB_BATCH_SIZE)}), 200


@bp.post("/daily-maintenance")
def daily_maintenance():
    reminders = schedule_reminders()
    return (
        jsonify(
            {
                "success": True,
                "reminders": reminders,
                "processed_emails": process_pending(EMAIL_JOB_BATCH_SIZE),
                "report": sync_report(),
                "backup": run_backup(),
            }
        ),
        200,
    )


@bp.post("/migrate-sheets")
def migrate_sheets():
    return jsonify({"success": True, "imported": import_all(), "status": migration_status()}), 200


@bp.get("/migration-status")
def get_migration_status():
    return jsonify({"success": True, "status": migration_status()}), 200

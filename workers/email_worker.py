import argparse
import time

from config.settings import EMAIL_WORKER_POLL_SECONDS
from repositories.email_job_repository import EmailJobRepository
from utils.mailer import send_email, send_password_reset_email, send_welcome_email


def deliver(job):
    payload = job["payload"]
    if job["kind"] == "welcome":
        send_welcome_email(job["recipient"], payload["username"])
    elif job["kind"] == "unvisited_reminder":
        send_email(
            job["recipient"],
            "Um lugar ainda espera por voce - VamoAli",
            f"Voce ainda possui {payload['count']} lugar(es) para conhecer.\n\n"
            f"Sugestao de hoje: {payload['suggestion']}",
        )
    elif job["kind"] == "password_reset":
        send_password_reset_email(job["recipient"], payload["token"])
    else:
        raise ValueError(f"Tipo de email desconhecido: {job['kind']}")


def process_one(repository=None):
    repository = repository or EmailJobRepository()
    job = repository.claim_next()
    if job is None:
        return False
    try:
        deliver(job)
    except Exception as exc:
        repository.mark_failed(job["id"], exc)
    else:
        repository.mark_sent(job["id"])
    return True


def process_pending(limit):
    processed = 0
    while processed < limit and process_one():
        processed += 1
    return processed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        processed = process_one()
        if args.once:
            return
        if not processed:
            time.sleep(EMAIL_WORKER_POLL_SECONDS)


if __name__ == "__main__":
    main()

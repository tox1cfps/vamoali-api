import os

from locust import HttpUser, between, events, task


def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except ValueError as exc:
        raise RuntimeError(f"{name} deve ser numerico") from exc


MAX_P95_MS = _env_float("PERF_MAX_P95_MS", "1500")
MAX_FAILURE_RATIO = _env_float("PERF_MAX_FAILURE_RATIO", "0.01")


class VamoAliUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        token = os.getenv("PERF_TOKEN")
        if token:
            self.client.headers["Authorization"] = f"Bearer {token}"
            return

        email = os.getenv("PERF_EMAIL")
        password = os.getenv("PERF_PASSWORD")
        if not email or not password:
            raise RuntimeError("Defina PERF_TOKEN ou PERF_EMAIL e PERF_PASSWORD")

        with self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
            name="/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Login falhou com status {response.status_code}")
                return

            token = response.json().get("token")
            if not token:
                response.failure("Login nao retornou token")
                return

            self.client.headers["Authorization"] = f"Bearer {token}"

    @task(6)
    def list_places(self):
        self.client.get("/places", name="/places")

    @task(2)
    def random_place(self):
        with self.client.get("/places/random", name="/places/random", catch_response=True) as response:
            if response.status_code == 404:
                response.success()

    @task(2)
    def get_group(self):
        with self.client.get("/sharing/group", name="/sharing/group", catch_response=True) as response:
            if response.status_code == 404:
                response.success()


@events.quitting.add_listener
def enforce_thresholds(environment, **_kwargs):
    if environment.stats.total.num_requests == 0:
        environment.process_exit_code = 1
        return

    p95 = environment.stats.total.get_response_time_percentile(0.95)
    if p95 > MAX_P95_MS or environment.stats.total.fail_ratio > MAX_FAILURE_RATIO:
        environment.process_exit_code = 1

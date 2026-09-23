#!/usr/bin/env python3
"""ПРОТОТИП. Воркер self-serve сканов: поллер очереди Cyber Galaxy.

Цикл: забрать задачу у платформы → поднять per-scan сеть + egress-gateway →
запустить ai-raider в сетевом скоупе (AIRAIDER_SELF_SERVE=1) → собрать находки →
сдать их платформе → снести сеть. Всё, что мимо allowlist, шлюз режет.

> Прототип: требует Docker-хост, запущенную платформу, ключ модели и разрешённую
> цель. В этой сессии не запускался. Не для продакшена как есть — нет ретраев,
> лимитов стоимости/времени, изоляции воркеров и т.п.

Окружение:
  AIRAIDER_PLATFORM_URL   базовый URL платформы (напр. http://localhost:3011)
  AIRAIDER_WORKER_TOKEN   общий bearer-токен воркера (совпадает с платформой)
  AIRAIDER_WORKER_ID      идентификатор воркера (по умолчанию hostname)
  AIRAIDER_MODEL_ENDPOINTS  доп. allowlist host:port модели, через запятую
                            (напр. api.openai.com:443,openrouter.ai:443)
  AIRAIDER_LLM / LLM_API_KEY  как обычно для ai-raider
  AIRAIDER_POLL_SECONDS   пауза между опросами пустой очереди (по умолчанию 10)

Только stdlib + subprocess. Использование: python3 scripts/worker.py
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from push_findings import build_payload, _latest_run  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GATEWAY_DIR = ROOT / "containers" / "egress-gateway"
RUNS_DIR = ROOT / "ai-raider_runs"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _api(path: str) -> str:
    base = _env("AIRAIDER_PLATFORM_URL", "http://localhost:3011").rstrip("/")
    return base + path


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    token = _env("AIRAIDER_WORKER_TOKEN")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_api(path), data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            if resp.status == 204 or not raw:
                return resp.status, {}
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def claim() -> dict | None:
    status, body = _request("POST", "/api/worker/claim", {"workerId": _env("AIRAIDER_WORKER_ID", socket.gethostname())})
    if status == 204 or not body:
        return None
    if status != 200 or not isinstance(body, dict):
        print(f"[claim] неожиданный ответ {status}: {body}", file=sys.stderr)
        return None
    return body


def report_status(job_id: str, status: str, error: str = "") -> None:
    _request("POST", f"/api/worker/scans/{job_id}/status", {"status": status, "error": error})


def submit_findings(job_id: str, payload: dict) -> None:
    st, body = _request("POST", f"/api/worker/scans/{job_id}/findings", payload)
    print(f"[findings] job={job_id} → {st}: {body if isinstance(body, str) else body.get('runId', body)}")


def allowlist_args(job: dict) -> list[str]:
    """HOST:PORT для egress-gateway: цель из задачи + эндпоинты модели из env."""
    pairs: list[str] = []
    for entry in job.get("allowlist", []):
        host = str(entry.get("host", ""))
        port = int(entry.get("port", 443))
        if host:
            pairs.append(f"{host}:{port}")
    for ep in _env("AIRAIDER_MODEL_ENDPOINTS").split(","):
        ep = ep.strip()
        if ep:
            pairs.append(ep if ":" in ep else f"{ep}:443")
    return pairs


def run_job(job: dict) -> None:
    j = job["job"]
    job_id = j["id"]
    target = job["target"]
    mode = job.get("scanMode", "quick")
    net_name = f"airaider-egress-{job_id}"

    print(f"[job] {job_id} target={target} mode={mode}")
    pairs = allowlist_args(job)
    if not pairs:
        report_status(job_id, "failed", "пустой allowlist")
        return

    # 1. Поднять per-scan сеть + шлюз с allowlist (прототип-скрипт).
    setup = subprocess.run(
        [str(GATEWAY_DIR / "setup-scan-network.sh"), job_id, *pairs],
        capture_output=True, text=True,
    )
    if setup.returncode != 0:
        report_status(job_id, "failed", f"egress-gateway setup: {setup.stderr[-500:]}")
        return

    try:
        # 2. Запуск ai-raider в сетевом скоупе.
        env = dict(os.environ)
        env["AIRAIDER_SELF_SERVE"] = "1"
        env["AIRAIDER_DOCKER_SANDBOX_NETWORK"] = net_name
        scan = subprocess.run(
            [str(ROOT / ".venv" / "bin" / "ai-raider"), "-n", "-t", target, "--scan-mode", mode],
            env=env, cwd=str(ROOT),
        )
        if scan.returncode not in (0, 2):  # 0 чисто, 2 находки есть — оба ок
            report_status(job_id, "failed", f"скан завершился с кодом {scan.returncode}")
            return

        # 3. Собрать находки последнего прогона и сдать платформе.
        run_dir = _latest_run(RUNS_DIR)
        if run_dir is None:
            report_status(job_id, "failed", "прогон не создал каталог")
            return
        try:
            payload = build_payload(run_dir)
        except SystemExit as exc:
            # build_payload вызывает SystemExit при отсутствии находок — это ok (чистый скан).
            report_status(job_id, "done", str(exc))
            return
        submit_findings(job_id, payload)
    finally:
        # 4. Снести сеть/шлюз в любом случае.
        subprocess.run([str(GATEWAY_DIR / "teardown-scan-network.sh"), job_id], capture_output=True)


def main() -> int:
    if not _env("AIRAIDER_WORKER_TOKEN"):
        print("Задай AIRAIDER_WORKER_TOKEN (общий с платформой).", file=sys.stderr)
        return 2
    poll = int(_env("AIRAIDER_POLL_SECONDS", "10") or "10")
    print(f"[worker] старт, платформа {_api('')}")
    while True:
        try:
            job = claim()
        except urllib.error.URLError as exc:
            print(f"[worker] платформа недоступна: {exc.reason}", file=sys.stderr)
            time.sleep(poll)
            continue
        if job is None:
            time.sleep(poll)
            continue
        job_id = job["job"]["id"]
        try:
            run_job(job)
        except Exception as exc:  # noqa: BLE001 — воркер не должен падать из-за одной задачи
            print(f"[worker] задача {job_id} упала: {exc}", file=sys.stderr)
            report_status(job_id, "failed", str(exc)[:500])


if __name__ == "__main__":
    sys.exit(main())

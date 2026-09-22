#!/usr/bin/env python3
"""Bridge в Cyber Galaxy: прямой пуш находок прогона в приватную админку платформы.

Собирает тело импорта из каталога прогона AI-Рейдера
(``vulnerabilities.json`` + ``penetration_test_report.md`` + ``run.json``)
и отправляет POST на ``<CG_PLATFORM_URL>/api/admin/pentest``.

Так убирается ручной шаг «выгрузить файл и залить в браузере».

Конфигурация через окружение:
  CG_PLATFORM_URL   базовый URL платформы (по умолчанию http://localhost:3000)
  CG_AUTH_COOKIE    значение owner-cookie ``cg_auth`` (JWT). Не нужно, если на
                    сервере включён ADMIN_DEV_BYPASS=1 (только не в production).

Использование:
  scripts/push_findings.py                 # последний прогон
  scripts/push_findings.py --run <каталог> # конкретный прогон
  scripts/push_findings.py --dry-run       # собрать тело и показать, не отправляя

Только stdlib — новых зависимостей не добавляет.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

RUNS_DIR = "ai-raider_runs"
DEFAULT_URL = "http://localhost:3000"
IMPORT_PATH = "/api/admin/pentest"


def _repo_root() -> Path:
    # scripts/push_findings.py → корень репозитория на уровень выше.
    return Path(__file__).resolve().parent.parent


def _latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.is_dir():
        return None
    candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Не удалось прочитать {path}: {exc}")


def _extract_target(run_record: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    targets = run_record.get("targets_info") or []
    if isinstance(targets, list) and targets:
        first = targets[0]
        if isinstance(first, dict):
            original = str(first.get("original") or "").strip()
            if original:
                return original
    # Резерв: цель из первой находки.
    for f in findings:
        if isinstance(f, dict):
            t = str(f.get("target") or "").strip()
            if t:
                return t
    return ""


def build_payload(run_dir: Path) -> dict[str, Any]:
    findings = _load_json(run_dir / "vulnerabilities.json", default=[])
    if not isinstance(findings, list):
        raise SystemExit(f"vulnerabilities.json в {run_dir} — не массив.")
    if not findings:
        raise SystemExit(
            f"В прогоне {run_dir.name} нет находок — импортировать нечего."
        )

    run_record = _load_json(run_dir / "run.json", default={})
    if not isinstance(run_record, dict):
        run_record = {}

    report_path = run_dir / "penetration_test_report.md"
    report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""

    run_name = (
        str(run_record.get("run_name") or "").strip()
        or str(run_record.get("run_id") or "").strip()
        or run_dir.name
    )
    scan_mode = str(run_record.get("scan_mode") or "").strip() or "unknown"
    target = _extract_target(run_record, findings)

    return {
        "runName": run_name,
        "target": target,
        "scanMode": scan_mode,
        "reportMd": report_md,
        "findings": findings,
    }


def push(payload: dict[str, Any], base_url: str, cookie: str | None) -> dict[str, Any]:
    url = base_url.rstrip("/") + IMPORT_PATH
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", f"cg_auth={cookie}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return {"status": resp.status, "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"status": exc.code, "body": body}
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Не удалось подключиться к {url}: {exc.reason}\n"
            f"Проверь, что платформа запущена и CG_PLATFORM_URL указывает на неё."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Прямой пуш находок прогона AI-Рейдера в Cyber Galaxy."
    )
    parser.add_argument("--run", help="каталог конкретного прогона (по умолчанию — последний)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="собрать тело запроса и показать сводку, ничего не отправляя",
    )
    args = parser.parse_args()

    root = _repo_root()
    if args.run:
        run_dir = Path(args.run)
        if not run_dir.is_absolute():
            run_dir = root / run_dir
    else:
        run_dir = _latest_run(root / RUNS_DIR)
        if run_dir is None:
            raise SystemExit(
                f"Прогонов не найдено в {root / RUNS_DIR} — сначала запусти скан (./run-scan.sh …)."
            )

    if not run_dir.is_dir():
        raise SystemExit(f"Каталог прогона не найден: {run_dir}")

    payload = build_payload(run_dir)
    print(f"Прогон:      {run_dir.name}")
    print(f"Цель:        {payload['target'] or '(не указана)'}")
    print(f"Режим:       {payload['scanMode']}")
    print(f"Находок:     {len(payload['findings'])}")

    if args.dry_run:
        print("\n[--dry-run] Тело запроса собрано, отправка пропущена.")
        preview = {k: (v if k != "findings" else f"<{len(v)} находок>") for k, v in payload.items()}
        preview["reportMd"] = f"<{len(payload['reportMd'])} символов>"
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    base_url = os.environ.get("CG_PLATFORM_URL", DEFAULT_URL)
    cookie = os.environ.get("CG_AUTH_COOKIE") or None
    if not cookie:
        print(
            "\n[i] CG_AUTH_COOKIE не задан — расчёт на dev-байпас платформы "
            "(ADMIN_DEV_BYPASS=1). В production нужен owner-cookie cg_auth."
        )

    print(f"\nОтправляю в {base_url}{IMPORT_PATH} …")
    result = push(payload, base_url, cookie)
    status = result["status"]
    try:
        parsed = json.loads(result["body"])
    except json.JSONDecodeError:
        parsed = result["body"]

    if status in (200, 201) and isinstance(parsed, dict) and parsed.get("ok"):
        stats = parsed.get("stats", {})
        print(
            f"✓ Импортировано. run id: {parsed.get('id')} · находок: {parsed.get('findings')}"
        )
        if stats:
            print(f"  критичность: {json.dumps(stats, ensure_ascii=False)}")
        return 0

    print(f"✗ Импорт не прошёл (HTTP {status}):")
    print(json.dumps(parsed, ensure_ascii=False, indent=2) if isinstance(parsed, dict) else parsed)
    if status == 403:
        print("\n  403 — нет прав owner. Задай CG_AUTH_COOKIE с owner-JWT или включи ADMIN_DEV_BYPASS=1 в dev.")
    elif status == 400:
        print("\n  400 — тело не прошло валидацию (см. errors выше).")
    elif status == 503:
        print("\n  503 — база платформы недоступна (нет supabase).")
    return 1


if __name__ == "__main__":
    sys.exit(main())

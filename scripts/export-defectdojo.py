#!/usr/bin/env python3
"""Export a run's findings to DefectDojo (https://www.defectdojo.org/).

Uploads the latest run's ``findings.sarif`` to DefectDojo's import-scan API as a
``SARIF`` scan. DefectDojo is open-source vulnerability management — this is a generic,
public integration (no third-party service of ours involved).

Configuration via environment:
  DEFECTDOJO_URL             base URL, e.g. https://defectdojo.example.com
  DEFECTDOJO_API_KEY         API v2 token (Django admin -> API v2 Key)
  # Target engagement — either an existing id, or product+engagement names to auto-create:
  DEFECTDOJO_ENGAGEMENT      engagement id (integer)
  DEFECTDOJO_PRODUCT         product name            (with DEFECTDOJO_ENGAGEMENT_NAME)
  DEFECTDOJO_ENGAGEMENT_NAME engagement name         (auto-created if missing)

Usage:
  scripts/export-defectdojo.py               # latest run
  scripts/export-defectdojo.py --run <dir>   # a specific run
  scripts/export-defectdojo.py --dry-run     # show what would be sent, don't upload

Only stdlib (urllib) — no extra dependencies.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

RUNS_DIR = "ai-raider_runs"
IMPORT_PATH = "/api/v2/import-scan/"
SCAN_TYPE = "SARIF"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.is_dir():
        return None
    candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def _multipart(fields: dict[str, str], file_field: str, filename: str, file_bytes: bytes) -> tuple[bytes, str]:
    """Encode fields + one file as multipart/form-data. Returns (body, content_type)."""
    boundary = f"----airaider{uuid.uuid4().hex}"
    crlf = "\r\n"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}{crlf}".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"{crlf}{crlf}'.encode())
        parts.append(f"{value}{crlf}".encode())
    parts.append(f"--{boundary}{crlf}".encode())
    parts.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"{crlf}'.encode()
    )
    parts.append(f"Content-Type: application/json{crlf}{crlf}".encode())
    parts.append(file_bytes)
    parts.append(crlf.encode())
    parts.append(f"--{boundary}--{crlf}".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def build_fields() -> dict[str, str] | None:
    """Assemble the import-scan form fields from the environment, or None if misconfigured."""
    fields: dict[str, str] = {"scan_type": SCAN_TYPE, "active": "true", "verified": "false"}
    engagement = os.environ.get("DEFECTDOJO_ENGAGEMENT", "").strip()
    product = os.environ.get("DEFECTDOJO_PRODUCT", "").strip()
    engagement_name = os.environ.get("DEFECTDOJO_ENGAGEMENT_NAME", "").strip()
    if engagement:
        fields["engagement"] = engagement
    elif product and engagement_name:
        fields["product_name"] = product
        fields["engagement_name"] = engagement_name
        fields["auto_create_context"] = "true"
    else:
        print(
            "Set DEFECTDOJO_ENGAGEMENT (id), or DEFECTDOJO_PRODUCT + DEFECTDOJO_ENGAGEMENT_NAME.",
            file=sys.stderr,
        )
        return None
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a run's findings to DefectDojo.")
    parser.add_argument("--run", help="run directory (default: latest)")
    parser.add_argument("--dry-run", action="store_true", help="show what would be sent, don't upload")
    args = parser.parse_args()

    root = _repo_root()
    if args.run:
        run_dir = Path(args.run)
        if not run_dir.is_absolute():
            run_dir = root / run_dir
    else:
        run_dir = _latest_run(root / RUNS_DIR)
        if run_dir is None:
            raise SystemExit(f"No runs in {root / RUNS_DIR} — run a scan first (./run-scan.sh ...).")
    if not run_dir.is_dir():
        raise SystemExit(f"Run directory not found: {run_dir}")

    sarif = run_dir / "findings.sarif"
    if not sarif.exists():
        raise SystemExit(f"No findings.sarif in {run_dir} — nothing to export.")
    file_bytes = sarif.read_bytes()

    fields = build_fields()
    if fields is None:
        return 2
    target_desc = fields.get("engagement") or f"{fields.get('product_name')} / {fields.get('engagement_name')}"
    print(f"Run:        {run_dir.name}")
    print(f"SARIF:      {sarif} ({len(file_bytes)} bytes)")
    print(f"Target:     {target_desc}")

    if args.dry_run:
        print("\n[--dry-run] Would POST to DefectDojo import-scan; not sending.")
        return 0

    url = os.environ.get("DEFECTDOJO_URL", "").strip()
    token = os.environ.get("DEFECTDOJO_API_KEY", "").strip()
    if not url or not token:
        raise SystemExit("Set DEFECTDOJO_URL and DEFECTDOJO_API_KEY.")

    body, content_type = _multipart(fields, "file", "findings.sarif", file_bytes)
    req = urllib.request.Request(url.rstrip("/") + IMPORT_PATH, data=body, method="POST")
    req.add_header("Authorization", f"Token {token}")
    req.add_header("Content-Type", content_type)
    print(f"\nUploading to {url.rstrip('/')}{IMPORT_PATH} ...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"✓ Imported (HTTP {resp.status}).")
            return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        print(f"✗ Import failed (HTTP {exc.code}):\n{detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc.reason}")


if __name__ == "__main__":
    sys.exit(main())

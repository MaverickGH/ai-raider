#!/usr/bin/env python3
"""Post a run's findings summary to a chat webhook and/or open Jira issues.

Reads the latest run's ``run.json`` + ``vulnerabilities.json`` and sends a compact
summary (counts by severity, status, cost, targets, top findings) to:

- a chat webhook — Slack, Mattermost, Microsoft Teams, Google Chat, or any
  endpoint that accepts a JSON POST (``AIRAIDER_WEBHOOK_FORMAT`` selects the body
  shape); and/or
- Jira — one summary issue, or ``--jira-per-finding`` to open one issue per
  high/critical finding.

Generic, self-hostable integration — only Python's stdlib (urllib), no third-party
service of ours involved, no extra dependencies.

Configuration via environment:
  # Chat webhook (optional)
  AIRAIDER_WEBHOOK_URL       incoming-webhook URL to POST to
  AIRAIDER_WEBHOOK_FORMAT    slack | teams | gchat | json   (default: slack)

  # Jira (optional; all four required to enable Jira)
  JIRA_URL                   base URL, e.g. https://acme.atlassian.net
  JIRA_USER                  account email (Jira Cloud) — omit for a bare PAT (Server/DC)
  JIRA_TOKEN                 API token (Cloud) or personal access token (Server/DC)
  JIRA_PROJECT               project key, e.g. SEC
  JIRA_ISSUE_TYPE            issue type name                (default: Task)

Usage:
  scripts/notify.py                         # latest run -> configured targets
  scripts/notify.py --run <dir>             # a specific run directory
  scripts/notify.py --min-severity high     # only notify if a finding >= this sev
  scripts/notify.py --jira-per-finding      # one Jira issue per high/critical
  scripts/notify.py --dry-run               # print what would be sent, send nothing
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

RUNS_DIR = "ai-raider_runs"
SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITY_ORDER)}
SEVERITY_EMOJI = {
    "critical": "🟥",
    "high": "🟧",
    "medium": "🟨",
    "low": "🟦",
    "info": "⬜",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.is_dir():
        return None
    candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _severity_of(report: dict[str, Any]) -> str:
    sev = str(report.get("severity", "info")).strip().lower()
    return sev if sev in SEVERITY_RANK else "info"


def summarize(run_dir: Path) -> dict[str, Any]:
    """Build a structured summary from a run directory's artifacts."""
    run = _load_json(run_dir / "run.json", {})
    vulns = _load_json(run_dir / "vulnerabilities.json", [])
    if not isinstance(vulns, list):
        vulns = []

    counts = dict.fromkeys(SEVERITY_ORDER, 0)
    for report in vulns:
        if isinstance(report, dict):
            counts[_severity_of(report)] += 1

    targets = []
    for info in run.get("targets_info", []) or []:
        if isinstance(info, dict):
            targets.append(str(info.get("target") or info.get("value") or "").strip())
        elif isinstance(info, str):
            targets.append(info.strip())
    targets = [t for t in targets if t]

    usage = run.get("llm_usage") or {}
    cost = usage.get("cost") if isinstance(usage, dict) else None

    ranked = sorted(
        (r for r in vulns if isinstance(r, dict)),
        key=lambda r: (SEVERITY_RANK[_severity_of(r)], str(r.get("timestamp", ""))),
    )
    return {
        "run_name": run.get("run_name") or run.get("run_id") or run_dir.name,
        "status": run.get("status", "unknown"),
        "scan_mode": run.get("scan_mode"),
        "targets": targets,
        "counts": counts,
        "total": sum(counts.values()),
        "cost": cost,
        "findings": ranked,
    }


def _highest_severity(summary: dict[str, Any]) -> str | None:
    for name in SEVERITY_ORDER:
        if summary["counts"].get(name):
            return name
    return None


def _count_line(counts: dict[str, int]) -> str:
    parts = [f"{SEVERITY_EMOJI[s]} {s.title()}: {counts[s]}" for s in SEVERITY_ORDER if counts[s]]
    return "  ".join(parts) if parts else "No findings"


def render_text(summary: dict[str, Any], top: int = 10) -> str:
    """Plain-text summary used for Slack/Teams/Google Chat and dry-run output."""
    lines = [
        f"AiRaider scan *{summary['run_name']}* — status: {summary['status']}",
    ]
    if summary["targets"]:
        shown = ", ".join(summary["targets"][:5])
        more = "" if len(summary["targets"]) <= 5 else f" (+{len(summary['targets']) - 5} more)"
        lines.append(f"Targets: {shown}{more}")
    if summary["scan_mode"]:
        lines.append(f"Mode: {summary['scan_mode']}")
    lines.append(f"Findings: {summary['total']} — {_count_line(summary['counts'])}")
    if isinstance(summary["cost"], int | float):
        lines.append(f"LLM cost: ${summary['cost']:.2f}")

    shown_findings = summary["findings"][:top]
    if shown_findings:
        lines.append("")
        for report in shown_findings:
            sev = _severity_of(report)
            lines.append(f"{SEVERITY_EMOJI[sev]} [{sev.upper()}] {report.get('title', 'Untitled')}")
        remaining = summary["total"] - len(shown_findings)
        if remaining > 0:
            lines.append(f"…and {remaining} more")
    return "\n".join(lines)


def _webhook_payload(fmt: str, text: str) -> dict[str, Any]:
    if fmt == "teams":
        return {"text": text}
    if fmt == "gchat":
        return {"text": text}
    if fmt == "json":
        return {"text": text}
    # slack (default): mrkdwn is the plain `text` field; newlines render as-is.
    return {"text": text}


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")  # noqa: S310 (user-provided URL)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return int(resp.status)


def send_webhook(summary: dict[str, Any], *, dry_run: bool) -> bool:
    url = os.environ.get("AIRAIDER_WEBHOOK_URL", "").strip()
    if not url:
        return False
    fmt = os.environ.get("AIRAIDER_WEBHOOK_FORMAT", "slack").strip().lower()
    text = render_text(summary)
    payload = _webhook_payload(fmt, text)
    if dry_run:
        print(f"[dry-run] POST {fmt} webhook ->\n{text}\n")
        return True
    try:
        status = _post_json(url, payload)
    except urllib.error.URLError as exc:  # pragma: no cover - network failure path
        print(f"webhook POST failed: {exc}", file=sys.stderr)
        return False
    print(f"webhook: HTTP {status}")
    return 200 <= status < 300


def _jira_auth_header() -> dict[str, str] | None:
    token = os.environ.get("JIRA_TOKEN", "").strip()
    if not token:
        return None
    user = os.environ.get("JIRA_USER", "").strip()
    if user:
        # Jira Cloud: HTTP Basic with email:api_token.
        raw = base64.b64encode(f"{user}:{token}".encode()).decode("ascii")
        return {"Authorization": f"Basic {raw}"}
    # Server/DC personal access token.
    return {"Authorization": f"Bearer {token}"}


def _jira_config() -> dict[str, str] | None:
    url = os.environ.get("JIRA_URL", "").strip().rstrip("/")
    project = os.environ.get("JIRA_PROJECT", "").strip()
    auth = _jira_auth_header()
    if not (url and project and auth):
        return None
    return {
        "url": url,
        "project": project,
        "issue_type": os.environ.get("JIRA_ISSUE_TYPE", "Task").strip() or "Task",
        **auth,
    }


def _jira_create_issue(
    cfg: dict[str, str], summary: str, description: str, labels: list[str]
) -> str:
    auth = {k: v for k, v in cfg.items() if k == "Authorization"}
    payload = {
        "fields": {
            "project": {"key": cfg["project"]},
            "summary": summary[:250],
            "description": description,
            "issuetype": {"name": cfg["issue_type"]},
            "labels": labels,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        f"{cfg['url']}/rest/api/2/issue", data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    for key, value in auth.items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        body = json.loads(resp.read().decode("utf-8"))
    return str(body.get("key", "?"))


def send_jira(summary: dict[str, Any], *, per_finding: bool, dry_run: bool) -> bool:
    cfg = _jira_config()
    if cfg is None:
        return False

    targets = ", ".join(summary["targets"]) or "(unspecified)"
    if per_finding:
        issues = [
            r
            for r in summary["findings"]
            if _severity_of(r) in ("critical", "high")
        ]
        if not issues:
            print("jira: no high/critical findings to file")
            return True
        for report in issues:
            sev = _severity_of(report)
            title = f"[AiRaider][{sev.upper()}] {report.get('title', 'Untitled')}"
            desc = (
                f"Severity: {sev.upper()}\n"
                f"Run: {summary['run_name']}\n"
                f"Targets: {targets}\n\n"
                f"{report.get('description', '') or report.get('summary', '')}"
            )
            if dry_run:
                print(f"[dry-run] Jira issue: {title}")
                continue
            key = _jira_create_issue(cfg, title, desc, ["airaider", sev])
            print(f"jira: created {key}  ({title})")
        return True

    # Single summary issue.
    title = f"[AiRaider] {summary['total']} finding(s) — {summary['run_name']}"
    desc = render_text(summary)
    if dry_run:
        print(f"[dry-run] Jira summary issue: {title}\n{desc}")
        return True
    key = _jira_create_issue(cfg, title, desc, ["airaider"])
    print(f"jira: created {key}  ({title})")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--run",
        type=Path,
        help="run directory (default: latest under ai-raider_runs/)",
    )
    parser.add_argument(
        "--min-severity",
        choices=SEVERITY_ORDER,
        help="only notify when at least one finding is this severity or higher",
    )
    parser.add_argument(
        "--jira-per-finding",
        action="store_true",
        help="one Jira issue per high/critical finding",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be sent; send nothing",
    )
    args = parser.parse_args()

    run_dir = args.run or _latest_run(_repo_root() / RUNS_DIR)
    if run_dir is None or not run_dir.is_dir():
        print(f"no run directory found (looked in {RUNS_DIR}/)", file=sys.stderr)
        return 1

    summary = summarize(run_dir)

    if args.min_severity:
        highest = _highest_severity(summary)
        threshold = SEVERITY_RANK[args.min_severity]
        if highest is None or SEVERITY_RANK[highest] > threshold:
            print(f"below --min-severity {args.min_severity}; nothing to send")
            return 0

    sent_webhook = send_webhook(summary, dry_run=args.dry_run)
    sent_jira = send_jira(summary, per_finding=args.jira_per_finding, dry_run=args.dry_run)

    if not (sent_webhook or sent_jira):
        print(
            "nothing sent: set AIRAIDER_WEBHOOK_URL and/or JIRA_URL+JIRA_TOKEN+JIRA_PROJECT",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

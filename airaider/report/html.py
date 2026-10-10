"""Self-contained, shareable HTML report.

Emits a single ``report.html`` with everything inlined (no external CSS/JS/fonts),
so a run's results can be opened offline or sent to a stakeholder as one file. It
is produced automatically alongside the markdown/CSV/SARIF artifacts, and can be
regenerated from a run directory with ``scripts/export-html.py``.

Template labels are bilingual via :mod:`airaider.report.i18n` (the run's
``report_lang``); model-produced content is shown as-is. All dynamic values are
HTML-escaped — vulnerability fields quote attacker-influenced text.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from airaider.report.i18n import set_report_lang, t


if TYPE_CHECKING:
    from pathlib import Path

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEVERITY_NAMES = ["critical", "high", "medium", "low", "info"]

# Palette shared by the summary bar, badges and card accents (light + dark safe).
_SEVERITY_COLOR = {
    "critical": "#b4232a",
    "high": "#c2410c",
    "medium": "#a16207",
    "low": "#1d4ed8",
    "info": "#4b5563",
}

_CSS = """
:root{color-scheme:light dark;
  --bg:#f6f7f9;--card:#ffffff;--fg:#1a1d23;--muted:#5b6370;--line:#e3e6ea;--code:#f2f3f5;}
@media (prefers-color-scheme:dark){:root{
  --bg:#0f1115;--card:#171a21;--fg:#e6e8ec;--muted:#9aa3b0;--line:#272b33;--code:#1f232b;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px 80px}
header.top{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:24px}
.brand{font-weight:700;letter-spacing:.3px;font-size:18px}
.kicker{color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;font-size:11px;
  margin-top:4px}
h1{font-size:26px;margin:8px 0 4px}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;
  margin-top:18px}
.meta .k{color:var(--muted);text-transform:uppercase;letter-spacing:.8px;font-size:10px}
.meta .v{font-weight:600;word-break:break-word}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 4px}
.pill{display:inline-flex;align-items:center;gap:7px;padding:6px 12px;border-radius:999px;
  background:var(--card);border:1px solid var(--line);font-weight:600;font-size:13px}
.dot{width:10px;height:10px;border-radius:50%}
h2.sec{font-size:18px;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.exec{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
  white-space:pre-wrap;word-break:break-word}
.card{background:var(--card);border:1px solid var(--line);border-left-width:5px;border-radius:10px;
  padding:18px 20px;margin:14px 0}
.card h3{margin:0 0 4px;font-size:17px}
.badge{display:inline-block;color:#fff;padding:2px 9px;border-radius:6px;font-size:11px;
  font-weight:700;letter-spacing:.5px;vertical-align:middle}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px 16px;
  margin:12px 0}
.grid .k{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.6px}
.grid .v{word-break:break-word}
.block h4{margin:14px 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.6px;
  color:var(--muted)}
.block p{margin:4px 0;white-space:pre-wrap;word-break:break-word}
pre{background:var(--code);border:1px solid var(--line);border-radius:8px;padding:12px 14px;
  overflow:auto;font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.loc{font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);
  margin-top:10px}
footer{margin-top:48px;color:var(--muted);font-size:12px;text-align:center}
""".strip()


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _severity(report: dict[str, Any]) -> str:
    sev = str(report.get("severity", "info")).strip().lower()
    return sev if sev in _SEVERITY_ORDER else "info"


def _targets(run_record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for info in run_record.get("targets_info", []) or []:
        if isinstance(info, dict):
            out.append(str(info.get("target") or info.get("value") or "").strip())
        elif isinstance(info, str):
            out.append(info.strip())
    return [x for x in out if x]


def _meta_row(key: str, value: Any) -> str:
    return f'<div><div class="k">{_esc(key)}</div><div class="v">{_esc(value)}</div></div>'


def _header(run_record: dict[str, Any], counts: dict[str, int]) -> str:
    targets = _targets(run_record)
    usage = run_record.get("llm_usage") or {}
    cost = usage.get("cost") if isinstance(usage, dict) else None

    rows = [
        _meta_row(t("m_run"), run_record.get("run_name") or run_record.get("run_id") or "—"),
        _meta_row(t("m_status"), run_record.get("status", "—")),
    ]
    if run_record.get("scan_mode"):
        rows.append(_meta_row(t("m_scan_mode"), run_record["scan_mode"]))
    if targets:
        rows.append(_meta_row(t("m_target"), ", ".join(targets)))
    if run_record.get("start_time"):
        rows.append(_meta_row(t("m_started"), run_record["start_time"]))
    if run_record.get("end_time"):
        rows.append(_meta_row(t("m_completed"), run_record["end_time"]))
    if isinstance(cost, int | float):
        rows.append(_meta_row(t("llm_cost"), f"${cost:.2f}"))

    pills = []
    for name in _SEVERITY_NAMES:
        if counts.get(name):
            color = _SEVERITY_COLOR[name]
            pills.append(
                f'<span class="pill"><span class="dot" style="background:{color}"></span>'
                f"{_esc(name.title())}: {counts[name]}</span>"
            )
    if not pills:
        pills.append(f'<span class="pill">{_esc(t("no_findings"))}</span>')

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        '<header class="top">'
        f'<div class="brand">{_esc(t("brand"))}</div>'
        f'<div class="kicker">{_esc(t("pdf_kicker"))}</div>'
        f"<h1>{_esc(t('pdf_cover_title'))}</h1>"
        f'<div class="kicker">{_esc(t("generated"))}: {_esc(generated)}</div>'
        f'<div class="meta">{"".join(rows)}</div>'
        f'<div class="bar">{"".join(pills)}</div>'
        "</header>"
    )


def _text_block(label: str, value: Any) -> str:
    if not value:
        return ""
    return f'<div class="block"><h4>{_esc(label)}</h4><p>{_esc(value)}</p></div>'


def _code_block(label: str, code: Any) -> str:
    if not code:
        return ""
    return f'<div class="block"><h4>{_esc(label)}</h4><pre>{_esc(code)}</pre></div>'


def _finding_meta(report: dict[str, Any]) -> str:
    dep = report.get("dependency_metadata") or {}
    pairs: list[tuple[str, Any]] = [
        ("ID", report.get("id")),
        (t("detected"), report.get("timestamp")),
        (t("target"), report.get("target")),
        (t("endpoint"), report.get("endpoint")),
        (t("method"), report.get("method")),
        ("CVE", report.get("cve")),
        ("CWE", report.get("cwe")),
        ("CVSS", report.get("cvss")),
        (t("confidence"), report.get("confidence")),
        (t("fix_effort"), report.get("fix_effort")),
        (t("package"), dep.get("package_name") if isinstance(dep, dict) else None),
        (t("fixed_version"), dep.get("fixed_version") if isinstance(dep, dict) else None),
    ]
    cells = [
        f'<div><div class="k">{_esc(k)}</div><div class="v">{_esc(v)}</div></div>'
        for k, v in pairs
        if v not in (None, "", [])
    ]
    return f'<div class="grid">{"".join(cells)}</div>' if cells else ""


def _code_locations(report: dict[str, Any]) -> str:
    locs = report.get("code_locations")
    if not isinstance(locs, list) or not locs:
        return ""
    parts = [f'<div class="block"><h4>{_esc(t("code_analysis"))}</h4>']
    for loc in locs:
        if not isinstance(loc, dict):
            continue
        ref = _esc(loc.get("file", "unknown"))
        line = ""
        if loc.get("start_line") is not None:
            end = loc.get("end_line")
            if end and end != loc["start_line"]:
                line = f" ({_esc(t('lines'))} {_esc(loc['start_line'])}-{_esc(end)})"
            else:
                line = f" ({_esc(t('line'))} {_esc(loc['start_line'])})"
        parts.append(f'<div class="loc">{ref}{line}</div>')
        if loc.get("snippet"):
            parts.append(f"<pre>{_esc(loc['snippet'])}</pre>")
    parts.append("</div>")
    return "".join(parts)


def _finding_card(report: dict[str, Any]) -> str:
    sev = _severity(report)
    color = _SEVERITY_COLOR[sev]
    title = report.get("title") or t("untitled_finding")
    badge = f'<span class="badge" style="background:{color}">{_esc(sev.upper())}</span>'
    body = [
        f'<div class="card" style="border-left-color:{color}">',
        f"<h3>{badge} {_esc(title)}</h3>",
        _finding_meta(report),
        _text_block(t("description"), report.get("description") or t("no_description")),
        _text_block(t("impact"), report.get("impact")),
        _text_block(t("evidence"), report.get("evidence")),
        _text_block(t("technical_analysis"), report.get("technical_analysis")),
        _text_block(t("poc"), report.get("poc_description")),
        _code_block(t("poc_script"), report.get("poc_script_code")),
        _code_locations(report),
        _text_block(t("remediation"), report.get("remediation_steps")),
        "</div>",
    ]
    return "".join(part for part in body if part)


def render_html_report(
    run_record: dict[str, Any],
    vulnerability_reports: list[dict[str, Any]],
    exec_summary: str | None = None,
) -> str:
    """Return a complete, self-contained HTML document for a run."""
    reports = [r for r in vulnerability_reports if isinstance(r, dict)]
    counts = dict.fromkeys(_SEVERITY_NAMES, 0)
    for report in reports:
        counts[_severity(report)] += 1

    ordered = sorted(
        reports,
        key=lambda r: (_SEVERITY_ORDER[_severity(r)], str(r.get("timestamp", ""))),
    )

    sections = [_header(run_record, counts)]
    if exec_summary and exec_summary.strip():
        sections.append(f'<h2 class="sec">{_esc(t("exec_summary"))}</h2>')
        sections.append(f'<div class="exec">{_esc(exec_summary.strip())}</div>')

    sections.append(f'<h2 class="sec">{_esc(t("findings_section"))}</h2>')
    if ordered:
        sections.append(t("total_findings_fmt").format(n=len(ordered)))
        sections.extend(_finding_card(r) for r in ordered)
    else:
        sections.append(f"<p>{_esc(t('no_findings'))}</p>")

    body = "".join(sections)
    lang = run_record.get("report_lang") or "en"
    return (
        "<!doctype html>"
        f'<html lang="{_esc(lang)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(t('pdf_doc_title'))}</title>"
        f"<style>{_CSS}</style></head>"
        f'<body><div class="wrap">{body}'
        f'<footer>{_esc(t("brand"))} · {_esc(t("confidential"))}</footer>'
        "</div></body></html>"
    )


def write_html_report(
    run_dir: Path,
    run_record: dict[str, Any],
    vulnerability_reports: list[dict[str, Any]],
    exec_summary: str | None = None,
) -> Path:
    """Write ``report.html`` into ``run_dir`` and return its path."""
    path = run_dir / "report.html"
    path.write_text(
        render_html_report(run_record, vulnerability_reports, exec_summary),
        encoding="utf-8",
    )
    return path


def _read_exec_summary(run_dir: Path) -> str | None:
    md = run_dir / "penetration_test_report.md"
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return None
    # Drop the markdown title + generated line; keep the body the model produced.
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines[:5]):
        if line.startswith(("**", "# ")):
            start = i + 1
    return "\n".join(lines[start:]).strip() or None


def write_html_report_from_dir(run_dir: Path, lang: str | None = None) -> Path:
    """Regenerate ``report.html`` from a run directory's JSON artifacts.

    ``lang`` overrides the template language; otherwise the run's own
    ``report_lang`` is used (falling back to the process default).
    """
    run_record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    chosen = lang or run_record.get("report_lang")
    if chosen:
        set_report_lang(chosen)
    try:
        vulns = json.loads((run_dir / "vulnerabilities.json").read_text(encoding="utf-8"))
    except OSError:
        vulns = []
    if not isinstance(vulns, list):
        vulns = []
    return write_html_report(run_dir, run_record, vulns, _read_exec_summary(run_dir))

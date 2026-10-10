"""Tests for the self-contained HTML report."""

from __future__ import annotations

import json

import pytest

from airaider.report.html import (
    render_html_report,
    write_html_report_from_dir,
)
from airaider.report.i18n import set_report_lang


RUN_RECORD = {
    "run_name": "demo",
    "run_id": "AIRAIDER-xyz",
    "status": "completed",
    "scan_mode": "deep",
    "targets_info": [{"target": "https://shop.example"}],
    "llm_usage": {"cost": 7.25},
}

VULNS = [
    {
        "id": "V1",
        "title": "SQLi in /login",
        "severity": "critical",
        "timestamp": "2026-10-10T10:01:00Z",
        "endpoint": "/login",
        "cwe": "CWE-89",
        "description": "the <user> param is injectable & breaks auth",
        "poc_script_code": "curl -d \"u=' OR 1=1--\" https://shop.example/login",
    },
    {"id": "V2", "title": "Low thing", "severity": "low", "timestamp": "t"},
]


@pytest.fixture(autouse=True)
def _default_lang() -> None:
    set_report_lang("en")


def test_render_includes_findings_and_counts() -> None:
    html = render_html_report(RUN_RECORD, VULNS, "exec body")
    assert "<!doctype html>" in html.lower()
    assert "SQLi in /login" in html
    assert "Critical: 1" in html
    assert "Low: 1" in html
    assert "exec body" in html
    assert "$7.25" in html


def test_user_content_is_escaped() -> None:
    html = render_html_report(RUN_RECORD, VULNS, None)
    # Attacker-influenced fields must not reach the DOM as live markup.
    assert "<user>" not in html
    assert "&lt;user&gt;" in html
    assert "' OR 1=1" not in html
    assert "&#x27; OR 1=1" in html


def test_no_findings_message() -> None:
    html = render_html_report(RUN_RECORD, [], None)
    assert "No findings" in html


def test_report_lang_switches_labels() -> None:
    set_report_lang("ru")
    html = render_html_report(RUN_RECORD, VULNS, None)
    assert "Стоимость LLM" in html
    assert 'lang="ru"' not in html  # run_record has no report_lang -> default lang attr


def test_write_from_dir_honors_run_report_lang(tmp_path) -> None:
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(
        json.dumps({**RUN_RECORD, "report_lang": "ru"}), encoding="utf-8"
    )
    (run_dir / "vulnerabilities.json").write_text(json.dumps(VULNS), encoding="utf-8")

    out = write_html_report_from_dir(run_dir)
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert 'lang="ru"' in html
    assert "Стоимость LLM" in html

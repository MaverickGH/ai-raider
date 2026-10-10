#!/usr/bin/env python3
"""Regenerate a run's self-contained ``report.html`` from its artifacts.

AiRaider already writes ``report.html`` automatically next to every run's other
outputs. Use this to rebuild it for an older run, or in a different report
language without re-scanning:

  scripts/export-html.py                     # latest run under ai-raider_runs/
  scripts/export-html.py --run <dir>         # a specific run directory
  scripts/export-html.py --report-lang ru    # force the template language

The HTML is a single file with all CSS inlined — open it offline or share it as-is.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


RUNS_DIR = "ai-raider_runs"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.is_dir():
        return None
    candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--run", type=Path, help="run directory (default: latest)")
    parser.add_argument(
        "--report-lang",
        choices=("en", "ru"),
        help="override the template language (default: the run's own report_lang)",
    )
    args = parser.parse_args()

    run_dir = args.run or _latest_run(_repo_root() / RUNS_DIR)
    if run_dir is None or not run_dir.is_dir():
        print(f"no run directory found (looked in {RUNS_DIR}/)", file=sys.stderr)
        return 1

    # Imported lazily so --help works without the package environment.
    from airaider.report.html import write_html_report_from_dir

    out = write_html_report_from_dir(run_dir, lang=args.report_lang)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

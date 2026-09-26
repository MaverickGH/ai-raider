#!/usr/bin/env bash
# AI-Raider — one-command install for self-hosting.
# Checks prerequisites, installs the tool from source, creates .env from the template.
# Usage:  ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\033[36m%s\033[0m\n' "$*"; }
ok()   { printf '\033[32m* %s\033[0m\n' "$*"; }
warn() { printf '\033[33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[31mx %s\033[0m\n' "$*" >&2; exit 1; }

say "AI-Raider - install"

# 1. Python 3.12+
if command -v python3 >/dev/null 2>&1; then
  PYV="$(python3 -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  case "$PYV" in
    3.1[2-9]|3.[2-9][0-9]) ok "Python $PYV" ;;
    *) die "Python 3.12+ required, found $PYV. Install a newer one: https://www.python.org/downloads/" ;;
  esac
else
  die "Python 3.12+ not found. Install it: https://www.python.org/downloads/"
fi

# 2. Docker (agent sandbox)
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "Docker is running"
  else
    warn "Docker is installed but the daemon is not running - start Docker before scanning."
  fi
else
  warn "Docker not found. It is required for the sandbox: https://docs.docker.com/get-docker/"
fi

# 3. Virtualenv + install (prefer uv, else venv+pip)
if command -v uv >/dev/null 2>&1; then
  say "Installing via uv..."
  uv venv >/dev/null
  uv pip install -e . >/dev/null
else
  say "uv not found - installing via python venv + pip..."
  python3 -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip >/dev/null
  ./.venv/bin/python -m pip install -e . >/dev/null
fi
ok "Tool installed into .venv"

# 4. .env from the template
if [ -f .env ]; then
  ok ".env already exists - leaving it as is"
else
  cp env.example .env
  ok "Created .env from env.example - fill in your model and key"
fi

echo
say "Done. Next:"
echo "  1) Edit .env - uncomment one provider block (your key, any LLM)."
echo "     For no key and no data leaving your machine - the Ollama block (local model)."
echo "  2) Run a scan against your own / authorized target ONLY:"
echo "       ./run-scan.sh https://your-staging quick        # cloud model from .env"
echo "       ./run-scan-local.sh https://your-staging        # local model (Ollama)"
echo "  3) Report and findings are in ai-raider_runs/<run-name>/"
echo
warn "Authorized testing only: your own systems or written permission."

#!/usr/bin/env bash
# AI-Рейдер — установка одной командой для самостоятельного развёртывания.
# Проверяет пререквизиты, ставит инструмент из исходников, создаёт .env из шаблона.
# Использование:  ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\033[36m%s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[33m⚠ %s\033[0m\n' "$*"; }
die()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

say "AI-Рейдер — установка"

# 1. Python 3.12+
if command -v python3 >/dev/null 2>&1; then
  PYV="$(python3 -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  case "$PYV" in
    3.1[2-9]|3.[2-9][0-9]) ok "Python $PYV" ;;
    *) die "Нужен Python 3.12+, найден $PYV. Установи новее: https://www.python.org/downloads/" ;;
  esac
else
  die "Python 3.12+ не найден. Установи: https://www.python.org/downloads/"
fi

# 2. Docker (песочница агентов)
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "Docker запущен"
  else
    warn "Docker установлен, но демон не запущен — запусти Docker перед сканом."
  fi
else
  warn "Docker не найден. Он нужен для песочницы: https://docs.docker.com/get-docker/"
fi

# 3. Виртуальное окружение + установка (предпочитаем uv, иначе venv+pip)
if command -v uv >/dev/null 2>&1; then
  say "Ставлю через uv…"
  uv venv >/dev/null
  uv pip install -e . >/dev/null
else
  say "uv не найден — ставлю через python venv + pip…"
  python3 -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip >/dev/null
  ./.venv/bin/python -m pip install -e . >/dev/null
fi
ok "Инструмент установлен в .venv"

# 4. .env из шаблона
if [ -f .env ]; then
  ok ".env уже есть — не трогаю"
else
  cp env.example .env
  ok "Создал .env из env.example — впиши свою модель и ключ"
fi

echo
say "Готово. Дальше:"
echo "  1) Отредактируй .env — раскомментируй один блок провайдера (свой ключ, любой LLM)."
echo "     Без ключа и без утечки данных — блок Ollama (локальная модель)."
echo "  2) Запусти скан ТОЛЬКО по своей/разрешённой цели:"
echo "       ./run-scan.sh https://твой-стенд quick        # облачная модель из .env"
echo "       ./run-scan-local.sh https://твой-стенд        # локальная модель (Ollama)"
echo "  3) Отчёт и находки — в ai-raider_runs/<имя-прогона>/"
echo
warn "Только авторизованное тестирование: свои системы или письменное разрешение."

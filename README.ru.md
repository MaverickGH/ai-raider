# AI-Рейдер

**Русский** · [English](README.md)

> Автономный AI-пентест. Форк [usestrix/strix](https://github.com/usestrix/strix) (Apache-2.0), переработанный для self-hosted-запуска с любой моделью.

AI-Рейдер — это команда автономных AI-агентов, которые проводят пентест как настоящие исследователи: ведут разведку, запускают код в песочнице, находят уязвимости и подтверждают их рабочими proof-of-concept, а затем предлагают исправления.

**Только для авторизованного тестирования.** Запускайте AI-Рейдер исключительно против собственных систем или целей, на которые у вас есть письменное разрешение.

**Развернуть у себя за пару минут** (свой ключ, любой LLM, ничего не уходит наружу) — см. **[SELF-HOST.md](SELF-HOST.md)**:

```bash
git clone https://github.com/MaverickGH/ai-raider && cd ai-raider
./setup.sh            # проверит Docker/Python, поставит инструмент, создаст .env
# впиши модель и ключ в .env (или блок Ollama — без ключа), затем:
./run-scan.sh https://твой-стенд quick
```

## Что это

- Полный набор для пентеста из коробки: разведка, эксплуатация, валидация.
- Мультиагентная оркестрация: команды AI-пентестеров работают параллельно.
- Реальная проверка эксплойтов, а не ложные срабатывания статических сканеров.
- CLI с понятными находками и рекомендациями по устранению.
- Авто-фиксы и отчёты.

## Требования

- Python 3.12+
- Запущенный Docker (песочница для агентов)
- API-ключ LLM (OpenAI, Anthropic, Google, OpenRouter и др. через LiteLLM)

## Установка (из исходников)

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
ai-raider --help
```

## Быстрый старт

```bash
export AIRAIDER_LLM="openrouter/z-ai/glm-5.3"   # любой id модели LiteLLM
export LLM_API_KEY="<ваш ключ>"

# headless-режим по разрешённой цели:
ai-raider -n -t ./путь-к-приложению --scan-mode quick
```

> Интерактивный TUI требует Go-тулчейна для сборки; headless-режим работает без него.

## Отличия от upstream (Strix)

- Ребрендинг в «AI-Рейдер», CLI-команда `ai-raider`, каталог конфигурации `~/.ai-raider`.
- Телеметрия выключена по умолчанию; апселл облака убран из подсказок.
- **Двуязычные отчёты**: подписи/заголовки отчёта — английский по умолчанию или русский через `--report-lang ru` (либо `AIRAIDER_REPORT_LANG`); содержимое от модели — как есть.
- **Свой sandbox-образ** `ai-raider-sandbox:0.1.0` (см. `containers/build-sandbox.sh`), не зависит от тега upstream при запуске.
- **Локальные модели**: пресет `run-scan-local.sh` для Ollama/LM Studio без облачного ключа.

## Быстрые команды

```bash
./run-scan.sh https://staging.твой-домен quick     # облачная модель (AIRAIDER_LLM + ключ провайдера)
./run-scan-local.sh https://staging.твой-домен      # локальная модель (Ollama), без облака

# свой sandbox-образ:
./containers/build-sandbox.sh          # быстрый брендированный (на базе upstream)
./containers/build-sandbox.sh --full   # полностью независимый из Kali-Dockerfile (долго)
```

## Ключ через Keychain (macOS)

Чтобы не держать ключ в открытом виде и не экспортировать его каждый раз, храни его в macOS Keychain — `run-scan.sh` подтянет автоматически:

```bash
./scripts/keychain-set.sh OPENAI_API_KEY            # вставь ключ скрытым вводом
./scripts/keychain-set.sh AIRAIDER_LLM openai/gpt-5.4 # модель
./run-scan.sh https://разрешённая-цель standard      # ключ/модель берутся из Keychain
```

Поддерживаются `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `AIRAIDER_LLM`, `LLM_API_BASE` (сервис `ai-raider.local.<ИМЯ>`). Значение ключа вводится скрыто и нигде не печатается.

## Использование в CI (GitHub Actions)

Подключи AI-Raider в любой workflow composite-action'ом — он запускает скан и отдаёт SARIF-отчёт (пинь на `@v1` для последней v1.x или `@v1.0.0`, чтобы зафиксировать точный релиз):

```yaml
- uses: MaverickGH/ai-raider@v1
  id: airaider
  with:
    target: ./                       # URL, домен, IP или путь к коду
    scan-mode: quick                 # quick | standard | deep
    model: anthropic/claude-sonnet-5 # любой id LiteLLM
    max-budget: "10"
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}   # ключ провайдера под твою модель
```

Job падает на подтверждённых находках (`fail-on-findings: "false"` — только отчёт). Загрузить результат в code scanning через output `sarif`:

```yaml
- uses: github/codeql-action/upload-sarif@v3
  if: always()                       # загрузить даже если скан упал на находках
  with:
    sarif_file: ${{ steps.airaider.outputs.sarif }}
```

## HTML-отчёт для шаринга

Каждый прогон также пишет один автономный файл `report.html` (весь CSS внутри, светлая/тёмная тема, двуязычный) рядом с остальными артефактами — открой офлайн или отправь как единый файл. Пересобрать для старого прогона или на другом языке без повторного скана:

```bash
python3 scripts/export-html.py                 # последний прогон
python3 scripts/export-html.py --run <dir> --report-lang ru
```

## Экспорт находок в DefectDojo

Каждый прогон пишет `findings.sarif` (SARIF 2.1.0) — загрузи его в GitHub code scanning или сразу в [DefectDojo](https://www.defectdojo.org/):

```bash
export DEFECTDOJO_URL=https://defectdojo.example.com
export DEFECTDOJO_API_KEY=...
export DEFECTDOJO_PRODUCT="My App"            # product + engagement создадутся автоматически
export DEFECTDOJO_ENGAGEMENT_NAME="AI-Raider scan"
python3 scripts/export-defectdojo.py          # последний прогон; работают и --run <кат> / --dry-run
```

Или укажи существующий engagement: `DEFECTDOJO_ENGAGEMENT=<id>`.

## Уведомления в Slack / Teams / Jira

Отправляй сводку по прогону (кол-во по severity, статус, стоимость, топ находок) в чат-вебхук и/или заводи задачи в Jira — только stdlib, без зависимостей:

```bash
# Чат-вебхук (Slack / Mattermost / Teams / Google Chat / любой JSON-эндпоинт)
export AIRAIDER_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
export AIRAIDER_WEBHOOK_FORMAT=slack            # slack | teams | gchat | json
python3 scripts/notify.py                        # последний прогон; есть и --run <dir>

# Пинговать только при серьёзных находках
python3 scripts/notify.py --min-severity high

# Заводить задачи в Jira (одна сводная или по одной на high/critical через --jira-per-finding)
export JIRA_URL=https://acme.atlassian.net
export JIRA_USER=you@acme.io                      # опусти для «голого» PAT (Server/DC)
export JIRA_TOKEN=...                             # API-токен / personal access token
export JIRA_PROJECT=SEC
python3 scripts/notify.py --jira-per-finding
```

Добавь `--dry-run`, чтобы увидеть сообщение, ничего не отправляя. Вешай вызов после скана в CI или в cron.

## Лицензия

Apache License 2.0 — см. [LICENSE](LICENSE) и [NOTICE](NOTICE). Основано на Strix (© Strix), с сохранением авторства согласно условиям лицензии.

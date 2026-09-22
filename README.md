# AI-Рейдер

> Автономный AI-пентест. Форк [usestrix/strix](https://github.com/usestrix/strix) (Apache-2.0), доработанный под наши задачи.

AI-Рейдер — это команда автономных AI-агентов, которые проводят пентест как настоящие исследователи: ведут разведку, запускают код в песочнице, находят уязвимости и подтверждают их рабочими proof-of-concept, а затем предлагают исправления.

**Только для авторизованного тестирования.** Запускайте AI-Рейдер исключительно против собственных систем или целей, на которые у вас есть письменное разрешение.

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
export STRIX_LLM="openrouter/z-ai/glm-5.3"   # любой id модели LiteLLM
export LLM_API_KEY="<ваш ключ>"

# headless-режим по разрешённой цели:
ai-raider -n -t ./путь-к-приложению --scan-mode quick
```

> Интерактивный TUI требует Go-тулчейна для сборки; headless-режим работает без него.

## Отличия от upstream (Strix)

- Ребрендинг в «AI-Рейдер», CLI-команда `ai-raider`, каталог конфигурации `~/.ai-raider`.
- Телеметрия выключена по умолчанию; апселл облака убран из подсказок.
- **Русские отчёты**: markdown-отчёт о пентесте и карточки уязвимостей на русском (значения от модели — как есть).
- **Свой sandbox-образ** `ai-raider-sandbox:0.1.0` (см. `containers/build-sandbox.sh`), не зависит от тега upstream при запуске.
- **Локальные модели**: пресет `run-scan-local.sh` для Ollama/LM Studio без облачного ключа.

## Быстрые команды

```bash
./run-scan.sh https://staging.твой-домен quick     # облачная модель (STRIX_LLM + ключ провайдера)
./run-scan-local.sh https://staging.твой-домен      # локальная модель (Ollama), без облака

# свой sandbox-образ:
./containers/build-sandbox.sh          # быстрый брендированный (на базе upstream)
./containers/build-sandbox.sh --full   # полностью независимый из Kali-Dockerfile (долго)
```

## Ключ через Keychain (macOS)

Чтобы не держать ключ в открытом виде и не экспортировать его каждый раз, храни его в macOS Keychain — `run-scan.sh` подтянет автоматически:

```bash
./scripts/keychain-set.sh OPENAI_API_KEY            # вставь ключ скрытым вводом
./scripts/keychain-set.sh STRIX_LLM openai/gpt-5.4  # модель
./run-scan.sh https://разрешённая-цель standard      # ключ/модель берутся из Keychain
```

Поддерживаются `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `STRIX_LLM`, `LLM_API_BASE` (сервис `ai-raider.local.<ИМЯ>`). Значение ключа вводится скрыто и нигде не печатается.

## Интеграция с Cyber Galaxy

Находки прогона попадают в приватную админку платформы Cyber Galaxy (раздел «Пентест-находки», только для владельцев). Два пути:

**Прямой пуш (без ручной загрузки файла).** Задай URL платформы — и находки уйдут в неё автоматически:

```bash
export CG_PLATFORM_URL=http://localhost:3000   # адрес платформы
export CG_AUTH_COOKIE=<owner-cookie cg_auth>   # в production; в dev не нужен при ADMIN_DEV_BYPASS=1
./scripts/export-findings.sh                   # соберёт тело и запушит находки последнего прогона
```

Тонкий контроль — напрямую через bridge-скрипт:

```bash
python3 scripts/push_findings.py               # последний прогон
python3 scripts/push_findings.py --run <кат>   # конкретный прогон
python3 scripts/push_findings.py --dry-run     # собрать тело и показать, не отправляя
```

**Вручную.** Без `CG_PLATFORM_URL` скрипт лишь покажет путь к `vulnerabilities.json`; дальше в админке: **Пентест-находки → Импорт прогона** — загрузи `vulnerabilities.json` (и по желанию `penetration_test_report.md`).

Находки чувствительные и в публичный контент не попадают.

## Лицензия

Apache License 2.0 — см. [LICENSE](LICENSE) и [NOTICE](NOTICE). Основано на Strix (© Strix), с сохранением авторства согласно условиям лицензии.

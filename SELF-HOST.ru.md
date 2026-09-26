# Развернуть AI-Рейдер у себя (свой ключ, любой LLM)

**Русский** · [English](SELF-HOST.md)

AI-Рейдер — полностью self-hosted инструмент: он работает на вашей машине, в своей
Docker-песочнице, с **вашей** моделью и **вашим** ключом. Никакой регистрации и
нашего сервера не нужно. Данные никуда не уходят (а с локальной моделью — вообще
остаются на вашем компьютере).

> **Только авторизованное тестирование.** Сканируйте лишь свои системы или цели,
> на которые у вас есть письменное разрешение.

## Что нужно

- **Docker** — песочница, в которой работают агенты. [Как поставить](https://docs.docker.com/get-docker/)
- **Python 3.12+**
- **Модель**: ключ любого провайдера (OpenAI, Anthropic, Google Gemini, OpenRouter и
  др.) **или** локальная модель через Ollama — без ключа и без утечки данных.

## Установка за один шаг

```bash
git clone https://github.com/MaverickGH/ai-raider && cd ai-raider
./setup.sh
```

`setup.sh` проверит Docker и Python, поставит инструмент в `.venv` и создаст `.env`
из шаблона. Дальше остаётся вписать модель и ключ.

<details>
<summary>Вручную, без setup.sh</summary>

```bash
uv venv && uv pip install -e .      # или: python3 -m venv .venv && ./.venv/bin/pip install -e .
cp env.example .env
```
</details>

## Выбор модели — любой LLM

Откройте `.env` и раскомментируйте **один** блок провайдера (уберите `#`):

| Провайдер | В `.env` |
|---|---|
| OpenAI | `AIRAIDER_LLM=openai/gpt-5.4` + `OPENAI_API_KEY=…` |
| Anthropic (Claude) | `AIRAIDER_LLM=anthropic/claude-sonnet-5` + `ANTHROPIC_API_KEY=…` |
| Google Gemini (есть бесплатный тариф) | `AIRAIDER_LLM=gemini/gemini-2.5-pro` + `GEMINI_API_KEY=…` |
| OpenRouter (много моделей одним ключом) | `AIRAIDER_LLM=openrouter/z-ai/glm-5.3` + `OPENROUTER_API_KEY=…` |
| Локально (Ollama), без ключа | `AIRAIDER_LLM=ollama/qwen2.5:32b` + `LLM_API_BASE=http://localhost:11434` |
| Любой OpenAI-совместимый (LM Studio, vLLM, шлюз) | `AIRAIDER_LLM=openai/<модель>` + `LLM_API_KEY=…` + `LLM_API_BASE=…` |

Модель — любой id [LiteLLM](https://docs.litellm.ai/docs/providers). Свой ключ и
свои деньги на модель — под вашим контролем, не у нас.

> **Совет по стоимости.** Агентный цикл делает сотни вызовов модели. Бесплатные
> тарифы (напр. лимит Gemini) быстро упираются в квоту. Для завершённого скана нужна
> модель с нормальным лимитом или локальная Ollama.

## Запуск скана

Только по своей/разрешённой цели:

```bash
./run-scan.sh https://ваш-стенд quick        # облачная модель из .env
./run-scan-local.sh https://ваш-стенд        # локальная модель (Ollama)
```

Режимы: `quick` (минуты), `standard`, `deep` (может идти часами — запускайте в фоне).
Цель — URL, домен, IP или путь к коду (`./`).

## Результаты

Всё пишется в `ai-raider_runs/<имя-прогона>/`:

| Файл | Что |
|---|---|
| `penetration_test_report.md` | Отчёт — читать первым |
| `vulnerabilities/*.md` | По файлу на находку: PoC и как чинить |
| `vulnerabilities.json` / `.csv` | Находки структурно |
| `findings.sarif` | SARIF 2.1.0 для GitHub code scanning |

Смотреть в браузере: `ai-raider view`.

> Подписи/заголовки отчёта по умолчанию на английском. Для русского добавьте
> `--report-lang ru` (или задайте `AIRAIDER_REPORT_LANG=ru`). Содержимое от модели —
> как есть в любом случае.

## Локально, без утечки данных

Если данные не должны покидать машину — модель через Ollama:

```bash
ollama serve
ollama pull qwen2.5:32b
./run-scan-local.sh ./ quick
```

Ни ключа, ни облака — весь пайплайн на вашем железе.

## Ответственность

Это наступательный инструмент. Запуская его, вы отвечаете за то, что имеете право
тестировать цель. По умолчанию тестируйте код и стейджинг, продакшн — осторожно.

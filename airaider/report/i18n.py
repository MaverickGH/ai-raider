"""Report template i18n (bilingual pentest reports).

Only the report *template* labels/headers are translated here. The model-produced
content (titles, descriptions, PoC, etc.) is written as-is in whatever language the
model returned it.

The report language is a single per-run setting, chosen at startup from
``--report-lang`` (or ``AIRAIDER_REPORT_LANG``), default ``en``. It is a module-level
setting because report writing happens once, in the host process, after the flag is
known — so there is no need to thread it through every call site.
"""

from __future__ import annotations

import os

REPORT_LANGS = ("en", "ru")
_DEFAULT = "en"

LABELS: dict[str, dict[str, str]] = {
    # --- executive report ---
    "report_title": {"en": "Penetration test report", "ru": "Отчёт о тестировании на проникновение"},
    "generated": {"en": "Generated", "ru": "Сформирован"},
    # --- vulnerability card: header ---
    "untitled": {"en": "Untitled vulnerability", "ru": "Уязвимость без названия"},
    "severity": {"en": "Severity", "ru": "Критичность"},
    "detected": {"en": "Detected", "ru": "Обнаружено"},
    # --- vulnerability card: metadata labels ---
    "target": {"en": "Target", "ru": "Цель"},
    "package": {"en": "Package", "ru": "Пакет"},
    "ecosystem": {"en": "Ecosystem", "ru": "Экосистема"},
    "installed_version": {"en": "Installed version", "ru": "Установленная версия"},
    "fixed_version": {"en": "Fixed version", "ru": "Исправленная версия"},
    "introduced_by": {"en": "Introduced by", "ru": "Внесено"},
    "dependency_path": {"en": "Dependency chain", "ru": "Цепочка зависимостей"},
    "endpoint": {"en": "Endpoint", "ru": "Эндпоинт"},
    "method": {"en": "Method", "ru": "Метод"},
    "advisory_cvss": {"en": "Advisory CVSS", "ru": "CVSS бюллетеня"},
    "contextual_cvss_vector": {"en": "Contextual CVSS vector", "ru": "Контекстный вектор CVSS"},
    "confidence": {"en": "Confidence", "ru": "Уверенность"},
    "fix_effort": {"en": "Fix effort", "ru": "Трудоёмкость фикса"},
    # --- vulnerability card: section headers ---
    "description": {"en": "Description", "ru": "Описание"},
    "no_description": {"en": "No description provided.", "ru": "Описание не предоставлено."},
    "evidence": {"en": "Evidence", "ru": "Доказательства"},
    "impact": {"en": "Impact", "ru": "Влияние"},
    "counterevidence": {"en": "Counter-evidence", "ru": "Контрдоказательства"},
    "confidence_rationale": {"en": "Confidence rationale", "ru": "Обоснование уверенности"},
    "severity_change": {"en": "What would change the severity", "ru": "Что изменит критичность"},
    "technical_analysis": {"en": "Technical analysis", "ru": "Технический анализ"},
    "contextual_cvss": {"en": "Contextual CVSS", "ru": "Контекстный CVSS"},
    "code_analysis": {"en": "Code analysis", "ru": "Анализ кода"},
    "location": {"en": "Location", "ru": "Расположение"},
    "lines": {"en": "lines", "ru": "строки"},
    "line": {"en": "line", "ru": "строка"},
    "suggested_fix": {"en": "Suggested fix", "ru": "Предлагаемый фикс"},
    "remediation": {"en": "Remediation", "ru": "Устранение"},
    "fix_verification": {"en": "Fix verification", "ru": "Проверка фикса"},
    "assumptions": {"en": "Assumptions", "ru": "Допущения"},
    # --- update history ---
    "change_history": {"en": "Change history", "ru": "История изменений"},
    "agent": {"en": "agent", "ru": "агент"},
    "updated_fields": {"en": "updated", "ru": "обновил"},
    "removed_stale": {"en": "Removed as stale", "ru": "Убрано как устаревшее"},
    "previous": {"en": "Previous", "ru": "Прежнее"},
    "prev_severity": {"en": "severity", "ru": "критичность"},
    "prev_confidence": {"en": "confidence", "ru": "уверенность"},
    "reason": {"en": "Reason", "ru": "Причина"},
}


def _normalize(lang: str | None) -> str:
    value = (lang or "").strip().lower()
    return value if value in REPORT_LANGS else _DEFAULT


_lang: str = _normalize(os.environ.get("AIRAIDER_REPORT_LANG"))


def set_report_lang(lang: str | None) -> None:
    """Set the process-wide report language (called once at CLI startup)."""
    global _lang
    _lang = _normalize(lang)


def get_report_lang() -> str:
    return _lang


def t(key: str, lang: str | None = None) -> str:
    """Translate a template label. Falls back to English, then to the key itself."""
    entry = LABELS.get(key)
    if not entry:
        return key
    chosen = _normalize(lang) if lang is not None else _lang
    return entry.get(chosen) or entry.get("en") or key

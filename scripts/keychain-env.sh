# Источается из run-scan.sh: экспортирует секреты из macOS Keychain, если они
# ещё не заданы в окружении. Так ключ «запрашивается» из Keychain при каждом запуске.
if [ "$(uname -s)" = "Darwin" ] && command -v security >/dev/null 2>&1; then
  _acct="${USER:-$(id -un)}"
  for _k in OPENAI_API_KEY ANTHROPIC_API_KEY OPENROUTER_API_KEY STRIX_LLM LLM_API_BASE; do
    if [ -z "${!_k:-}" ]; then
      _v="$(security find-generic-password -a "$_acct" -s "ai-raider.local.$_k" -w 2>/dev/null || true)"
      [ -n "$_v" ] && export "$_k=$_v"
    fi
  done
  unset _acct _k _v 2>/dev/null || true
fi

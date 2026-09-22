# Источается из run-scan.sh: экспортирует секреты из macOS Keychain, если не заданы в env.
if [ "$(uname -s)" = "Darwin" ] && command -v security >/dev/null 2>&1; then
  _acct="${USER:-$(id -un)}"
  for _k in OPENAI_API_KEY ANTHROPIC_API_KEY OPENROUTER_API_KEY GEMINI_API_KEY GOOGLE_API_KEY \
            AIRAIDER_LLM AIRAIDER_LLM AIRAIDER_IMAGE AIRAIDER_IMAGE LLM_API_BASE; do
    if [ -z "${!_k:-}" ]; then
      _v="$(security find-generic-password -a "$_acct" -s "ai-raider.local.$_k" -w 2>/dev/null || true)"
      [ -n "$_v" ] && export "$_k=$_v"
    fi
  done
  unset _acct _k _v 2>/dev/null || true
fi

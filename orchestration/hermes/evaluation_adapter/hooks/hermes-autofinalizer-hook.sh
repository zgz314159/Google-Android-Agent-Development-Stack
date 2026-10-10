#!/usr/bin/env bash
# Hermes shell hook: session teardown -> Auto-Finalizer Hermes source adapter (S1.1).
#
# Event: on_session_finalize  (pinned Hermes vgit.af90026 fires it from
#        hermes_cli/lifecycle.py::finalize_session, including the one-shot CLI
#        exit path via cli_shutdown.py::_notify_single_query_session_finalize).
#
# Contract (see agent/shell_hooks.py in the pinned install):
#   stdin  = one JSON payload; `session_id` is a top-level promoted key.
#   stdout = optional JSON directive. This hook is OBSERVER-ONLY: it prints nothing.
#
# Behaviour: extract session_id and launch the ONE-SHOT Auto-Finalizer for that
# session detached, so the hook never blocks or delays the agent turn. All output
# goes to a log file inside the profile, never to the hook's stdout.
set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DEFAULT="$(cd "$HOOK_DIR/../../../.." && pwd)"
REPO="${HERMES_AUTOFINALIZER_REPO:-$REPO_DEFAULT}"
ADAPTER="$REPO/evaluation/commandcode/auto_finalize.py"
PY="$(command -v python3 || echo /usr/bin/python3)"
LOG="${HERMES_AUTOFINALIZER_LOG:-${HERMES_HOME:-$HOME/.hermes}/logs/autofinalizer-hermes.log}"

[ -f "$ADAPTER" ] || exit 0

payload="$(cat)"
sid="$(printf '%s' "$payload" | "$PY" -c 'import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not isinstance(d, dict):
    sys.exit(0)
sid = d.get("session_id") or (d.get("extra") or {}).get("session_id") or ""
sys.stdout.write(str(sid))' 2>/dev/null)"

[ -n "$sid" ] || exit 0

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
{
  printf '[%s] hook on_session_finalize session_id=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$sid"
} >>"$LOG" 2>/dev/null || true

# Detached one-shot: the Auto-Finalizer is idempotent per (source, session_id),
# so a duplicate fire is a NO-OP.
setsid nohup "$PY" "$ADAPTER" hermes-session --session-id "$sid" \
  >>"$LOG" 2>&1 </dev/null &
exit 0

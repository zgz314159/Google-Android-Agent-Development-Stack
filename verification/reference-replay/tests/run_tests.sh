#!/usr/bin/env bash
# Reference Replay test suite: static policy + device lock + offline harness.
set -euo pipefail
T_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RR_HOME="$(cd "$T_DIR/.." && pwd)"
rc=0

echo "== static policy =="
bash "$T_DIR/test_policy_static.sh" || rc=1

echo "== device lock =="
python3 "$T_DIR/test_device_lock.py" || rc=1

echo "== offline harness =="
python3 "$T_DIR/test_replay_offline.py" || rc=1

echo "== hardening (nested screenshot path + fail-fast) =="
python3 "$T_DIR/test_replay_hardening.py" || rc=1

if [ "$rc" -eq 0 ]; then echo "REFERENCE_REPLAY_TESTS=PASS"; else echo "REFERENCE_REPLAY_TESTS=FAIL" >&2; fi
exit "$rc"

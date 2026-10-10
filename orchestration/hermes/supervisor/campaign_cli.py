#!/usr/bin/env python3
"""campaign_cli.py — the Campaign Supervisor CLI.

    python3 orchestration/hermes/supervisor/campaign_cli.py status --campaign-id ID
    python3 orchestration/hermes/supervisor/campaign_cli.py run --campaign-id ID \\
        --milestone MILESTONE --start-sequence N --start-nonce NONCE \\
        --start-in-reply-to HASH --max-rounds N --max-wall-seconds N --poll-seconds N

``run`` stays in the foreground until CLOSED / PAUSED / a safety stop / a limit and
emits compact progress lines only. There is no log-streaming framework, no daemon and
no unbounded loop.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BRIDGE = _HERE.parent / "bridge"
for _p in (str(_HERE), str(_BRIDGE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from . import campaign_state as cstate
    from . import campaign_supervisor as csup
except ImportError:
    import campaign_state as cstate
    import campaign_supervisor as csup

# Conservative bounded-autonomy defaults.
DEFAULT_MAX_ROUNDS = 1
DEFAULT_MAX_WALL_SECONDS = 900
DEFAULT_POLL_SECONDS = 5.0

EXIT_OK = 0


def _cmd_status(args) -> int:
    store = cstate.CampaignStore(args.campaign_id)
    state = store.load()
    payload = {"campaign_id": args.campaign_id, "state_dir": str(store.root)}
    if state is None:
        payload["status"] = "ABSENT"
        payload["journal_entries"] = 0
    else:
        payload["status"] = state.get("status")
        payload["milestone"] = state.get("milestone")
        payload["round_count"] = state.get("round_count")
        payload["max_rounds"] = state.get("max_rounds")
        payload["terminal_outcome"] = state.get("terminal_outcome")
        payload["last_seen_assistant_sha256"] = state.get("last_seen_assistant_sha256")
        payload["last_bridge_result_sha256"] = state.get("last_bridge_result_sha256")
        payload["journal_entries"] = len(store.read_journal())
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return EXIT_OK


def _cmd_run(args) -> int:
    store = cstate.CampaignStore(args.campaign_id)
    supervisor = csup.CampaignSupervisor(
        campaign_id=args.campaign_id,
        milestone=args.milestone,
        start_sequence=args.start_sequence,
        start_nonce=args.start_nonce,
        start_in_reply_to=args.start_in_reply_to,
        max_rounds=args.max_rounds,
        max_wall_seconds=args.max_wall_seconds,
        poll_seconds=args.poll_seconds,
        store=store,
    )
    result = supervisor.run()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return int(result.get("exit_code", 1))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="campaign_cli.py",
        description="GPT <-> Hermes Campaign Supervisor (bounded, one round at a time)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="print one campaign's persisted state")
    p_status.add_argument("--campaign-id", required=True)
    p_status.set_defaults(func=_cmd_status)

    p_run = sub.add_parser("run", help="run one bounded campaign in the foreground")
    p_run.add_argument("--campaign-id", required=True)
    p_run.add_argument("--milestone", required=True)
    p_run.add_argument("--start-sequence", type=int, default=None)
    p_run.add_argument("--start-nonce", default=None)
    p_run.add_argument("--start-in-reply-to", default=None)
    p_run.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    p_run.add_argument("--max-wall-seconds", type=int, default=DEFAULT_MAX_WALL_SECONDS)
    p_run.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    p_run.set_defaults(func=_cmd_run)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

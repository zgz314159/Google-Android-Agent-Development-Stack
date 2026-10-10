#!/usr/bin/env python3
"""Campaign Supervisor — a thin, bounded, stdlib-only wake-up / scheduling layer.

This package schedules one-round-at-a-time wake-ups of the EXISTING GPT <-> Hermes
Bridge for exactly one milestone. It is a scheduling layer only:

  * the Bridge (``orchestration/hermes/bridge/``) remains the sole authority for task
    schema, nonce / sequence / in_reply_to, replay, risk, contract validation, the
    self-modification gate, Contract Guard execution, the durable result transaction
    and the browser send;
  * the Supervisor never executes a Hermes contract, never sends a ChatGPT message
    and never edits Bridge state.

Modules:

  campaign_protocol.py    the separate strict campaign-terminal envelope + classification
  campaign_state.py       private per-campaign state.json / journal.jsonl / campaign.lock
  campaign_supervisor.py  the bounded loop, dispatch policy, reconciliation, fail-closed pause
  campaign_cli.py         the ``status`` and ``run`` subcommands

Standard library only.
"""

from __future__ import annotations

__all__ = [
    "campaign_protocol",
    "campaign_state",
    "campaign_supervisor",
    "campaign_cli",
]

__version__ = "0.1.0"

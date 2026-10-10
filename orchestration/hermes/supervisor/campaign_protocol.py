#!/usr/bin/env python3
"""campaign_protocol.py — the strict campaign-terminal envelope for the Supervisor.

This is a SEPARATE protocol from the Bridge ``HERMES_TASK_V1`` task protocol. The
Bridge task envelope is reused READ-ONLY through ``protocol.extract_control_message``
(imported from the Bridge package); this module never reimplements or extends it and
never reuses the Bridge task envelope for milestone close.

The campaign-terminal markers are composed AT RUNTIME from their components (three
``<`` characters, the protocol name, three ``>`` characters) rather than spelled out
as a literal delimiter string.

This module owns:

  * marker composition + extraction/counting of campaign-terminal envelopes
  * strict JSON decoding (duplicate keys are an error, never last-wins)
  * exact field-set validation (unknown and missing fields both rejected)
  * value validation (protocol / status / outcome) and chain validation
    (campaign_id / milestone / in_reply_to against the current campaign and the
    Bridge ``state.last_result_sha256``)
  * classification of one assistant response into: no control / one candidate Bridge
    task / campaign terminal / malformed / ambiguous / mixed

Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BRIDGE = _HERE.parent / "bridge"
for _p in (str(_HERE), str(_BRIDGE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import protocol as bridge_protocol  # noqa: E402  (Bridge HERMES_TASK_V1, read-only)

# --------------------------------------------------------------------------- #
# Marker composition (runtime, from components)
# --------------------------------------------------------------------------- #

_ANGLE_OPEN = "<" * 3
_ANGLE_CLOSE = ">" * 3

CAMPAIGN_PROTOCOL_NAME = "HERMES_CAMPAIGN_V1"
CAMPAIGN_END_NAME = "END_" + CAMPAIGN_PROTOCOL_NAME

CAMPAIGN_OPEN = _ANGLE_OPEN + CAMPAIGN_PROTOCOL_NAME + _ANGLE_CLOSE
CAMPAIGN_CLOSE = _ANGLE_OPEN + CAMPAIGN_END_NAME + _ANGLE_CLOSE

PROTOCOL_CAMPAIGN = CAMPAIGN_PROTOCOL_NAME

# Exact field set. Unknown fields are rejected (default deny), missing fields are
# rejected, and no field is optional.
CAMPAIGN_FIELDS = (
    "protocol",
    "campaign_id",
    "milestone",
    "status",
    "outcome",
    "in_reply_to",
)

STATUS_VALUES = ("CLOSED", "PAUSED")
OUTCOME_VALUES = (
    "PASS",
    "BLOCKED",
    "FAILED",
    "HUMAN_REQUIRED",
    "SAFETY_STOP",
    "LIMIT_REACHED",
)

# Classification vocabulary for one assistant response.
S_NO_CONTROL = "NO_CONTROL"
S_TASK_CANDIDATE = "TASK_CANDIDATE"
S_CAMPAIGN_TERMINAL = "CAMPAIGN_TERMINAL"
S_CAMPAIGN_INVALID = "CAMPAIGN_INVALID"
S_MALFORMED = "MALFORMED"
S_AMBIGUOUS = "AMBIGUOUS"
S_MIXED = "MIXED"

S_ACCEPTED = "ACCEPTED"
S_REJECTED = "REJECTED"

_BLOCK_RE = re.compile(
    re.escape(CAMPAIGN_OPEN) + r"(.*?)" + re.escape(CAMPAIGN_CLOSE),
    re.DOTALL,
)

# Reused read-only from the Bridge protocol module (no duplicate implementation).
load_json_strict = bridge_protocol.load_json_strict
DuplicateKeyError = bridge_protocol.DuplicateKeyError
sha256_text = bridge_protocol.sha256_text


# --------------------------------------------------------------------------- #
# Extraction + validation
# --------------------------------------------------------------------------- #

def extract_campaign_blocks(text):
    """Return the campaign-terminal blocks and marker counts of one response."""
    if not isinstance(text, str) or not text.strip():
        return {"blocks": [], "opens": 0, "closes": 0, "ambiguous": False}
    blocks = [match.group(1) for match in _BLOCK_RE.finditer(text)]
    opens = text.count(CAMPAIGN_OPEN)
    closes = text.count(CAMPAIGN_CLOSE)
    ambiguous = (len(blocks) != opens) or (opens != closes)
    return {"blocks": blocks, "opens": opens, "closes": closes, "ambiguous": ambiguous}


def parse_campaign_envelope(payload, *, campaign_id, milestone, last_result_sha256):
    """Validate one campaign-terminal payload.

    Returns {"status": "ACCEPTED"|"REJECTED", "code": ..., "message"/"campaign": ...}.
    Default deny: every check must pass.
    """

    def reject(code, message):
        return {"status": S_REJECTED, "code": code, "message": message}

    try:
        doc = load_json_strict(payload)
    except DuplicateKeyError as exc:
        return reject("E_DUPLICATE_KEY", str(exc))
    except ValueError as exc:
        return reject("E_MALFORMED_JSON", str(exc))

    if not isinstance(doc, dict):
        return reject("E_NOT_OBJECT", "campaign envelope must be a JSON object")

    unknown = sorted(set(doc) - set(CAMPAIGN_FIELDS))
    if unknown:
        return reject("E_UNKNOWN_FIELD", "unknown fields: %s" % ", ".join(unknown))

    missing = sorted(set(CAMPAIGN_FIELDS) - set(doc))
    if missing:
        return reject("E_MISSING_FIELD", "missing fields: %s" % ", ".join(missing))

    if doc["protocol"] != PROTOCOL_CAMPAIGN:
        return reject("E_PROTOCOL", "protocol must equal %s" % PROTOCOL_CAMPAIGN)
    if doc["campaign_id"] != campaign_id:
        return reject("E_CAMPAIGN_ID", "campaign_id does not match the current campaign")
    if doc["milestone"] != milestone:
        return reject("E_MILESTONE", "milestone does not match the current milestone")
    if doc["in_reply_to"] != last_result_sha256:
        return reject(
            "E_IN_REPLY_TO",
            "in_reply_to does not match Bridge state.last_result_sha256",
        )
    if doc["status"] not in STATUS_VALUES:
        return reject("E_STATUS", "status must be one of %s" % ", ".join(STATUS_VALUES))
    if doc["outcome"] not in OUTCOME_VALUES:
        return reject("E_OUTCOME", "outcome must be one of %s" % ", ".join(OUTCOME_VALUES))

    return {
        "status": S_ACCEPTED,
        "code": "OK",
        "campaign": {
            "protocol": doc["protocol"],
            "campaign_id": doc["campaign_id"],
            "milestone": doc["milestone"],
            "status": doc["status"],
            "outcome": doc["outcome"],
            "in_reply_to": doc["in_reply_to"],
        },
    }


def classify_bridge(text):
    """Coarse classification of the Bridge task side of one response."""
    extracted = bridge_protocol.extract_control_message(text)
    status = extracted.get("status")
    if status == bridge_protocol.S_ACCEPTED:
        return "ACCEPTED"
    if status == bridge_protocol.S_AMBIGUOUS:
        return "AMBIGUOUS"
    if status == bridge_protocol.S_NO_CONTROL:
        return "NO_CONTROL"
    return "MALFORMED"


def classify_response(text, *, campaign_id, milestone, last_result_sha256):
    """Classify one assistant response for the Supervisor's dispatch policy.

    Returns a dict whose ``status`` is one of ``S_NO_CONTROL``,
    ``S_TASK_CANDIDATE``, ``S_CAMPAIGN_TERMINAL``, ``S_CAMPAIGN_INVALID``,
    ``S_MALFORMED``, ``S_AMBIGUOUS`` or ``S_MIXED``.
    """
    campaign = extract_campaign_blocks(text)
    if campaign["ambiguous"]:
        return {"status": S_AMBIGUOUS, "reason": "unbalanced campaign-terminal markers"}

    blocks = campaign["blocks"]
    bridge = classify_bridge(text)

    if len(blocks) > 1:
        return {"status": S_AMBIGUOUS, "reason": "more than one campaign-terminal envelope"}

    if len(blocks) == 1:
        if bridge == "ACCEPTED":
            return {
                "status": S_MIXED,
                "reason": "response contains both a campaign terminal and an executable Bridge task",
            }
        if bridge in ("MALFORMED", "AMBIGUOUS"):
            return {
                "status": S_MALFORMED,
                "reason": "campaign terminal combined with a malformed/ambiguous Bridge task",
            }
        parsed = parse_campaign_envelope(
            blocks[0],
            campaign_id=campaign_id,
            milestone=milestone,
            last_result_sha256=last_result_sha256,
        )
        if parsed["status"] != S_ACCEPTED:
            return {"status": S_CAMPAIGN_INVALID, "code": parsed["code"], "message": parsed["message"]}
        return {"status": S_CAMPAIGN_TERMINAL, "campaign": parsed["campaign"]}

    # len(blocks) == 0
    if bridge == "ACCEPTED":
        extracted = bridge_protocol.extract_control_message(text)
        return {
            "status": S_TASK_CANDIDATE,
            "task": extracted["task"],
            "task_envelope_sha256": extracted["task_envelope_sha256"],
        }
    if bridge in ("MALFORMED", "AMBIGUOUS"):
        return {"status": S_MALFORMED, "reason": "malformed or ambiguous Bridge task envelope"}
    return {"status": S_NO_CONTROL}

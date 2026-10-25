#!/usr/bin/env python3
"""Deterministic ChatGPT transport adapter (read + single-attempt send).

Phase 3 proved READ works and that a message WAS delivered, yet ``send_once()``
reported a composer readback mismatch because it used *exact multiline composer
readback equality* as the authority for success. That equality is wrong: the
composer's innerText is not a faithful echo of what was submitted, so a real
delivery was reported as a failure — which invites a blind resend and a duplicate
control message.

Phase 4 semantics (SSOT for send success):

    CHECK IDENTIFIER ABSENT
      -> FILL
      -> SINGLE SEND ATTEMPT
      -> CONFIRM IDENTIFIER APPEARS IN USER TURN
      -> CONFIRMED_SENT

If confirmation cannot be established the result is ``SEND_UNCERTAIN`` and the
caller STOPs. This adapter never resends, never retries and never guesses.

The identifier is a unique token carried inside the outgoing control message, so
"did my message land" is decided by the conversation, not by the composer.

The browser/env bootstrap is performed lazily (first real browser operation) so
this module can be imported and unit-tested without a browser or a live daemon.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

CONTROL_URL = "https://chatgpt.com/c/6ac4d058-acb8-83e8-bf2c-8bb4b8aa2278"

EXPECTED_CDP = "http://127.0.0.1:9333"


def _default_hermes_agent_dir() -> str:
    """The pinned Hermes install dir, derived portably (env override, then ``$HOME``)."""
    override = os.environ.get("HERMES_AGENT_DIR")
    if override:
        return override
    return str(Path.home() / ".hermes" / "hermes-agent")


HERMES_AGENT = _default_hermes_agent_dir()

DEFAULT_CONFIRM_TIMEOUT_S = 15.0

# Status vocabulary
CONFIRMED_SENT = "CONFIRMED_SENT"
SEND_UNCERTAIN = "SEND_UNCERTAIN"
ALREADY_PRESENT = "ALREADY_PRESENT"


class AdapterError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Browser bootstrap (lazy)
# --------------------------------------------------------------------------- #

_HELPERS: dict | None = None


def _browser_state_dir() -> Path:
    _repo = Path(__file__).resolve().parents[3]
    _lib = str(_repo / "scripts" / "lib")
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
    import stack_paths  # noqa: PLC0415

    return stack_paths.browser_state_root() / "browser-harness"


def _ensure_browser_env() -> dict:
    """Fixed Browser-Harness environment + Hermes bootstrap, executed once."""
    global _HELPERS
    if _HELPERS is not None:
        return _HELPERS

    os.environ.setdefault("BU_NAME", "hermes-chatgpt")
    os.environ.setdefault("BH_HOME", str(_browser_state_dir()))
    os.environ.setdefault("BH_RUNTIME_DIR", os.environ["BH_HOME"] + "/runtime")

    # Only an already-established daemon may be used; otherwise fail closed.
    os.environ["BH_REQUIRE_EXISTING_DAEMON"] = "1"
    os.environ["BH_TAB_MARKER"] = "0"
    os.environ["BH_RECORD"] = "0"

    if os.environ.get("BU_CDP_URL") != EXPECTED_CDP:
        raise AdapterError("BU_CDP_URL must equal %s" % EXPECTED_CDP)
    if os.environ.get("BU_CDP_WS"):
        raise AdapterError("BU_CDP_WS must be unset")

    os.environ.pop("PYTHONHOME", None)
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("VIRTUAL_ENV", None)

    import sys

    sys.path.insert(0, HERMES_AGENT)

    from hermes_constants import get_default_hermes_root  # noqa: PLC0415

    os.environ["HERMES_HOME"] = os.environ.get("HERMES_HOME") or str(get_default_hermes_root())

    import hermes_bootstrap  # noqa: F401,PLC0415

    from browser_harness.admin import ensure_daemon  # noqa: PLC0415
    from browser_harness.helpers import (  # noqa: PLC0415
        current_tab,
        fill_input,
        js,
        list_tabs,
        press_key,
        switch_tab,
    )

    _HELPERS = {
        "ensure_daemon": ensure_daemon,
        "current_tab": current_tab,
        "fill_input": fill_input,
        "js": js,
        "list_tabs": list_tabs,
        "press_key": press_key,
        "switch_tab": switch_tab,
    }
    return _HELPERS


class RealOps:
    """The live Browser-Harness transport."""

    def __init__(self) -> None:
        self.h = _ensure_browser_env()

    # -- tab -----------------------------------------------------------------
    def find_control_tab(self) -> dict:
        self.h["ensure_daemon"]()
        matches = [tab for tab in self.h["list_tabs"]() if tab.get("url") == CONTROL_URL]
        if len(matches) != 1:
            raise AdapterError("expected exactly 1 control tab, got %d" % len(matches))
        self.h["switch_tab"](matches[0])
        current = self.h["current_tab"]()
        if current.get("url") != CONTROL_URL:
            raise AdapterError("wrong control URL: %s" % current.get("url"))
        return {
            "target_id": current.get("targetId") or current.get("target_id"),
            "title": current.get("title"),
            "url": current.get("url"),
        }

    def js(self, expression: str):
        return self.h["js"](expression)

    def fill_input(self, selector: str, text: str) -> None:
        self.h["fill_input"](selector, text, clear_first=True, timeout=3)

    def press_key(self, key: str) -> None:
        self.h["press_key"](key)

    # -- DOM reads -----------------------------------------------------------
    def composer_selector(self) -> str:
        selectors = [
            'div[contenteditable="true"][role="textbox"][aria-label="询问 ChatGPT"]',
            'div[contenteditable="true"][role="textbox"][aria-label="Ask ChatGPT"]',
        ]
        for selector in selectors:
            encoded = json.dumps(selector)
            count = self.js(
                """
                (() => {
                  const nodes = [...document.querySelectorAll(%s)];
                  return nodes.filter(e => {
                    const r = e.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                  }).length;
                })()
                """
                % encoded
            )
            if count == 1:
                return selector
        raise AdapterError("unique visible ChatGPT composer not found")

    def composer_text(self, selector: str) -> str:
        encoded = json.dumps(selector)
        value = self.js(
            """
            (() => {
              const e = document.querySelector(%s);
              return e ? e.innerText : null;
            })()
            """
            % encoded
        )
        return value or ""

    def conversation_text(self) -> str:
        """Whole conversation text (both roles) — the identifier-absent check."""
        value = self.js(
            """
            (() => {
              const main = document.querySelector('main');
              return main ? main.innerText : '';
            })()
            """
        )
        return value or ""

    def user_turns(self) -> list[str]:
        """Individual user message bodies — the exact-match authority for confirmation.

        Reads only user-message containers observed in the live ChatGPT DOM and
        returns each message's own body text. There is deliberately NO whole-page
        fallback: if user messages cannot be identified this raises so that
        delivery confirmation fails closed instead of comparing the entire page.
        """
        value = self.js(
            """
            (() => {
              const bubbles = [...document.querySelectorAll('[data-user-message-bubble="true"]')];
              if (!bubbles.length) return null;
              return bubbles.map(bubble => {
                const parts = [...bubble.querySelectorAll('.whitespace-pre-wrap')]
                  .map(node => node.innerText);
                if (!parts.length) return null;
                return parts.join("");
              });
            })()
            """
        )
        if not isinstance(value, list) or not value:
            raise AdapterError("no user message nodes found in the control conversation")
        if any(item is None for item in value):
            raise AdapterError("a user message node has no extractable body")
        return [str(item) for item in value]

    def user_turn_text(self) -> str:
        """Text of the user turns only — the authority for send confirmation."""
        return "\n".join(self.user_turns())

    def latest_assistant_text(self) -> str:
        value = self.js(
            """
            (() => {
              const nodes = [...document.querySelectorAll('[class*="MarkdownRoot"]')];
              if (!nodes.length) return null;
              return nodes[nodes.length - 1].innerText;
            })()
            """
        )
        if not value:
            raise AdapterError("latest assistant MarkdownRoot not found")
        return str(value)


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #

def read_latest_assistant(ops=None) -> dict:
    ops = ops or RealOps()
    tab = ops.find_control_tab()
    text = ops.latest_assistant_text()
    return {
        "status": "OK",
        **tab,
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def wait_for_new_assistant(previous_sha256: str, timeout: int = 120, ops=None) -> dict:
    """Poll until a NEW, stable assistant response appears (read-only)."""
    ops = ops or RealOps()
    ops.find_control_tab()
    deadline = time.monotonic() + timeout
    candidate = None
    stable = 0
    while time.monotonic() < deadline:
        try:
            text = ops.latest_assistant_text()
        except AdapterError:
            text = ""
        if text:
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if sha != previous_sha256:
                if sha == candidate:
                    stable += 1
                else:
                    candidate, stable = sha, 1
                if stable >= 2:  # two identical reads: generation has settled
                    return {"status": "NEW_ASSISTANT", "text": text, "sha256": sha}
            else:
                candidate, stable = None, 0
        time.sleep(1)
    return {"status": "TIMEOUT"}


# --------------------------------------------------------------------------- #
# Read-only pending-result confirmation
# --------------------------------------------------------------------------- #
#
# DELIVERY AUTHORITY (DEC-001 / DEC-002 / DEC-003): a pending result is delivered
# only when a USER TURN, normalised for CRLF/LF and surrounding whitespace, EQUALS
# the normalised complete canonical HERMES_RESULT_V1 message that was built for
# that pending result. When that message embeds a NEXT_CONTROL_CHALLENGE, its
# sequence / nonce / in_reply_to are part of the compared text.
#
# An identifier (result_sha256 / task_id) substring is NOT delivery: a diagnostic
# JSON dump of the result object, a copied SEND_UNCERTAIN diagnostic, a log line or
# a prose mention can all legitimately contain the same hash while the canonical
# message was never delivered.

_CHALLENGE_KEY = "NEXT_CONTROL_CHALLENGE:"


def normalize_message(text: str) -> str:
    """Normalise harmless browser text differences: CRLF/LF and edge whitespace.

    Only line-ending style and surrounding whitespace are normalised; the
    comparison stays exact (no fuzzing, no tokenising, no substring search).
    """
    if not isinstance(text, str):
        raise AdapterError("message text is required for confirmation")
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def parse_control_challenge(message: str) -> dict | None:
    """Return the embedded ``NEXT_CONTROL_CHALLENGE`` fields, or ``None``."""
    if not isinstance(message, str) or _CHALLENGE_KEY not in message:
        return None
    tail = message.split(_CHALLENGE_KEY, 1)[1]
    out: dict = {}
    for raw in tail.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key in ("sequence", "nonce", "in_reply_to"):
            out[key] = int(value) if key == "sequence" and value.isdigit() else value
    return out or None


def _user_turns(ops) -> list[str]:
    """Individual user turns through the read-only seam (per-turn, no joining)."""
    getter = getattr(ops, "user_turns", None)
    if callable(getter):
        try:
            turns = getter()
        except Exception:  # noqa: BLE001 - fall back to the aggregate read seam
            turns = None
        if turns is not None:
            return [str(turn) for turn in turns]
    text = ops.user_turn_text()
    return [str(text)]


def confirm_message_present(message: str, *, challenge: dict | None = None,
                            ops=None) -> bool:
    """READ-ONLY: is the exact canonical ``message`` present in a USER TURN?

    Returns True only when some user turn, normalised for CRLF/LF and surrounding
    whitespace, equals the normalised canonical message. When ``challenge`` is
    supplied it must also equal the challenge embedded in the matched turn.

    Never sends, never retries, never opens a tab, never navigates and never falls
    back to a looser comparison: it only reads the control conversation's user
    turns through the existing adapter seam.
    """
    if not isinstance(message, str) or not message.strip():
        raise AdapterError("canonical message is required for exact confirmation")
    ops = ops or RealOps()
    ops.find_control_tab()
    target = normalize_message(message)
    for turn in _user_turns(ops):
        if normalize_message(turn) != target:
            continue
        if challenge is not None and parse_control_challenge(turn) != challenge:
            continue
        return True
    return False


def confirm_result_present(identifier: str, *, ops=None) -> bool:
    """LEGACY (not delivery authority): does ``identifier`` appear in a USER TURN?

    Retained only for the pre-existing adapter tests (DEC-004). It is an
    identifier-substring check and MUST NOT decide whether a pending result or a
    round result is delivered; :func:`confirm_message_present` is that authority.
    """
    if not isinstance(identifier, str) or not identifier.strip():
        raise AdapterError("identifier is required for result confirmation")
    ops = ops or RealOps()
    ops.find_control_tab()
    return identifier in ops.user_turn_text()


# --------------------------------------------------------------------------- #
# Send (single attempt, identifier-confirmed)
# --------------------------------------------------------------------------- #

def send_once(text: str, identifier: str, *, ops=None,
              confirm_timeout_s: float = DEFAULT_CONFIRM_TIMEOUT_S,
              sleep=time.sleep, now=time.monotonic, exact: bool = False) -> dict:
    """Send ``text`` exactly once and confirm it, never by composer readback.

    The message MUST contain ``identifier`` (a unique token). Returns:

      {"status": "ALREADY_PRESENT"}  the message is already delivered
      {"status": "CONFIRMED_SENT"}   the message is visible in a user turn
      {"status": "SEND_UNCERTAIN", "reason": ..., "sent": bool}

    ``SEND_UNCERTAIN`` is terminal for this call: the caller STOPs. No resend is
    ever attempted, in either path.

    Confirmation authority:

    * ``exact=False`` (legacy default): ``identifier`` appears in a user turn. Kept
      for the pre-existing adapter tests (DEC-004).
    * ``exact=True`` (the normal bridge result path, DEC-001): a user turn,
      normalised for CRLF/LF and surrounding whitespace, EQUALS the complete
      canonical result message. A hash-only, diagnostic-JSON or prose user turn
      therefore does NOT confirm.
    """
    if not isinstance(text, str) or not text.strip():
        raise AdapterError("message is empty")
    if not isinstance(identifier, str) or not identifier.strip():
        raise AdapterError("identifier is required for send confirmation")
    if identifier not in text:
        raise AdapterError("identifier must appear inside the message text")

    ops = ops or RealOps()
    ops.find_control_tab()

    def _already_present() -> bool:
        if exact:
            return confirm_message_present(text, ops=ops)
        return identifier in ops.conversation_text()

    def _delivered() -> bool:
        if exact:
            return confirm_message_present(text, ops=ops)
        return identifier in ops.user_turn_text()

    # 1. CHECK THE MESSAGE ABSENT ------------------------------------------
    if _already_present():
        return {"status": ALREADY_PRESENT, "sent": False}

    # 2. FILL ---------------------------------------------------------------
    selector = ops.composer_selector()
    ops.fill_input(selector, text)

    if not ops.composer_text(selector).strip():
        # Nothing to submit. No send is attempted, so there is no resend risk.
        return {
            "status": SEND_UNCERTAIN,
            "sent": False,
            "reason": "composer empty after fill; no send attempted",
        }

    # 3. SINGLE SEND ATTEMPT ------------------------------------------------
    ops.press_key("Enter")

    # 4. CONFIRM THE RESULT MESSAGE (exact) OR THE IDENTIFIER (legacy) ------
    deadline = now() + max(0.0, confirm_timeout_s)
    while True:
        if _delivered():
            return {"status": CONFIRMED_SENT, "sent": True}
        if now() >= deadline:
            break
        sleep(0.5)

    # 5. UNCERTAIN -> STOP. Never resend.
    return {
        "status": SEND_UNCERTAIN,
        "sent": True,
        "reason": "result message was not confirmed in a user turn after the single send attempt",
    }


# --------------------------------------------------------------------------- #
# CLI (manual transport checks only; the kernel uses bridge_cli.py)
# --------------------------------------------------------------------------- #

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("find")
    sub.add_parser("read")
    p_send = sub.add_parser("send")
    p_send.add_argument("text")
    p_send.add_argument("identifier")
    p_wait = sub.add_parser("wait")
    p_wait.add_argument("previous_sha256")
    p_wait.add_argument("--timeout", type=int, default=120)

    args = parser.parse_args()
    try:
        if args.command == "find":
            result = {"status": "OK", **RealOps().find_control_tab()}
        elif args.command == "read":
            result = read_latest_assistant()
        elif args.command == "send":
            result = send_once(args.text, args.identifier)
        else:
            result = wait_for_new_assistant(args.previous_sha256, args.timeout)
    except Exception as exc:  # noqa: BLE001 - CLI reports, never raises
        result = {"status": "ERROR", "error": type(exc).__name__, "message": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Persistent bridge state, replay journal and the single-worker lock.

State root (default ``~/.local/state/hermes-chatgpt-bridge/``):

  state.json     chain state: expected_sequence / expected_nonce / expected_in_reply_to
  journal.jsonl  append-only decision journal (task identity consumption + outcomes)
  bridge.lock    flock target for the single-writer guard

Design constraints (Phase 4):

  * MAX_IN_FLIGHT_TASKS = 1. One worker only; the whole round holds the lock.
  * Task identity (task_id and the (sequence, nonce) pair) is consumed BEFORE the
    execution is invoked, so a crash can never cause blind re-execution.
  * The journal is append-only and flushed+fsynced before a decision is acted on.

The nonce is a correlation / replay-protection value. It is NOT cryptographic
sender authentication and must never be described as such.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import secrets
import sys
import time
from pathlib import Path

from protocol import GENESIS, canonical_json, sha256_text

PROTOCOL_VERSION = "HERMES_TASK_V1"

MAX_IN_FLIGHT_TASKS = 1

STATE_FILE = "state.json"
JOURNAL_FILE = "journal.jsonl"
LOCK_FILE = "bridge.lock"
PENDING_FILE = "pending_result.json"

def _default_state_dir() -> Path:
    _repo = Path(__file__).resolve().parents[3]
    _lib = str(_repo / "scripts" / "lib")
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
    import stack_paths  # noqa: PLC0415

    return stack_paths.bridge_state_root()


DEFAULT_STATE_DIR = _default_state_dir()

NONCE_BYTES = 32  # 256-bit random hex nonce

DIR_MODE = 0o700
FILE_MODE = 0o600

LOCK_TIMEOUT_S = 30.0


class BridgeBusy(RuntimeError):
    """Another worker holds the bridge lock."""


def state_dir() -> Path:
    override = os.environ.get("HERMES_BRIDGE_STATE_DIR")
    return Path(override) if override else DEFAULT_STATE_DIR


def new_nonce() -> str:
    """Cryptographically random nonce (correlation + replay protection)."""
    return secrets.token_hex(NONCE_BYTES)


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, DIR_MODE)
    except OSError:
        pass


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(path))
    try:
        os.chmod(path, FILE_MODE)
    except OSError:
        pass
    # Durability: the rename itself must reach disk, otherwise a power loss can
    # revert the directory entry even though the file content was fsynced.
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Chain state
# --------------------------------------------------------------------------- #

def initial_state() -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "expected_sequence": 1,
        "expected_nonce": new_nonce(),
        "expected_in_reply_to": GENESIS,
        "status": "IDLE",
        "last_task_id": None,
        "last_result_sha256": None,
    }


class BridgeState:
    """A dict-backed view of state.json with a stable write path."""

    def __init__(self, data: dict, path: Path):
        self._data = data
        self._path = path

    # -- accessors -----------------------------------------------------------
    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def as_dict(self) -> dict:
        return dict(self._data)

    def set_status(self, status: str) -> None:
        self._data["status"] = status
        self.save()

    def chain(self, *, next_sequence: int, next_nonce: str, next_in_reply_to: str,
              status: str, last_task_id: str | None = None,
              last_result_sha256: str | None = None) -> None:
        self._data.update(
            {
                "expected_sequence": next_sequence,
                "expected_nonce": next_nonce,
                "expected_in_reply_to": next_in_reply_to,
                "status": status,
            }
        )
        if last_task_id is not None:
            self._data["last_task_id"] = last_task_id
        if last_result_sha256 is not None:
            self._data["last_result_sha256"] = last_result_sha256
        self.save()

    # -- persistence ---------------------------------------------------------
    def save(self) -> None:
        _ensure_private_dir(self._path.parent)
        _atomic_write(self._path, canonical_json(self._data) + "\n")


def load_state(root: Path | None = None) -> BridgeState:
    root = Path(root) if root else state_dir()
    _ensure_private_dir(root)
    path = root / STATE_FILE
    if not path.exists():
        state = BridgeState(initial_state(), path)
        state.save()
        return state
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("state.json is not a JSON object")
    return BridgeState(data, path)


# --------------------------------------------------------------------------- #
# Journal (replay protection)
# --------------------------------------------------------------------------- #

def _journal_path(root: Path) -> Path:
    return root / JOURNAL_FILE


def journal_append(entry: dict, root: Path | None = None) -> None:
    """Append one decision record and fsync it before returning."""
    root = Path(root) if root else state_dir()
    _ensure_private_dir(root)
    path = _journal_path(root)
    record = dict(entry)
    record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    line = canonical_json(record) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, FILE_MODE)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def read_journal(root: Path | None = None) -> list[dict]:
    root = Path(root) if root else state_dir()
    path = _journal_path(root)
    if not path.exists():
        return []
    entries: list[dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                # A torn final line is ignored; earlier consumption records stand.
                continue
    return entries


def consumed_identities(root: Path | None = None) -> tuple[set[str], set[tuple]]:
    """(consumed task_ids, consumed (sequence, nonce) pairs) from the journal."""
    task_ids: set[str] = set()
    pairs: set[tuple] = set()
    for entry in read_journal(root):
        if entry.get("event") != "ACCEPTED":
            continue
        task_id = entry.get("task_id")
        sequence = entry.get("sequence")
        nonce = entry.get("nonce")
        if isinstance(task_id, str) and task_id:
            task_ids.add(task_id)
        if isinstance(sequence, int) and isinstance(nonce, str) and nonce:
            pairs.add((sequence, nonce))
    return task_ids, pairs


def is_consumed(task_id: str, sequence: int, nonce: str, root: Path | None = None) -> bool:
    task_ids, pairs = consumed_identities(root)
    return task_id in task_ids or (sequence, nonce) in pairs


def consume_task(task: dict, *, task_envelope_sha256: str, root: Path | None = None) -> dict:
    """Consume a task identity BEFORE execution.

    Returns {"status": "CONSUMED"|"REPLAY_REJECTED", "reason": ...}. The ACCEPTED
    record is written and fsynced first, so a crash between here and the Hermes
    invocation leaves the identity consumed (a replay is refused, never re-run).
    """
    task_id = task["task_id"]
    sequence = task["sequence"]
    nonce = task["nonce"]

    if is_consumed(task_id, sequence, nonce, root):
        journal_append(
            {
                "event": "REPLAY_REJECTED",
                "task_id": task_id,
                "sequence": sequence,
                "nonce_sha256": sha256_text(nonce),
            },
            root,
        )
        return {"status": "REPLAY_REJECTED", "reason": "task identity already consumed"}

    journal_append(
        {
            "event": "ACCEPTED",
            "task_id": task_id,
            "sequence": sequence,
            "nonce": nonce,
            "task_envelope_sha256": task_envelope_sha256,
        },
        root,
    )
    return {"status": "CONSUMED"}


def journal_outcome(*, task_id: str, sequence: int, outcome: str, exit_code: int,
                    result_sha256: str, root: Path | None = None) -> None:
    journal_append(
        {
            "event": "RESULT",
            "task_id": task_id,
            "sequence": sequence,
            "outcome": outcome,
            "exit_code": exit_code,
            "result_sha256": result_sha256,
        },
        root,
    )


# --------------------------------------------------------------------------- #
# Durable pending-result transaction
# --------------------------------------------------------------------------- #
#
# A browser send is NOT idempotent. The pending record is therefore written and
# fsynced BEFORE the send and its ``send_attempted`` flag is made durable BEFORE
# the single attempt, so a crash in between is recoverable by read-only evidence
# rather than by a blind resend.

TERMINAL_EVENTS = ("RESULT", "STOPPED")


def pending_path(root: Path | None = None) -> Path:
    root = Path(root) if root else state_dir()
    return root / PENDING_FILE


def write_pending(record: dict, root: Path | None = None) -> None:
    """Atomically persist the pending result (file fsync + directory fsync)."""
    root = Path(root) if root else state_dir()
    _ensure_private_dir(root)
    _atomic_write(pending_path(root), canonical_json(record) + "\n")


def read_pending(root: Path | None = None) -> dict | None:
    path = pending_path(root)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def remove_pending(root: Path | None = None) -> None:
    """Remove the pending record after the chain has been committed."""
    try:
        pending_path(root).unlink()
    except FileNotFoundError:
        pass


def mark_send_attempted(root: Path | None = None) -> dict:
    """Durably set ``send_attempted=true`` BEFORE the non-idempotent send."""
    record = read_pending(root)
    if record is None:
        raise RuntimeError("no pending result to mark as send_attempted")
    record["send_attempted"] = True
    write_pending(record, root)
    return record


def human_resend_count(root: Path | None = None) -> int:
    """The durable human-resend counter on the pending result (absent => 0)."""
    record = read_pending(root)
    if record is None:
        return 0
    value = record.get("human_resend_count")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def record_human_resend(root: Path | None = None, *, reason: str | None = None) -> dict:
    """Durably record ONE human-authorized resend BEFORE the send is attempted.

    Read-modify-write of the pending record through :func:`write_pending` (atomic
    rename + file fsync + directory fsync), so the authorization survives a crash
    that happens between here and the non-idempotent browser send. Returns the
    persisted record.
    """
    record = read_pending(root)
    if record is None:
        raise RuntimeError("no pending result to record a human resend for")
    current = record.get("human_resend_count")
    current = current if isinstance(current, int) and not isinstance(current, bool) else 0
    record["human_resend_count"] = current + 1
    if reason is not None:
        record["human_resend_reason"] = reason
    write_pending(record, root)
    return record


# --------------------------------------------------------------------------- #
# Startup reconciliation (kill -9 / power-loss recovery)
# --------------------------------------------------------------------------- #


def unresolved_accepted(root: Path | None = None) -> list[dict]:
    """ACCEPTED journal entries with no later terminal RESULT/STOPPED for that task.

    This is the fail-closed startup shape: a task identity was consumed (so it can
    never be replayed) but the round never produced a terminal outcome.
    """
    entries = read_journal(root)
    terminal: set[str] = set()
    for entry in entries:
        if entry.get("event") in TERMINAL_EVENTS:
            task_id = entry.get("task_id")
            if isinstance(task_id, str) and task_id:
                terminal.add(task_id)
    unresolved: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.get("event") != "ACCEPTED":
            continue
        task_id = entry.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            continue
        if task_id in terminal or task_id in seen:
            continue
        seen.add(task_id)
        unresolved.append(entry)
    return unresolved


# --------------------------------------------------------------------------- #
# Single-worker lock
# --------------------------------------------------------------------------- #

class bridge_lock:  # noqa: N801 - context manager reads as a noun
    """Exclusive flock on bridge.lock. One round at a time (MAX_IN_FLIGHT_TASKS=1)."""

    def __init__(self, root: Path | None = None, timeout: float = LOCK_TIMEOUT_S):
        self.root = Path(root) if root else state_dir()
        self.timeout = timeout
        self._fd: int | None = None

    def __enter__(self):
        _ensure_private_dir(self.root)
        path = self.root / LOCK_FILE
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT, FILE_MODE)
        deadline = time.monotonic() + max(0.0, self.timeout)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    os.close(fd)
                    raise
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise BridgeBusy("another bridge worker holds the lock")
                time.sleep(0.05)
        self._fd = fd
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None
        return False

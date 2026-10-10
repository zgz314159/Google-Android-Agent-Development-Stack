#!/usr/bin/env python3
"""campaign_state.py — durable per-campaign state, journal and single-owner lock.

Private state root (default ``~/.local/state/hermes-chatgpt-supervisor/<campaign-id>/``):

  state.json     the campaign record (see ``STATE_FIELDS``)
  journal.jsonl  append-only decision journal
  campaign.lock  flock target for the single-owner guard

Design constraints:

  * exactly one Supervisor process may own a campaign; a second process is refused
    with ``CampaignLockBusy`` BEFORE any campaign state is read or written and
    without touching the Bridge;
  * writes are atomic replace plus fsync (file fsync and directory fsync);
  * directory mode 0700 and state/journal file mode 0600 where practical.

The Bridge's own lock and state files are never touched by this module.

Standard library only.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import sys
import time
from pathlib import Path


def _default_root() -> Path:
    _repo = Path(__file__).resolve().parents[3]
    _lib = str(_repo / "scripts" / "lib")
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
    import stack_paths  # noqa: PLC0415

    return stack_paths.supervisor_state_root()


DEFAULT_ROOT = _default_root()

STATE_FILE = "state.json"
JOURNAL_FILE = "journal.jsonl"
LOCK_FILE = "campaign.lock"

DIR_MODE = 0o700
FILE_MODE = 0o600
LOCK_TIMEOUT_S = 0.5

STATE_FIELDS = (
    "campaign_id",
    "milestone",
    "status",
    "started_at",
    "deadline",
    "max_rounds",
    "round_count",
    "initial_sequence",
    "last_seen_assistant_sha256",
    "last_dispatched_task_id",
    "last_bridge_result_sha256",
    "terminal_outcome",
)

# A campaign id must be usable as a directory name and must never traverse.
_CAMPAIGN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class CampaignLockBusy(RuntimeError):
    """Another Supervisor process already owns this campaign."""


def state_root(override=None) -> Path:
    """The private Supervisor state root, with an optional test override."""
    if override is not None:
        return Path(override)
    env = os.environ.get("HERMES_CAMPAIGN_STATE_DIR")
    return Path(env) if env else DEFAULT_ROOT


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, DIR_MODE)
    except OSError:
        pass


def _atomic_write(path: Path, text: str) -> None:
    """Atomic replace plus fsync (file and directory)."""
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
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def initial_state(*, campaign_id: str, milestone: str, started_at: float,
                  deadline: float, max_rounds: int, initial_sequence) -> dict:
    """The initial campaign record, carrying every ``STATE_FIELDS`` entry."""
    return {
        "campaign_id": campaign_id,
        "milestone": milestone,
        "status": "RUNNING",
        "started_at": started_at,
        "deadline": deadline,
        "max_rounds": int(max_rounds),
        "round_count": 0,
        "initial_sequence": initial_sequence,
        "last_seen_assistant_sha256": None,
        "last_dispatched_task_id": None,
        "last_bridge_result_sha256": None,
        "terminal_outcome": None,
    }


class campaign_lock:
    """Exclusive flock on ``campaign.lock``. One Supervisor per campaign."""

    def __init__(self, root: Path, timeout: float = LOCK_TIMEOUT_S):
        self.root = Path(root)
        self.timeout = timeout
        self._fd = None

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
                    raise CampaignLockBusy("another supervisor worker holds the campaign lock")
                time.sleep(0.02)
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


class CampaignStore:
    """The private per-campaign state store for exactly one campaign id."""

    def __init__(self, campaign_id: str, root=None):
        if not isinstance(campaign_id, str) or not _CAMPAIGN_ID_RE.match(campaign_id):
            raise ValueError("invalid campaign id: %r" % (campaign_id,))
        self.campaign_id = campaign_id
        self.root = state_root(root) / campaign_id

    # -- paths --------------------------------------------------------------- #
    @property
    def state_path(self) -> Path:
        return self.root / STATE_FILE

    @property
    def journal_path(self) -> Path:
        return self.root / JOURNAL_FILE

    @property
    def lock_path(self) -> Path:
        return self.root / LOCK_FILE

    def ensure_dir(self) -> None:
        _ensure_private_dir(self.root)

    def exists(self) -> bool:
        return self.state_path.is_file()

    # -- state --------------------------------------------------------------- #
    def load(self):
        if not self.state_path.is_file():
            return None
        with open(self.state_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("state.json is not a JSON object")
        return data

    def save(self, state: dict) -> None:
        self.ensure_dir()
        _atomic_write(self.state_path, canonical_json(state) + "\n")

    def create(self, state: dict) -> None:
        self.save(state)

    # -- journal ------------------------------------------------------------- #
    def journal(self, entry: dict) -> None:
        self.ensure_dir()
        record = dict(entry)
        record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        line = canonical_json(record) + "\n"
        fd = os.open(str(self.journal_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, FILE_MODE)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def read_journal(self) -> list:
        if not self.journal_path.is_file():
            return []
        entries: list = []
        with open(self.journal_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    continue
        return entries

    # -- lock ---------------------------------------------------------------- #
    def lock(self, timeout: float = LOCK_TIMEOUT_S) -> campaign_lock:
        return campaign_lock(self.root, timeout=timeout)

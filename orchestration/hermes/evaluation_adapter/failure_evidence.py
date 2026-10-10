#!/usr/bin/env python3
"""Structured failure evidence — "prove failure, then classify failure" (P0B-EVAL-GUARD-FIX).

Why this module exists
----------------------
The frozen Evaluation Core classifies a logical failure by searching a tool result's
*text* for failure-looking patterns (``evaluation/commandcode/core.py::_FAIL_PATTERNS``).
Nothing in that rule requires the operation that produced the text to have actually
failed. Two real, evidenced consequences in the P0B-CLOSE run ``HERMES-20261005_032302_4c6c40``:

  FAIL-001  PROVIDER_AUTH — produced by a *successful* ``grep`` (exit 0) that merely
            printed ``evaluation/commandcode/core.py`` source lines containing the
            literals ``PROVIDER_AUTH`` and ``401``/``authentication failed``. Nothing
            provider-related happened; the provider-fallback deviation was derived from it.

  FAIL-002  TEST_PROBLEM — a pipeline-lost exit status made the core read a test run's
            text without any structured proof of what the command returned.

The architectural rule this module enforces:

    PROVE FAILURE   (structured execution state: exit status, tool status, provider error)
        |
        v
    CLASSIFY FAILURE (textual evidence may only *classify* an already-proven/plausible failure)

Consequences, by construction:

  * A logical failure is removed as a false positive when **every** operation it was drawn
    from carries a *reliable* structured success (exit code 0, no structured error, and an
    exit status the runner did NOT flag as non-authoritative). In that case the failure's
    only evidence is descriptive text inside a successful operation — the case the rule forbids.
  * This module can only ever REMOVE failures. It never invents one, so it cannot introduce a
    new false positive.
  * A real build/test failure is never weakened: a genuine failure either returns a non-zero
    exit status (=> FAILED) or is produced by a command whose exit status the runner explicitly
    flags as the *last pipeline stage only* (=> INDETERMINATE, not SUCCEEDED, so it is kept).

P0B-EVAL-INSPECTION-CONTEXT-FIX (this module's second rule)
----------------------------------------------------------
The prove-then-classify rule above still could not disprove a failure whose *quoted historical* text
is itself an invoked-tool verdict (``BUILD FAILED``, ``FAILED (failures=N)``, ``401 unauthorized``,
``Traceback``): the OPERATION_SUCCEEDED rule deliberately keeps any output carrying such a verdict,
and a pipeline advisory turns the persisted exit status into INDETERMINATE. The remaining false
positive is therefore:

    a *successful* evidence-inspection command (``cat``/``grep``/``show_run.py``/``scan_calls.py``/
    ``cmp_runs.py``/``dump_raw.py``/…) whose stdout merely *quotes* an archived failure verdict is
    attributed to the current operation.

The correction adds two deterministic concepts, derived from the command only (never from the
result text, never from an LLM, never from a file-name lookup):

  OPERATION ROLE       EXECUTES_BUILD / EXECUTES_TEST / EXECUTES_PROVIDER / INSPECTS_EVIDENCE / OTHER
  VERDICT OWNERSHIP    a textual verdict may classify a failure only for the role that can own it:
                       build verdicts -> EXECUTES_BUILD, test verdicts -> EXECUTES_TEST,
                       provider verdicts -> EXECUTES_PROVIDER. INSPECTS_EVIDENCE owns none.

A failure is removed as inspection-derived only when **every** operation behind it is positively
classified INSPECTS_EVIDENCE, **every** one of those inspections is a clean structured success (an
exit-0 pipeline advisory of a read-only command still counts as clean, because the command executes
nothing), the failure's type belongs to a textual verdict family, no operation can own that family,
and one of the outputs actually carries the family's verdict token. Unknown roles are never removed
(section 11: preserve uncertain real failures), so a real build/test/provider failure survives.

P0B-EVAL-WRAPPER-ROLE-FIX (this module's third rule)
----------------------------------------------------
The role classifier above resolved the *program* of a simple command by stripping only a fixed set of
bare wrappers (``sudo``/``env``/``VAR=value``/``nohup``/``time``/``nice``/``exec``). A wrapper that
carries its own **options or a duration** was not unwrapped, so the wrapper itself became the program
token:

    timeout 300 python3 -m unittest … -v | tail -40

resolved to program ``timeout``, which the classifier treats as neutral; the only positively
classified simple command was then ``tail`` → INSPECTS_EVIDENCE. A real unittest execution was thus
downgraded to an inspection, no operation could own the TEST verdict family, and a genuine
``FAILED (failures=N)`` test failure was removed as a quoted-verdict false positive — the observed
regression.

The correction extends the deterministic parser with a **process-wrapper unwrapper** that consumes
each wrapper together with its own options/duration and then classifies the underlying executable
recursively: ``timeout`` (with its duration and options), ``sudo``, ``env``, ``nohup``, ``command``,
``nice``, ``ionice``, ``chrt``, ``stdbuf``, ``setsid`` and ``time``. Parsing is conservative: a
recognised wrapper whose payload cannot be resolved confidently (an unknown option, a missing/
unparseable duration, no command) yields **OTHER**, never INSPECTS_EVIDENCE — an execution may never
be downgraded to an inspection because of a wrapper. The role priority is unchanged and explicit:
execution roles (EXECUTES_BUILD / EXECUTES_TEST / EXECUTES_PROVIDER) always dominate a trailing
``tail``/``head``/``cat``/``grep`` stage, so a real test/build behind a pipe stays a test/build.

Why the source adapter and not ``core.py``
------------------------------------------
``core.py`` is ``PRODUCTION_IMMUTABLE`` in the frozen P0B-CLOSE contract
(``forbidden_paths``) and the live ``pre_tool_call`` Contract Guard blocks writes to it;
the same contract's DEC-010 states the Evaluation Core is unchanged and that only the Hermes
source adapter plus one additive optional finalizer parameter may change. This module and the
``failure_evidence`` parameter of ``finalize_session.finalize`` are exactly that additive layer:
no phase, clock, token or task-window semantics are touched.

Stdlib only, zero LLM calls, zero network calls, never writes anything.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

MODULE_VERSION = "p0b-eval-wrapper-role-fix-1"

# The tools whose result can express an *operation* outcome. Kept identical to the frozen
# core's ``core._COMMAND_TOOLS`` (a test asserts the two sets never drift apart).
OPERATION_TOOLS = frozenset({
    "shell_command", "shell_output", "shell_tasks", "kill_shell", "monitor_command",
})

# --------------------------------------------------------------------------- #
# structured parsing
# --------------------------------------------------------------------------- #
# A Hermes tool result is a JSON envelope:  {"output": ..., "exit_code": N, "error": ...}
# Command Code writes a plain-text header:   Task: sBG1 (shell, failed) / Exit code: N
_ENVELOPE_EXIT_KEYS = ("exit_code", "exitCode", "returncode", "return_code")
_ENVELOPE_ERROR_KEYS = ("error", "provider_error")
# Hermes prints this advisory when a pipeline hides the pre-pipe status: the persisted
# exit code is then the LAST stage's status only and is NOT authoritative.
_PIPELINE_WARNING_MARKERS = (
    "last pipeline command",
    "not of the command before the pipe",
    "treat this run as failed until proven otherwise",
)

_TEXT_EXIT_RE = re.compile(r"\bExit code:\s*(-?\d+)")
_TEXT_EXIT_ENV_RE = re.compile(r"\bEXIT=(-?\d+)\b")
_TEXT_STATUS_RE = re.compile(r"\((?:shell|monitor|background),\s*(completed|failed|running)\)")

SRC_ENVELOPE = "runner-json-envelope"
SRC_TEXT = "runner-text-status"
SRC_NONE = "none"

OUTCOME_FAILED = "FAILED"
OUTCOME_SUCCEEDED = "SUCCEEDED"
OUTCOME_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OperationState:
    """Structured execution state of one tool result, as the runner persisted it."""

    tool: str = ""
    exit_code: int = None
    error: str = None
    exit_reliable: bool = False
    status: str = None
    source: str = SRC_NONE

    @property
    def has_exit_status(self) -> bool:
        return isinstance(self.exit_code, int) and not isinstance(self.exit_code, bool)

    @property
    def outcome(self) -> str:
        """FAILED / SUCCEEDED / UNKNOWN — proven from structured state only."""
        if self.status == "failed":
            return OUTCOME_FAILED
        if self.error:
            return OUTCOME_FAILED
        if self.has_exit_status and self.exit_code != 0:
            return OUTCOME_FAILED
        if self.has_exit_status and self.exit_code == 0 and self.exit_reliable:
            return OUTCOME_SUCCEEDED
        return OUTCOME_UNKNOWN

    def as_dict(self) -> dict:
        return {
            "tool": self.tool,
            "exit_code": self.exit_code,
            "error": self.error,
            "exit_reliable": self.exit_reliable,
            "status": self.status,
            "source": self.source,
            "outcome": self.outcome,
        }


def _parse_envelope(text: str):
    """Return the parsed JSON object when ``text`` is a runner JSON envelope, else None."""
    s = (text or "").lstrip()
    if not s.startswith("{"):
        return None
    try:
        obj = json.loads(s)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _envelope_reliable(obj: dict) -> bool:
    """False when the runner itself flags the persisted exit status as non-authoritative."""
    hint = obj.get("hint")
    if isinstance(hint, str):
        low = hint.lower()
        if any(marker in low for marker in _PIPELINE_WARNING_MARKERS):
            return False
    for key in ("exit_reliable", "exit_status_reliable"):
        value = obj.get(key)
        if isinstance(value, bool):
            return value
    return True


def parse_operation_state(result_text: str, tool_name: str = "") -> OperationState:
    """Extract the structured execution state of one tool result.

    The JSON envelope is authoritative when present; plain-text fallback is used only for the
    Command Code result form. Nothing is inferred from prose: an absent exit status stays absent
    (=> UNKNOWN), never "0".
    """
    text = result_text if isinstance(result_text, str) else ""

    obj = _parse_envelope(text)
    if obj is not None and any(k in obj for k in _ENVELOPE_EXIT_KEYS + _ENVELOPE_ERROR_KEYS):
        exit_code = None
        for key in _ENVELOPE_EXIT_KEYS:
            value = obj.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                exit_code = value
                break
            if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
                exit_code = int(value.strip())
                break
        error = None
        for key in _ENVELOPE_ERROR_KEYS:
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                error = value.strip()
                break
        status = obj.get("status") if obj.get("status") in ("completed", "failed", "running") else None
        return OperationState(
            tool=tool_name,
            exit_code=exit_code,
            error=error,
            exit_reliable=_envelope_reliable(obj),
            status=status,
            source=SRC_ENVELOPE,
        )

    # Command Code plain-text result form.
    m = _TEXT_EXIT_RE.search(text) or _TEXT_EXIT_ENV_RE.search(text)
    m_status = _TEXT_STATUS_RE.search(text)
    if m or m_status:
        return OperationState(
            tool=tool_name,
            exit_code=int(m.group(1)) if m else None,
            error=None,
            # The Command Code text header only prints a real exit status, so it is authoritative.
            exit_reliable=bool(m),
            status=m_status.group(1) if m_status else None,
            source=SRC_TEXT,
        )
    return OperationState(tool=tool_name)


def outcome_of_result(result_text: str, tool_name: str = "") -> str:
    return parse_operation_state(result_text, tool_name).outcome


# --------------------------------------------------------------------------- #
# correction
# --------------------------------------------------------------------------- #
RULE_OPERATION_SUCCEEDED = "OPERATION_SUCCEEDED"
RULE_PROVIDER_FROM_INSPECTION_TEXT = "PROVIDER_TYPED_FROM_INSPECTION_TEXT"
RULE_INSPECTION_CONTEXT = "INSPECTION_CONTEXT_NO_VERDICT_OWNER"

FALSE_POSITIVE_RULES = {
    RULE_OPERATION_SUCCEEDED: (
        "every operation this failure was drawn from is a clean structured success (exit 0, no "
        "structured error, exit status not flagged non-authoritative) AND none of their output "
        "carries the invoked tool's own termination verdict (BUILD FAILED / FAILED (failures=N) / "
        "Traceback / TIMEOUT) - so the failure rests on descriptive text inside a successful "
        "operation"
    ),
    RULE_PROVIDER_FROM_INSPECTION_TEXT: (
        "a PROVIDER_* type was asserted from the output of read-only inspection commands "
        "(grep/cat/sed/head/sort/...) that carry no provider-operation token, i.e. no provider "
        "operation was executed"
    ),
    RULE_INSPECTION_CONTEXT: (
        "every operation this failure was drawn from is a positively classified INSPECTS_EVIDENCE "
        "command (read/print/parse/compare helpers only - no build, test or provider execution) and "
        "each of those inspections itself completed cleanly, and no operation can own the textual "
        "verdict family of the failure (verdict ownership), so the verdict token in the output is "
        "quoted historical/descriptive evidence, not this operation's own failure"
    ),
}

# A read-only inspection: the command only reads/prints text. It cannot itself be a provider
# operation, so its output cannot prove a provider failure.
_READ_ONLY_INSPECTION_RE = re.compile(
    r"(?i)(?:^|[;&|]\s*|\|\|\s*|&&\s*)(?:sudo\s+)?"
    r"(?:grep|egrep|fgrep|rg|ag|ack|sed|cat|head|tail|less|more|find|ls|tree|stat|file|wc|diff|"
    r"sha256sum|md5sum|shasum|strings|xxd|od|nl|cut|sort|uniq|awk|echo|pwd|which|type|dirname|"
    r"basename)\b"
)
# A genuine provider operation names the provider/CLI/HTTP endpoint. Its presence disqualifies
# the "inspection text" rule, so a real provider probe can never be dropped by it. The
# alternatives carry no trailing word boundary so snake_case identifiers (provider_probe,
# PROBE_PROVIDER, api_key) also count.
_PROVIDER_OPERATION_RE = re.compile(
    r"(?i)\bclaude|\bcodex|\bopencode|\bopenai|\banthropic|\bcommandcode|"
    r"\bdeepseek|\bgemini|\bllm|\bprovider|\bprobe|\bapi|\btoken|\bmodel|"
    r"\bcurl|\bwget|https?://|\bbearer|\bquota|\brate[_ ]?limit|\bunauthor"
)
# The invoked tool's OWN termination verdict - the build tool, test runner or interpreter
# declaring that the operation failed. Deliberately NOT a provider/auth keyword: source code
# that merely *contains* the words "invalid api key" is not a provider failure.
_TOOL_FAILURE_VERDICT_RE = re.compile(
    r"(?i)BUILD FAILED|FAILURE:\s*Build failed|Execution failed for task|"
    r"FAILED\s*\((?=[^)]*(?:failures|errors)\s*=)|"
    r"\b\d+\s+tests?\s+failed\b|\bTESTS FAILED\b|\bSELFTEST_[A-Z_]*=FAIL\b|"
    r"Traceback \(most recent call last\)|\[TIMEOUT\]|\bEXIT=124\b"
    r"|^\s*FAILED\s*$",
    re.M,
)


def is_read_only_inspection(command: str) -> bool:
    return bool(_READ_ONLY_INSPECTION_RE.search(command or ""))


def is_provider_operation(command: str) -> bool:
    return bool(_PROVIDER_OPERATION_RE.search(command or ""))


def has_tool_failure_verdict(*texts: str) -> bool:
    """True when some output carries the invoked tool's own failure termination verdict."""
    return any(_TOOL_FAILURE_VERDICT_RE.search(t or "") for t in texts)


# --------------------------------------------------------------------------- #
# operation role  (P0B-EVAL-INSPECTION-CONTEXT-FIX)
# --------------------------------------------------------------------------- #
# What an operation DID, derived deterministically from the command structure alone: its program
# tokens, the invoked executable/script, its explicit targets and the known purpose of the helper it
# runs. The result text is never consulted, so a quoted historical verdict cannot influence the role.
ROLE_BUILD = "EXECUTES_BUILD"
ROLE_TEST = "EXECUTES_TEST"
ROLE_PROVIDER = "EXECUTES_PROVIDER"
ROLE_INSPECT = "INSPECTS_EVIDENCE"
ROLE_OTHER = "OTHER"

OPERATION_ROLES = (ROLE_BUILD, ROLE_TEST, ROLE_PROVIDER, ROLE_INSPECT, ROLE_OTHER)

# Textual-verdict families (brief section 9/11).
FAMILY_BUILD = "BUILD"
FAMILY_TEST = "TEST"
FAMILY_PROVIDER = "PROVIDER"

_FAMILY_BY_TYPE = {
    "BUILD_ERROR": FAMILY_BUILD,
    "TEST_PROBLEM": FAMILY_TEST,
    "PROVIDER_QUOTA": FAMILY_PROVIDER,
    "PROVIDER_AUTH": FAMILY_PROVIDER,
    "PROVIDER_MODEL": FAMILY_PROVIDER,
    "PROVIDER_TIMEOUT": FAMILY_PROVIDER,
}

# Programs that only read / print. A command composed of these (plus neutral shell noise) is
# INSPECTS_EVIDENCE; it cannot execute what the text it prints is talking about.
_TEXT_TOOLS = frozenset({
    "cat", "grep", "egrep", "fgrep", "rg", "ag", "ack", "sed", "head", "tail", "less", "more",
    "find", "fd", "ls", "tree", "stat", "file", "wc", "diff", "sha256sum", "md5sum", "shasum",
    "strings", "xxd", "od", "nl", "cut", "sort", "uniq", "awk", "gawk", "mawk", "jq", "printf",
    "pwd", "which", "type", "dirname", "basename", "realpath", "readlink", "tr", "column", "comm",
    "join", "paste", "fold", "fmt", "expand", "unexpand", "seq", "yes",
})
# Shell keywords / builtins / pure file bookkeeping. They neither read evidence nor execute an
# operation, so they are neutral for the role (they never turn a command into an inspection).
_NEUTRAL_TOKENS = frozenset({
    "cd", "export", "set", "unset", "source", ".", "true", "false", "test", "[", "[[", "read",
    "echo", "exit", "return", "wait", "trap", "umask", "alias", "for", "do", "done", "if", "then",
    "else", "elif", "fi", "while", "until", "case", "esac", "function", "local", "declare", "eval",
    "shift", "pushd", "popd", "break", "continue", "sleep", "mk", "mkdir", "touch", "cp", "mv",
    "rm", "rmdir", "chmod", "chown", "ln", "tee", "truncate", "xargs", "timeout", "time", "env",
    "nohup", "exec", "command", "builtin", "sudo", "nice", "strace", "which",
})
_INTERPRETERS = frozenset({"python", "python2", "python3", "py", "pypy", "pypy3"})
_SHELLS = frozenset({"bash", "sh", "dash", "zsh", "ksh", "ash"})
_BUILD_TOOLS = frozenset({
    "gradle", "gradlew", "mvn", "mvnw", "maven", "make", "gmake", "ninja", "bazel", "bazelisk",
    "ant", "msbuild", "xcodebuild", "cmake", "gcc", "g++", "clang", "clang++", "javac", "kotlinc",
    "cargo", "go", "dotnet", "swiftc", "d8", "r8", "aapt2",
})
_TEST_TOOLS = frozenset({
    "pytest", "py.test", "jest", "mocha", "vitest", "ctest", "phpunit", "rspec", "tox", "nose2",
    "karma", "ava", "jasmine", "gradlew",  # gradlew is refined by its task argument below
})
_PROVIDER_TOOLS = frozenset({
    "claude", "codex", "opencode", "openai", "anthropic", "deepseek", "gemini", "llm", "ollama",
    "curl", "wget", "http", "https", "httpie", "xh",
})
_PACKAGE_RUNNERS = frozenset({"npm", "npx", "yarn", "pnpm", "bun", "node", "deno"})

# Word tokens that name a helper script whose explicit purpose is printing / parsing / comparing /
# summarising existing Evaluation or Hermes artifacts (show_run.py, scan_calls.py, cmp_runs.py,
# dump_raw.py, inspect_removals.py, …). Only name tokens are inspected — never a file's contents.
_HELPER_WORDS = frozenset({
    "show", "scan", "dump", "cmp", "compare", "diff", "inspect", "list", "print", "prints",
    "summary", "summarise", "summarize", "summar", "parse", "extract", "view", "display", "render",
    "report", "read", "cat", "grep",
})
_BUILD_WORDS = frozenset({"build", "assemble", "compile", "gradle", "bundle", "apk", "package"})
_TEST_WORDS = frozenset({"test", "tests", "pytest", "unittest", "spec", "specs", "jest", "mocha",
                         "connectedandroidtest"})
_PROVIDER_WORDS = frozenset({"probe", "provider", "claude", "codex", "llm", "openai", "anthropic",
                             "deepseek", "gemini", "apikey", "auth"})

# Redirection operators are removed before tokenising so ``2>&1`` / ``>>`` cannot masquerade as a
# command separator or as a program token.
_REDIR_RE = re.compile(r"\d*>&\s*\d+|&>>?|\d*>>?")

# The verdict token each family is allowed to attribute (brief section 9).
_FAMILY_VERDICT_RE = {
    FAMILY_BUILD: re.compile(r"(?i)BUILD FAILED|FAILURE:\s*Build failed|Execution failed for task"),
    FAMILY_TEST: re.compile(
        r"(?i)FAILED\s*\((?=[^)]*(?:failures|errors)\s*=)|\b\d+\s+tests?\s+failed\b|"
        r"\bTESTS FAILED\b|^\s*FAILED\s*$", re.M),
    FAMILY_PROVIDER: re.compile(
        r"(?i)\b40[13]\b|\b429\b|authentication failed|invalid api key|quota exhausted|rate limit"),
}


def _split_simple_commands(command: str) -> list:
    """Quote-aware split of a shell command into its simple commands (``;`` ``&&`` ``||`` ``|``)."""
    text = (command or "").replace("\\\n", " ")     # join line continuations first
    text = _REDIR_RE.sub(" ", text)
    out, buf, i, n, quote = [], [], 0, len(text), None
    while i < n:
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == quote and text[i - 1:i] != "\\":
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch in ";|&\n(){}":
            j = i
            if ch in ";|&":
                while j < n and text[j] == ch:
                    j += 1
            else:
                j = i + 1
            out.append("".join(buf))
            buf = []
            i = j
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


# --------------------------------------------------------------------------- #
# process-control wrappers  (P0B-EVAL-WRAPPER-ROLE-FIX)
# --------------------------------------------------------------------------- #
# A command can be wrapped by a process-control utility that only *supervises* the real
# executable: ``timeout 300 python3 -m unittest …``, ``nice -n 5 ./gradlew test``,
# ``sudo -u agent python3 scan_calls.py …``. The wrapper is never the operation; its payload is.
# Each wrapper is therefore consumed together with its own options/duration and the payload is
# classified recursively, so a real execution role can never be lost behind a wrapper - and,
# symmetrically, an inspection can never be promoted to an execution.
#
# Parsing is deliberately conservative: a KNOWN wrapper whose payload cannot be resolved
# confidently yields OTHER (never INSPECTS_EVIDENCE), because an unknown capability must never
# silently downgrade an execution to an inspection (brief section 5/6).
_DURATION_RE = re.compile(r"^\d+(?:\.\d+)?[smhdSMHD]?$")
_SUDO_VALUE_OPTS = frozenset({"-u", "-g", "-p", "-C", "-U", "-r", "-t", "-T", "-h", "-R", "-D"})
_ENV_VALUE_OPTS = frozenset({"-u", "-C", "-S"})
_NICE_VALUE_OPTS = frozenset({"-n", "--adjustment"})
_IONICE_VALUE_OPTS = frozenset({"-c", "-n", "-p", "--class", "--classdata", "--pid"})
_TIMEOUT_VALUE_OPTS = frozenset({"-k", "--kill-after", "-s", "--signal"})
_TIMEOUT_FLAG_OPTS = frozenset({"--preserve-status", "--foreground", "-v", "--verbose"})
_CHRT_FLAG_OPTS = frozenset({"-m", "-o", "-i", "-b", "-f", "-r", "-d", "-a", "-v", "-R", "-S"})
_ASSIGNMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")


def _skip_flags(tokens):
    """Drop leading boolean ``-x`` / ``--long`` flags (no value argument)."""
    while tokens and tokens[0] not in ("-", "--") and tokens[0].startswith("-"):
        tokens.pop(0)
    if tokens and tokens[0] == "--":
        tokens.pop(0)
    return tokens


def _unwrap_wrappers(tokens):
    """Strip leading ``VAR=value`` assignments and process-control wrappers.

    Returns ``(tokens, ok)``; ``ok is False`` when a recognised wrapper could not be parsed
    confidently (unknown option, missing/unparseable duration, no command left), in which case the
    caller must classify the command as OTHER.
    """
    while tokens:
        tok = tokens[0]
        if _ASSIGNMENT_RE.match(tok):                     # VAR=value assignment
            tokens.pop(0)
            continue
        if tok in ("(", "{"):
            tokens.pop(0)
            continue
        if tok == "sudo":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t in _SUDO_VALUE_OPTS:
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    tokens.pop(0)
                    continue
                break
            continue
        if tok == "env":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if _ASSIGNMENT_RE.match(t):
                    tokens.pop(0)
                    continue
                if t in _ENV_VALUE_OPTS:
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    tokens.pop(0)
                    continue
                break
            continue
        if tok in ("command", "builtin", "nohup", "exec", "setsid"):
            tokens.pop(0)
            _skip_flags(tokens)
            continue
        if tok == "nice":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t in _NICE_VALUE_OPTS:
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)
                    continue
                if re.fullmatch(r"-\d+", t) or t.startswith("--adjustment="):
                    tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    return tokens, False              # unknown nice option
                break
            continue
        if tok == "ionice":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t in _IONICE_VALUE_OPTS:
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)
                    continue
                if t.startswith("--class=") or t.startswith("--classdata="):
                    tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    tokens.pop(0)
                    continue
                break
            continue
        if tok == "chrt":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t == "-p":                         # -p takes a pid
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)
                    continue
                if t in _CHRT_FLAG_OPTS:
                    tokens.pop(0)
                    continue
                if t.startswith("-") and t != "-":
                    return tokens, False              # unknown chrt option
                break
            if not tokens or not re.fullmatch(r"\d+", tokens[0]):
                return tokens, False                  # chrt requires a priority argument
            tokens.pop(0)
            continue
        if tok == "stdbuf":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t in ("-i", "-o", "-e"):           # mode is normally attached (-oL)
                    tokens.pop(0)
                    if tokens and not tokens[0].startswith("-"):
                        tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    tokens.pop(0)
                    continue
                break
            continue
        if tok == "time":
            tokens.pop(0)
            while tokens:
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t in ("-o", "--output"):
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    tokens.pop(0)
                    continue
                break
            continue
        if tok == "timeout":
            tokens.pop(0)
            while tokens:                             # options may precede the duration
                t = tokens[0]
                if t == "--":
                    tokens.pop(0)
                    break
                if t in _TIMEOUT_VALUE_OPTS:
                    tokens.pop(0)
                    if not tokens:
                        return tokens, False
                    tokens.pop(0)                     # kill-after duration / signal
                    continue
                if t.startswith("--kill-after=") or t.startswith("--signal="):
                    tokens.pop(0)
                    continue
                if t in _TIMEOUT_FLAG_OPTS:
                    tokens.pop(0)
                    continue
                if t != "-" and t.startswith("-"):
                    return tokens, False              # unknown timeout option
                break
            if not tokens or not _DURATION_RE.match(tokens[0]):
                return tokens, False                  # duration missing/unparseable
            tokens.pop(0)
            if not tokens:
                return tokens, False                  # no command after the duration
            continue
        break
    return tokens, True


def _program_and_args(simple: str):
    """First real program token of a simple command plus its argument text (wrappers stripped).

    Returns ``(program, args, ok)``; ``ok is False`` when a recognised process-control wrapper could
    not be resolved - the caller then classifies the command as OTHER, never as an inspection.
    """
    tokens = (simple or "").split()
    tokens, ok = _unwrap_wrappers(tokens)
    if not ok:
        return None, "", False
    if not tokens:
        return None, "", True
    return tokens[0], " ".join(tokens[1:]), True


def _word_tokens(basename: str) -> set:
    return {t for t in re.split(r"[^A-Za-z0-9]+", (basename or "").lower()) if t}


def _script_role(script: str) -> str:
    """Role of an interpreter-run script, decided by its name tokens only."""
    words = _word_tokens(os.path.basename(script or ""))
    if words & _TEST_WORDS:
        return ROLE_TEST
    if words & _BUILD_WORDS:
        return ROLE_BUILD
    if words & _PROVIDER_WORDS:
        return ROLE_PROVIDER
    if words & _HELPER_WORDS:
        return ROLE_INSPECT
    # An unrecognised script is neither a known helper nor a known executor: NEUTRAL (ignored for
    # the role, so it can never by itself turn a command into an inspection or into an execution).
    return None


def _role_of_simple(simple: str) -> str:
    program, args, ok = _program_and_args(simple)
    if not ok:
        # A recognised process-control wrapper whose payload could not be resolved confidently:
        # the operation's capability is unknown, so it is OTHER (never INSPECTS_EVIDENCE).
        return ROLE_OTHER
    if program is None:
        return None
    base = os.path.basename(program)
    low = base.lower()

    if base in _INTERPRETERS or low in _INTERPRETERS:
        if args.startswith("-c") or re.search(r"(?:^|\s)-c(?:\s|$)", args):
            return ROLE_OTHER                      # inline code: capability unknown
        m = re.search(r"(?:^|\s)-m\s+([A-Za-z0-9_.]+)", args)
        if m:
            module = m.group(1)
            role = _script_role(module)
            return role or ROLE_OTHER
        for tok in args.split():
            if tok.startswith("-"):
                continue
            if tok.endswith((".py", ".sh", ".bash", ".rb", ".pl", ".js", ".ts")):
                role = _script_role(tok)
                if role is not None:
                    return role
                break
        # `python3 -c` (inline code) and `-m <unknown>` are OTHER; an unrecognised *named* script
        # is NEUTRAL: its name is no evidence that it executes a build, a test or a provider call,
        # so it can neither confer INSPECTS_EVIDENCE on the command nor block one.
        if re.search(r"(?:^|\s)-c(?:\s|$)", args):
            return ROLE_OTHER
        if re.search(r"(?:^|\s)-m\s+", args):
            return ROLE_OTHER
        return None

    if low in _SHELLS:
        m = re.search(r"-c\s+(.*)", args, re.S)
        if m:
            inner = m.group(1).strip().strip("'\"")
            role = _role_of_command(inner)
            return role          # the wrapper is exactly as executing as its payload
        return ROLE_OTHER

    if low in ("gradlew", "gradle"):
        tasks = [t for t in args.split() if t and not t.startswith("-")]
        if any(re.search(r"(?i)(^|:)test|connectedandroidtest", t) for t in tasks):
            return ROLE_TEST
        if tasks or ("build" in args or "assemble" in args):
            return ROLE_BUILD
        return ROLE_BUILD

    if low in _TEST_TOOLS:
        return ROLE_TEST
    if low in _BUILD_TOOLS:
        if low in ("cargo", "go", "dotnet") and re.search(r"\btest\b", args):
            return ROLE_TEST
        return ROLE_BUILD
    if low in _PROVIDER_TOOLS:
        return ROLE_PROVIDER
    if low in _PACKAGE_RUNNERS:
        if re.search(r"(?i)\btest\b|\bjest\b|\bmocha\b|\bvitest\b", args):
            return ROLE_TEST
        if re.search(r"(?i)\bbuild\b|\bpackage\b|\bassemble\b", args):
            return ROLE_BUILD
        return ROLE_OTHER
    if low in _TEXT_TOOLS:
        return ROLE_INSPECT
    if low in _NEUTRAL_TOKENS:
        return None

    if base.endswith((".sh", ".bash", ".py", ".rb", ".pl", ".js", ".ts")):
        role = _script_role(base)                  # ./run_tests.sh, ./bin/build.sh, ./show_run.sh
        if role is not None:
            return role
    # A directly invoked, unrecognised token (including a bare path) cannot own any family and is
    # not provably an inspection either: treat it as OTHER so it is preserved (conservative).
    return ROLE_OTHER


def _aggregate_roles(roles) -> str:
    present = {r for r in roles if r}
    for execution_role in (ROLE_BUILD, ROLE_TEST, ROLE_PROVIDER):
        if execution_role in present:
            return execution_role
    if ROLE_INSPECT in present and ROLE_OTHER not in present:
        return ROLE_INSPECT
    return ROLE_OTHER


def _role_of_command(command: str) -> str:
    return _aggregate_roles(_role_of_simple(s) for s in _split_simple_commands(command))


def classify_operation_role(command: str) -> str:
    """Deterministic operation role of a shell command (never uses the result text or an LLM)."""
    return _role_of_command(command or "")


def verdict_family(failure_type: str):
    """The textual-verdict family a failure type belongs to, or None."""
    return _FAMILY_BY_TYPE.get(str(failure_type or ""))


def verdict_family_is_owned(family, operations) -> bool:
    """True when some operation can own ``family``'s textual verdict (brief section 9).

    An OTHER (unknown) role is treated as potentially owning every family, so an operation whose
    capability cannot be determined is never used to drop a failure.
    """
    if family is None:
        return True
    for op in operations or ():
        role = getattr(op, "role", None)
        if role == ROLE_OTHER or role is None:
            return True
        if family == FAMILY_BUILD and role in (ROLE_BUILD, ROLE_TEST):
            return True
        if family == FAMILY_TEST and role == ROLE_TEST:
            return True
        if family == FAMILY_PROVIDER and role == ROLE_PROVIDER:
            return True
    return False


def is_clean_success(state) -> bool:
    """A structured clean success; an exit-0 pipeline advisory of a read-only command still counts.

    The advisory makes the persisted exit status the *last pipeline stage's* status, which is why it
    is not authoritative for an unknown operation. For an INSPECTS_EVIDENCE operation (which executes
    nothing) exit 0 still means every read/print stage it ran completed.
    """
    if state.outcome == OUTCOME_SUCCEEDED:
        return True
    return bool(state.has_exit_status and state.exit_code == 0 and not state.error
                and state.status in (None, "completed"))


def _is_operation(call) -> bool:
    return getattr(call, "name", None) in OPERATION_TOOLS


@dataclass
class EventOperation:
    """One operation event of a logical failure: its command, its structured state and its role."""

    row: int
    tool: str
    command: str
    text: str
    state: OperationState
    role: str

    def as_dict(self) -> dict:
        return {
            "row": self.row,
            "tool": self.tool,
            "command": self.command[:400],
            "role": self.role,
            "state": self.state.as_dict(),
        }


def collect_event_operations(failure: dict, calls_by_row: dict) -> list:
    """Every operation event the logical failure was drawn from, with role + structured state."""
    out = []
    for row in failure.get("raw_events") or []:
        for call in calls_by_row.get(row, ()):  # noqa: B007
            if not _is_operation(call):
                continue
            text = getattr(call, "result_text", "") or ""
            tool = getattr(call, "name", "") or ""
            command = ((getattr(call, "input", None) or {}).get("command") or "")
            out.append(EventOperation(
                row=row, tool=tool, command=command, text=text,
                state=parse_operation_state(text, tool),
                role=classify_operation_role(command),
            ))
    return out


def collect_event_states(failure: dict, calls_by_row: dict) -> list:
    """(call, structured state) pairs for every operation event (kept for compatibility)."""
    ops = collect_event_operations(failure, calls_by_row)
    return [(op, op.state) for op in ops]


def inspection_context_rule(failure: dict, ops: list):
    """Remove a failure whose textual verdict belongs to no executed operation (sections 9-11).

    Fires only when every backing operation is positively classified INSPECTS_EVIDENCE, every one
    of those inspections is a clean structured success, the failure's type is a textual-verdict
    family, no operation can own that family, and one of the outputs actually carries the family's
    verdict token. Anything else - an unknown role, an executing role, a non-clean inspection, a
    failure type outside the textual families - is preserved.
    """
    if not ops:
        return None
    if not all(op.role == ROLE_INSPECT for op in ops):
        return None
    if not all(is_clean_success(op.state) for op in ops):
        return None
    family = verdict_family(failure.get("type"))
    if family is None:
        return None
    if verdict_family_is_owned(family, ops):
        return None
    if not any(_FAMILY_VERDICT_RE[family].search(op.text or "") for op in ops):
        return None
    return RULE_INSPECTION_CONTEXT


def false_positive_rule(failure: dict, ops: list):
    """Return the rule id that disproves this failure, or None when it stands.

    A compound shell command's exit status is frequently the LAST statement's status (``; echo
    DONE``) or the last pipeline stage's, so exit 0 alone never proves that the *marked*
    operation succeeded. The invoked tool's own termination verdict is therefore checked too: a
    real ``BUILD FAILED`` / ``FAILED (failures=N)`` inside an exit-0 compound command stays a
    failure.

    The rules are tried in order of increasing aggressiveness, so the stronger, text-based
    disproofs keep their existing rule attribution:

      1. OPERATION_SUCCEEDED                  - every op a clean structured success, no verdict text
      2. PROVIDER_TYPED_FROM_INSPECTION_TEXT  - a PROVIDER_* type from read-only inspection text
      3. INSPECTION_CONTEXT_NO_VERDICT_OWNER  - the quoted-verdict false positive of this phase
    """
    if not ops:
        return None
    clean = all(op.state.outcome == OUTCOME_SUCCEEDED for op in ops)
    if clean and not has_tool_failure_verdict(*[op.text for op in ops]):
        return RULE_OPERATION_SUCCEEDED
    if str(failure.get("type", "")).startswith("PROVIDER_"):
        commands = [op.command for op in ops]
        if commands and all(is_read_only_inspection(c) and not is_provider_operation(c)
                            for c in commands):
            return RULE_PROVIDER_FROM_INSPECTION_TEXT
    return inspection_context_rule(failure, ops)


def failure_is_false_positive(failure: dict, ops: list) -> bool:
    """True when the failure's evidence cannot support the classification it carries."""
    return false_positive_rule(failure, ops) is not None


def correct_logical_failures(failures: list, calls_by_row: dict) -> tuple:
    """Split failures into (kept, removed) under the prove-then-classify rule.

    Returns ``(kept, removed)`` where ``removed`` is an audit list of dicts. Order of the kept
    failures — and therefore their ``FAIL-xxx`` ids — is preserved exactly.
    """
    kept, removed = [], []
    for failure in failures or []:
        ops = collect_event_operations(failure, calls_by_row)
        rule = false_positive_rule(failure, ops)
        if rule:
            removed.append({
                "logical_failure_id": failure.get("logical_failure_id"),
                "type": failure.get("type"),
                "owner_row": failure.get("owner_row"),
                "raw_events": list(failure.get("raw_events") or []),
                "rule_id": rule,
                "rule": FALSE_POSITIVE_RULES[rule],
                "event_states": [op.state.as_dict() for op in ops],
                "event_commands": [op.command[:200] for op in ops],
                "event_operation_roles": [op.role for op in ops],
                "event_operations": [op.as_dict() for op in ops],
                "core_evidence_head": (failure.get("evidence") or "")[:200],
            })
        else:
            kept.append(failure)
    return kept, removed


def recompute_repair_linkage(failures: list, repairs: list) -> dict:
    """Recompute the core's repair_linkage rollup for the corrected failure set.

    Key set and semantics are identical to ``core.analyze``'s rollup, so an unchanged failure
    set produces an unchanged ``repair_linkage``.
    """
    unprovable = [
        {"failure_id": f["logical_failure_id"], "reason": f.get("repair_status")}
        for f in failures or []
        if f.get("repair_status") and f.get("repair_status") != "REPAIRED"
    ]
    repaired = sum(1 for f in failures or [] if f.get("repair_status") == "REPAIRED")
    return {
        "repairs": len(repairs or []),
        "repaired_failures": repaired,
        "unprovable": unprovable,
        "status": "REPAIR_LINKAGE_UNPROVABLE" if unprovable else "OK",
    }


def _provider_fallback_deviation():
    return {
        "type": "PROVIDER_FALLBACK",
        "count": 1,
        "evidence": "provider probe failed and execution fell back",
    }


def correct_run(run: dict, calls_by_row: dict) -> dict:
    """Apply the correction to a ``core.analyze`` result in place; return the audit summary.

    Only failure attribution is touched. Phases, clocks, tokens, task window, identity and
    agent-host attribution are left exactly as the frozen core produced them.
    """
    before = list(run.get("logical_failures") or [])
    kept, removed = correct_logical_failures(before, calls_by_row)

    removed_ids = {r["logical_failure_id"] for r in removed}
    # A repair whose trigger failure was removed is not a repair of anything.
    repairs = [r for r in (run.get("repairs") or [])
               if r.get("trigger_failure") not in removed_ids]

    deviations = list(run.get("execution_deviations") or [])
    provider_failures = [f for f in kept if str(f.get("type", "")).startswith("PROVIDER_")]
    removed_provider_fallback = None
    if not provider_failures:
        filtered = [d for d in deviations
                    if not (d.get("type") == "PROVIDER_FALLBACK"
                            and d.get("evidence") == _provider_fallback_deviation()["evidence"])]
        if len(filtered) != len(deviations):
            removed_provider_fallback = _provider_fallback_deviation()
        deviations = filtered

    run["logical_failures"] = kept
    run["repairs"] = repairs
    run["execution_deviations"] = deviations
    run["repair_linkage"] = recompute_repair_linkage(kept, repairs)

    summary = {
        "module_version": MODULE_VERSION,
        "rules": FALSE_POSITIVE_RULES,
        "failures_before": len(before),
        "failures_after": len(kept),
        "removed_count": len(removed),
        "removed_failures": removed,
        "provider_fallback_deviation_removed": removed_provider_fallback,
        "ids_are_stable": True,
        "note": ("a logical failure is removed only when its own operations cannot support it "
                 "(proven-successful operations, or provider typing from inspection text); "
                 "this layer can never add a failure"),
    }
    run["failure_evidence_correction"] = summary
    return summary

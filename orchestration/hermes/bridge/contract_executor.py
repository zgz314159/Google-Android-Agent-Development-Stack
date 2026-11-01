#!/usr/bin/env python3
"""Contract-package gate + Contract-Guard execution.

Two responsibilities, both strictly bounded:

  1. gate()      — prove the requested contract package is a real, project-local,
                   compiler-generated READY package whose manifest hash matches the
                   hash the task supplied. Reuses the EXISTING deterministic validator
                   (``specification/compiler/validate_package.py``) instead of
                   re-implementing the compiler's rules.

  2. execute()   — run the EXISTING generated ``EXECUTOR-PROMPT.md`` through the
                   pinned Hermes with the Contract Guard active. One fixed argv,
                   no shell, no raw NL, no alternate route.

Nothing here accepts shell text, a command string, or an arbitrary path.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from protocol import GENESIS, sha256_file  # noqa: F401  (GENESIS re-exported for callers)
    import projects  # noqa: E402
except ImportError:  # imported as a package rather than from the bridge dir
    from .protocol import GENESIS, sha256_file  # noqa: F401
    from . import projects  # noqa: E402

def _resolve_project_root() -> Path:
    """The Stack root, derived portably (env override, then this file's location)."""
    override = os.environ.get("HERMES_STACK_ROOT")
    if override:
        return Path(override)
    # <repo>/orchestration/hermes/bridge/contract_executor.py -> <repo>
    return Path(__file__).resolve().parents[3]


PROJECT_ROOT = _resolve_project_root()

# The projects root (the parent of the Stack root) that the compiler validator resolves
# against; overridable for a host whose project layout differs.
COMPILER_PROJECT_ROOT = Path(os.environ.get("HERMES_PROJECTS_ROOT") or PROJECT_ROOT.parent)

COMPILER_VALIDATOR = PROJECT_ROOT / "specification" / "compiler" / "validate_package.py"

HERMES_BIN = "hermes"
HERMES_PROFILE = "android-stack"
CONTROLLED_WRAPPER = "/usr/local/lib/aegl-bridge/run_registered_task"
CONTROLLED_TASK_REGISTRY = "/var/lib/aegl-model/registry.json"
CONTROLLED_TASK_ID_ENV = "AEGL_HERMES_TASK_ID"

# Compiler-generated artifacts a READY package must carry.
REQUIRED_ARTIFACTS = (
    "implementation-contract.json",
    "manifest.json",
    "READY.json",
    "EXECUTOR-PROMPT.md",
)

PROMPT_FILE = "EXECUTOR-PROMPT.md"
MANIFEST_FILE = "manifest.json"
READY_FILE = "READY.json"

LOG_TAIL_CHARS = 2000

# The root wrapper supervises the task and owns TERM -> grace -> KILL -> reap.
# The bridge must wait past that cleanup window; it is never allowed to kill the
# controller early and leave privileged descendants behind.
WRAPPER_GRACE_S = 10
WRAPPER_SLACK_S = 30

# Outcomes
O_SUCCESS = "SUCCESS"
O_FAILED = "FAILED"
O_BLOCKED = "BLOCKED"


class GateError(RuntimeError):
    """A contract-package gate rejected the package. Carries a stable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def as_dict(self) -> dict:
        return {"status": "REJECTED", "code": self.code, "message": self.message}


class ControlledLaunchError(GateError):
    """The pre-registered controlled Hermes task cannot be used."""


# --------------------------------------------------------------------------- #
# Path gate
# --------------------------------------------------------------------------- #

def resolve_package(package_raw: str, project_root: Path | None = None, *,
                    binding: dict | None = None) -> Path:
    """Resolve contract_package to a real directory under its declared root.

    Rejects: empty, relative, missing, not a directory, and anything whose REAL
    path escapes the declared root (symlink or ``..`` traversal). The root is an
    explicitly supplied ``project_root`` (tests/legacy) or, in production, the
    binding's ``contract_root``.
    """
    if not isinstance(package_raw, str) or not package_raw.strip():
        raise GateError("E_PACKAGE_EMPTY", "contract_package is empty")
    if not os.path.isabs(package_raw):
        raise GateError("E_PACKAGE_NOT_ABSOLUTE", "contract_package must be an absolute path")

    candidate = Path(package_raw)
    # strict=True resolves symlinks and raises on a missing component.
    try:
        real = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise GateError("E_PACKAGE_MISSING", "contract_package does not resolve: %s" % exc) from exc

    if not real.is_dir():
        raise GateError("E_PACKAGE_NOT_DIR", "contract_package is not a directory")

    if project_root is not None:
        root = Path(project_root).resolve(strict=True)
    elif binding is not None:
        root = Path(binding["contract_root"]).resolve(strict=True)
    else:
        raise GateError("E_PACKAGE_ROOT_UNSPECIFIED", "no root given to resolve_package")
    if real == root:
        raise GateError("E_PACKAGE_ESCAPE", "contract_package is the declared root itself")
    if root not in real.parents:
        raise GateError("E_PACKAGE_ESCAPE", "contract_package resolves outside the declared contract_root")

    return real


def manifest_sha256(package: Path) -> str:
    """The authoritative manifest hash: sha256 of the package's manifest.json."""
    return sha256_file(str(package / MANIFEST_FILE))


def check_artifacts(package: Path) -> None:
    for name in REQUIRED_ARTIFACTS:
        if not (package / name).is_file():
            raise GateError("E_ARTIFACT_MISSING", "required artifact missing: %s" % name)
    # The manifest is an integrity statement about the package; a manifest that
    # fails its own entries is refused before anything else runs.
    import json

    with open(package / MANIFEST_FILE, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    bad = []
    for entry in manifest.get("entries", []):
        target = package / entry.get("path", "")
        if not target.is_file() or sha256_file(str(target)) != entry.get("sha256"):
            bad.append(entry.get("path"))
    if bad:
        raise GateError("E_MANIFEST_INTEGRITY", "manifest entries do not match: %s" % ", ".join(map(str, bad)))


def check_ready(package: Path) -> None:
    import json

    with open(package / READY_FILE, "r", encoding="utf-8") as handle:
        ready = json.load(handle)
    if not isinstance(ready, dict) or ready.get("status") != "READY":
        raise GateError("E_NOT_READY", "READY.json status is not READY")


def run_package_validator(package: Path, project_root: Path = PROJECT_ROOT,
                          *, isolate: bool = True,
                          validator_project_root: str | None = str(COMPILER_PROJECT_ROOT)) -> dict:
    """Run the EXISTING deterministic validator against the package.

    ``isolate=True`` validates a byte-for-byte snapshot in a temp directory: the
    validator rewrites ``implementation-contract.json`` (readiness) and writes
    ``validation-report.json``, and a frozen contract package is a READ_ONLY_INPUT
    that must not be mutated by a gate. The package's own bytes are never touched.

    Returns {"exit_code": int, "status": "READY"|"NOT_READY"|"ERROR", "summary": str}.
    """
    if not COMPILER_VALIDATOR.is_file():
        raise GateError("E_VALIDATOR_MISSING", "compiler validator not found: %s" % COMPILER_VALIDATOR)

    with tempfile.TemporaryDirectory(prefix="hermes-pkg-gate-") as tmp:
        if isolate:
            target = Path(tmp) / "pkg"
            shutil.copytree(package, target)
        else:
            target = package
        # The validator resolves read_first against --project-root when given, else
        # against the package's own source_root. A binding may pin it (Stack keeps its
        # historical shared projects root) or set it to None (IAP resolves against the
        # disposable task root the contract declares).
        argv = [sys.executable, str(COMPILER_VALIDATOR), str(target)]
        if validator_project_root is not None:
            argv += ["--project-root", str(validator_project_root)]
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
        )
        summary = (proc.stdout or "").strip().splitlines()
        first = summary[0] if summary else ""
        status = "READY" if proc.returncode == 0 else "NOT_READY"
        if proc.returncode not in (0, 1):
            status = "ERROR"
        return {
            "exit_code": proc.returncode,
            "status": status,
            "summary": first[:400],
            "stderr_tail": (proc.stderr or "")[-400:],
        }


# --------------------------------------------------------------------------- #
# Self-modification gate (live EXECUTE_CONTRACT only)
# --------------------------------------------------------------------------- #
#
# Transport authenticity proves who sent a task, not that the task is safe to run.
# A live task whose validated contract authorizes a control-plane prefix could
# rewrite the bridge, the guard or the compiler that judges it. This gate refuses
# that on semantics, BEFORE the task identity is consumed.

E_SELF_MODIFY_CONTROL_PLANE = "E_SELF_MODIFY_CONTROL_PLANE"

# Project-relative control-plane prefixes, in the same rel-path form the Contract
# Guard resolves against its source_root (both the bare repo-relative form and the
# "Google-Android-Agent-Development-Stack/..." form are accepted, see _canonical_rel).
CONTROL_PLANE_PATHS = (
    "orchestration/hermes/bridge/",
    "orchestration/hermes/evaluation_adapter/contract_guard.py",
    "orchestration/hermes/evaluation_adapter/hooks/",
    "orchestration/hermes/HERMES-LOCK.json",
    "specification/compiler/",
    ".hermes.md",
)

_REPO_PREFIX = "Google-Android-Agent-Development-Stack/"


def _canonical_rel(path) -> str:
    """Repo-relative posix form, with an optional leading project-dir segment dropped."""
    text = str(path).replace("\\", "/").strip().rstrip("/")
    if text == _REPO_PREFIX.rstrip("/"):
        return ""
    if text.startswith(_REPO_PREFIX):
        text = text[len(_REPO_PREFIX):]
    return text


def _path_overlaps(allowed: str, protected: str) -> bool:
    """True when two relative paths are equal, one contains the other, or one is the other's parent."""
    if not allowed or not protected:
        return False
    if allowed == protected:
        return True
    return allowed.startswith(protected + "/") or protected.startswith(allowed + "/")


def control_plane_overlaps(allowed_paths) -> list[str]:
    """The subset of ``allowed_paths`` that overlaps the control plane."""
    protected = [_canonical_rel(item) for item in CONTROL_PLANE_PATHS]
    hits: list[str] = []
    for entry in allowed_paths or []:
        canonical = _canonical_rel(entry)
        if any(_path_overlaps(canonical, item) for item in protected):
            hits.append(entry)
    return hits


def check_self_modification(allowed_paths) -> None:
    """Raise ``E_SELF_MODIFY_CONTROL_PLANE`` when a live contract can rewrite the control plane."""
    hits = control_plane_overlaps(allowed_paths)
    if hits:
        raise GateError(
            E_SELF_MODIFY_CONTROL_PLANE,
            "live EXECUTE_CONTRACT authorizes control-plane path(s): %s" % ", ".join(map(str, hits)),
        )


def _controlled_task_id(task_id=None) -> str:
    if task_id is None:
        task_id = os.environ.get(CONTROLLED_TASK_ID_ENV, "")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_ID_MISSING",
            "%s is required; register a task with the installed aegl-model-task as root"
            % CONTROLLED_TASK_ID_ENV,
        )
    return task_id.strip()


def controlled_task_check(package, *, task_id=None,
                          registry_path=CONTROLLED_TASK_REGISTRY,
                          wrapper=CONTROLLED_WRAPPER,
                          require_root_owner: bool = True) -> dict:
    """Require a root-registered task and the fixed root-owned launch wrapper."""
    task_id = _controlled_task_id(task_id)
    registry = os.fspath(registry_path)
    if not os.path.isfile(registry):
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_REGISTRY_INVALID",
            "trusted task registry missing: %s" % registry,
        )
    try:
        with open(registry, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_REGISTRY_INVALID",
            "trusted task registry invalid: %s" % exc,
        ) from exc
    if not isinstance(data, dict):
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_REGISTRY_INVALID",
            "trusted task registry must be a JSON object",
        )
    entry = data.get(task_id)
    if not isinstance(entry, dict):
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_NOT_REGISTERED",
            "task %r is not registered in %s; use the installed aegl-model-task as root"
            % (task_id, registry),
        )
    entry_package = entry.get("contract_package")
    if not isinstance(entry_package, str) or not entry_package:
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_CONTRACT_MISMATCH",
            "registered task %r has no contract_package" % task_id,
        )
    if os.path.realpath(entry_package) != os.path.realpath(os.fspath(package)):
        raise ControlledLaunchError(
            "E_CONTROLLED_TASK_CONTRACT_MISMATCH",
            "registered task %r contract_package does not match the validated package"
            % task_id,
        )
    wrapper_path = os.fspath(wrapper)
    if not os.path.isfile(wrapper_path) or not os.access(wrapper_path, os.X_OK):
        raise ControlledLaunchError(
            "E_CONTROLLED_WRAPPER_MISSING",
            "controlled launch wrapper missing or not executable: %s" % wrapper_path,
        )
    if require_root_owner:
        st = os.stat(wrapper_path)
        if st.st_uid != 0:
            raise ControlledLaunchError(
                "E_CONTROLLED_WRAPPER_NOT_ROOT",
                "controlled launch wrapper must be root-owned: %s" % wrapper_path,
            )
        if st.st_mode & 0o022:
            raise ControlledLaunchError(
                "E_CONTROLLED_WRAPPER_WRITABLE",
                "controlled launch wrapper must not be group/other writable: %s" % wrapper_path,
            )
    return {"task_id": task_id, "wrapper": wrapper_path, "entry": entry}


def gate(package_raw: str, supplied_manifest_sha256: str,
         project_root: Path | None = None, *, project: str | None = None,
         binding: dict | None = None, task_id=None,
         task_registry=CONTROLLED_TASK_REGISTRY,
         wrapper=CONTROLLED_WRAPPER,
         require_root_owner: bool = True) -> dict:
    """Full package gate. Raises GateError on the first failure.

    ``project`` MUST come from the validated HERMES_TASK_V1 envelope (or an explicit
    ``binding`` in tests); it is never inferred from a path. The task identity, the
    trusted registration entry, the root-frozen contract and the execution worktree are
    then cross-checked so a run can never target the wrong project. When the binding
    requires it, repo ownership is proven with real git before anything executes.

    Order matters: the manifest hash is checked against the PRISTINE package before the
    validator runs, so the supplied hash describes exactly the bytes the validator judges.
    """
    binding = binding or projects.binding_for(project)
    if binding is None:
        raise GateError("E_PROJECT", "project %r is not in the allowlist" % (project,))

    package = resolve_package(package_raw, project_root, binding=binding)
    check_artifacts(package)

    actual = manifest_sha256(package)
    if supplied_manifest_sha256 != actual:
        raise GateError(
            "E_MANIFEST_HASH_MISMATCH",
            "supplied contract_manifest_sha256 does not match the package manifest",
        )

    # Trusted registration: fixed wrapper + root-owned entry whose contract_package
    # matches this validated package.
    controlled = controlled_task_check(
        package, task_id=task_id, registry_path=task_registry,
        wrapper=wrapper, require_root_owner=require_root_owner,
    )
    entry = controlled["entry"]

    # registry project PATH must be exactly the declared formal source root
    registry_project = entry.get("project")
    if not isinstance(registry_project, str) or \
            os.path.realpath(registry_project) != os.path.realpath(binding["formal_source_root"]):
        raise GateError(
            "E_EXT_REGISTRY_PROJECT",
            "registry project %r is not the declared formal source root %s"
            % (registry_project, binding["formal_source_root"]),
        )

    with open(package / "project-context.json", "r", encoding="utf-8") as handle:
        context = json.load(handle)

    contract_root = Path(project_root) if project_root is not None else Path(binding["contract_root"])
    verdict = projects.validate_project(
        project,
        package_real=str(package),
        contract_root=str(contract_root),
        context_project=context.get("project"),
        context_source_root=context.get("source_root"),
        context_allowed_paths=context.get("allowed_paths"),
        worktree=entry.get("worktree"),
        binding=binding,
    )
    if not verdict["ok"]:
        raise GateError(verdict["code"], verdict["message"])

    if binding.get("require_git_ownership"):
        ownership = projects.verify_git_binding(entry.get("worktree"), binding["formal_source_root"])
        if not ownership["ok"]:
            raise GateError(ownership["code"], ownership["message"])

    check_ready(package)

    validation = run_package_validator(
        package, project_root or PROJECT_ROOT,
        validator_project_root=projects.validator_project_root_for(project),
    )
    if validation["status"] != "READY":
        raise GateError(
            "E_PACKAGE_NOT_READY",
            "compiler validator reported %s (%s)" % (validation["status"], validation["summary"]),
        )

    with open(package / "implementation-contract.json", "r", encoding="utf-8") as handle:
        contract = json.load(handle)

    return {
        "status": "READY",
        "project": project,
        "package": str(package),
        "manifest_sha256": actual,
        "prompt": str(package / PROMPT_FILE),
        "allowed_paths": list(contract.get("allowed_paths", [])),
        "forbidden_paths": list(contract.get("forbidden_paths", [])),
        "validator": validation,
        "controlled_task_id": controlled["task_id"],
        "controlled_wrapper": controlled["wrapper"],
    }


# --------------------------------------------------------------------------- #
# Contract-Guard execution
# --------------------------------------------------------------------------- #

def hermes_inner_argv(prompt_path: Path) -> list[str]:
    """The Hermes argv INSIDE the controlled sandbox (never executed directly)."""
    return [
        HERMES_BIN,
        "-p", HERMES_PROFILE,
        "chat",
        "--oneshot",
        "--query-file", str(prompt_path),
    ]


def hermes_argv(prompt_path: Path, *, task_id=None, wrapper=CONTROLLED_WRAPPER,
                manifest_sha256=None, require_root_owner: bool = True) -> list[str]:
    """zhong -> narrow sudo -> fixed root wrapper -> installed sandbox."""
    task_id = _controlled_task_id(task_id)
    if not isinstance(manifest_sha256, str) or len(manifest_sha256) != 64:
        raise ControlledLaunchError(
            "E_CONTROLLED_MANIFEST_SHA_MISSING",
            "expected contract manifest sha256 is required",
        )
    wrapper_path = os.fspath(wrapper)
    if not os.path.isfile(wrapper_path) or not os.access(wrapper_path, os.X_OK):
        raise ControlledLaunchError(
            "E_CONTROLLED_WRAPPER_MISSING",
            "controlled launch wrapper missing or not executable: %s" % wrapper_path,
        )
    if require_root_owner:
        st = os.stat(wrapper_path)
        if st.st_uid != 0:
            raise ControlledLaunchError(
                "E_CONTROLLED_WRAPPER_NOT_ROOT",
                "controlled launch wrapper must be root-owned: %s" % wrapper_path,
            )
        if st.st_mode & 0o022:
            raise ControlledLaunchError(
                "E_CONTROLLED_WRAPPER_WRITABLE",
                "controlled launch wrapper must not be group/other writable: %s" % wrapper_path,
            )
    return [
        "sudo", "-n", "--", wrapper_path,
        "--task-id", task_id,
        "--prompt-file", str(prompt_path),
        "--expected-manifest-sha256", manifest_sha256,
    ]


_AEGL_TIMEOUT_RE = re.compile(r"AEGL_TASK_TIMEOUT\b[^\n]*\bphase=([A-Za-z]+)")


def _wrapper_markers(stderr: str) -> dict:
    """Structure the wrapper's timeout/cleanup markers.

    Only the structured state is extracted — never the raw log — so the Bridge and the
    Campaign can carry it without persisting stdout/stderr that may contain prompts,
    model text, headers or credentials. Missing markers are reported as UNKNOWN.
    """
    text = stderr or ""
    cleanup = "UNKNOWN"
    if "AEGL_TASK_CLEANUP=CONFIRMED" in text:
        cleanup = "CONFIRMED"
    elif "AEGL_TASK_CLEANUP=UNCONFIRMED" in text:
        cleanup = "UNCONFIRMED"
    return {
        "timed_out": "AEGL_TASK_TIMEOUT" in text,
        "timeout_phases": sorted(set(_AEGL_TIMEOUT_RE.findall(text))),
        "cleanup": cleanup,
    }


def execute(package: str, prompt_path: Path, max_runtime_s: int, *,
            project_root: Path = PROJECT_ROOT, runner=subprocess.run,
            base_env: dict | None = None, task_id=None,
            task_registry=CONTROLLED_TASK_REGISTRY,
            wrapper=CONTROLLED_WRAPPER,
            require_root_owner: bool = True) -> dict:
    """Run the validated EXECUTOR-PROMPT.md under the Contract Guard.

    Sets HERMES_CONTRACT_PACKAGE to the validated package (the Contract Guard's own
    documented switch) and never disables the guard.
    """
    env = dict(os.environ if base_env is None else base_env)
    env["HERMES_CONTRACT_PACKAGE"] = str(package)

    try:
        controlled = controlled_task_check(
            package, task_id=task_id, registry_path=task_registry,
            wrapper=wrapper, require_root_owner=require_root_owner,
        )
        contract_manifest = manifest_sha256(Path(package))
        argv = hermes_argv(prompt_path, task_id=controlled["task_id"],
                           wrapper=controlled["wrapper"],
                           manifest_sha256=contract_manifest,
                           require_root_owner=require_root_owner)
        argv = [
            *argv,
            "--max-runtime", str(max(1, int(max_runtime_s))),
            "--grace", str(WRAPPER_GRACE_S),
        ]
    except GateError as exc:
        return {
            "outcome": O_BLOCKED,
            "exit_code": 1,
            "argv": [],
            "stdout_tail": "",
            "stderr_tail": exc.message,
            "reason": exc.code,
            "timed_out": "UNKNOWN",
            "timeout_phases": [],
            "cleanup": "UNKNOWN",
        }
    runtime_s = max(1, int(max_runtime_s))
    try:
        proc = runner(
            argv,
            capture_output=True,
            text=True,
            timeout=runtime_s + WRAPPER_GRACE_S + WRAPPER_SLACK_S,
            cwd=str(project_root),
            env=env,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "outcome": O_BLOCKED,
            "exit_code": 125,
            "argv": argv,
            "stdout_tail": (exc.stdout or "")[-LOG_TAIL_CHARS:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (
                "controller wait exceeded after %ss; wrapper cleanup not confirmed"
                % (runtime_s + WRAPPER_GRACE_S + WRAPPER_SLACK_S)
            ),
            "timed_out": True,
            "timeout_phases": [],
            "cleanup": "UNKNOWN",
        }

    exit_code = int(proc.returncode)
    if exit_code == 0:
        outcome = O_SUCCESS
    elif exit_code in (124, 125):
        outcome = O_BLOCKED
    else:
        outcome = O_FAILED
    return {
        "outcome": outcome,
        "exit_code": exit_code,
        "argv": argv,
        "stdout_tail": (proc.stdout or "")[-LOG_TAIL_CHARS:],
        "stderr_tail": (proc.stderr or "")[-LOG_TAIL_CHARS:],
        **_wrapper_markers(proc.stderr),
    }

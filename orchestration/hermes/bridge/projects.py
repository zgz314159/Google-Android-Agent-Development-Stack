#!/usr/bin/env python3
"""projects.py — declared, default-deny project bindings for the HERMES_TASK_V1 kernel.

Replaces the single-entry allowlist in ``protocol.py``::

    ALLOWED_PROJECTS = frozenset({"Google-Android-Agent-Development-Stack"})

with a verifiable binding table. A live EXECUTE_CONTRACT task is executable only when
its identities agree, and each identity is taken from a TRUSTED source, never inferred
from a path:

    task.project (validated envelope)
        == registry["project"] basename + formal root
        == contract project-context.json "project"
        == binding identity

The *approved* task root is the contract's own ``source_root``: the contract package is
root-owned and was already validated at registration by the trusted registrar
(AEGL ``model_task_registry._validate_contract``), so no new registry field is needed.
The bridge re-checks the relation statically, and — for bindings that require it — the
repo ownership is proven with REAL git queries.

Standard library only.
"""

from __future__ import annotations

import os
import subprocess

SCHEMA_VERSION = 3

_HOME = os.path.expanduser("~")


def _home(*parts):
    return os.path.join(_HOME, *parts)


# The AEGL sandbox's allowed disposable-worktree bases (mirror of
# recovery/model_task_registry.py ALLOWED_BASES). Every binding's worktree_bases MUST
# be a subset of this.
AEGL_ALLOWED_BASES = ("/tmp/", "/var/tmp/", "/run/aegl-", "/var/lib/aegl-")

# Roots too broad to be "this task's approved source root".
FORBIDDEN_BROAD_ROOTS = (
    "/", "/home", "/var", "/tmp", "/var/tmp", "/run",
    _HOME, _home("Projects"), _home("AndroidStudioProjects"),
)

PROJECT_BINDINGS: dict[str, dict] = {
    "Google-Android-Agent-Development-Stack": {
        "formal_source_root": _home("Projects", "Google-Android-Agent-Development-Stack"),
        "contract_root": _home("Projects", "Google-Android-Agent-Development-Stack",
                               "reports", "contracts"),
        "worktree_bases": AEGL_ALLOWED_BASES,
        "promotion_target_ref": "refs/heads/master",
        "hermes_profile": "android-stack",
        # Historical validator behaviour, kept verbatim for Stack compatibility.
        "validator_project_root": _home("Projects"),
        # Legacy: the formal Stack .git is aegl-broker-only and MUST NOT be relaxed, so
        # the bridge (an unprivileged identity) cannot read it. Ownership for Stack is
        # proven by the root registration path, not here.
        "require_git_ownership": False,
    },
    "ImageAnalysisFactory": {
        "formal_source_root": _home("AndroidStudioProjects", "ImageAnalysisFactory"),
        "contract_root": "/var/lib/aegl-model/trusted/ImageAnalysisFactory/reports/contracts",
        "worktree_bases": ("/var/tmp/",),
        "promotion_target_ref": "refs/heads/main",
        "hermes_profile": "android-stack",
        # IAP packages scope read_first to the disposable task root: do not override.
        "validator_project_root": None,
        # IAP's own repository metadata is operator-controlled and readable by the
        # bridge identity, so require a live git-ownership proof at the gate.
        "require_git_ownership": True,
    },
}

ALLOWED_PROJECTS = frozenset(PROJECT_BINDINGS)


def binding_for(project):
    return PROJECT_BINDINGS.get(project) if isinstance(project, str) else None


def target_ref_for(project):
    b = binding_for(project)
    return b["promotion_target_ref"] if b else None


def profile_for(project):
    b = binding_for(project)
    return b["hermes_profile"] if b else None


def validator_project_root_for(project):
    b = binding_for(project)
    return None if b is None else b.get("validator_project_root")


def _real(path):
    return os.path.realpath(os.fspath(path)) if path else ""


def _under(child, base):
    if not child or not base:
        return False
    base = base.rstrip("/")
    return child == base or child.startswith(base + "/")


def _is_broad_root(root):
    if not root:
        return True
    return root.rstrip("/") in {r.rstrip("/") for r in FORBIDDEN_BROAD_ROOTS}


def worktree_bases_are_safe(binding):
    return all(
        any(base.startswith(allowed) for allowed in AEGL_ALLOWED_BASES)
        for base in binding.get("worktree_bases", ())
    )


# --------------------------------------------------------------------------- #
# Git ownership (real queries)
# --------------------------------------------------------------------------- #

class GitError(RuntimeError):
    pass


def _git(args, cwd, trusted=()):
    """Run one git query.

    ``safe.directory`` is set to the EXACT, already-resolved repository/worktree paths
    for this one command only — never a wildcard, never global config, never an ACL
    change. A git failure is raised, never swallowed.
    """
    argv = ["git"]
    for path in trusted:
        argv += ["-c", "safe.directory=%s" % os.path.realpath(os.fspath(path))]
    argv += ["-C", os.fspath(cwd), *args]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise GitError("git %s failed in %s: %s" % (" ".join(args), cwd, (proc.stderr or "").strip()[:200]))
    return proc.stdout.strip()


def _abspath_in(base, value):
    return os.path.realpath(value if os.path.isabs(value) else os.path.join(base, value))


def git_identity(worktree, trusted=None):
    """Real git identity: toplevel / git-dir / common-dir / HEAD.

    Trust is limited to the supplied exact paths (default: the worktree itself).
    git may report ``--git-common-dir`` relative to the worktree, so every reported
    path is resolved against the worktree, never this process's cwd.
    """
    wt = os.path.realpath(os.fspath(worktree))
    trusted = tuple(trusted) if trusted else (wt,)
    return {
        "worktree": wt,
        "toplevel": _abspath_in(wt, _git(["rev-parse", "--show-toplevel"], wt, trusted)),
        "git_dir": _abspath_in(wt, _git(["rev-parse", "--absolute-git-dir"], wt, trusted)),
        "common_dir": _abspath_in(wt, _git(["rev-parse", "--git-common-dir"], wt, trusted)),
        "head": _git(["rev-parse", "HEAD"], wt, trusted),
    }


def verify_git_binding(worktree, formal_source_root):
    """Prove the worktree really belongs to the formal repo, using real git.

    Requires: the worktree is its own toplevel, its common dir is the formal repo's
    ``.git``, and its git dir is under ``<formal>/.git/worktrees``.
    """
    formal = os.path.realpath(os.fspath(formal_source_root))
    try:
        ident = git_identity(worktree, trusted=(worktree, formal))
    except GitError as exc:
        return {"ok": False, "code": "E_EXT_WORKTREE_GIT", "message": str(exc), "identity": None}
    if ident["toplevel"] != ident["worktree"]:
        return {"ok": False, "code": "E_EXT_WORKTREE_GIT", "identity": ident,
                "message": "worktree toplevel %s != worktree %s" % (ident["toplevel"], ident["worktree"])}
    if ident["common_dir"] != os.path.join(formal, ".git"):
        return {"ok": False, "code": "E_EXT_WORKTREE_GIT", "identity": ident,
                "message": "git common dir %s is not %s/.git" % (ident["common_dir"], formal)}
    if not _under(ident["git_dir"], os.path.join(formal, ".git", "worktrees")):
        return {"ok": False, "code": "E_EXT_WORKTREE_GIT", "identity": ident,
                "message": "git dir %s is not under %s/.git/worktrees" % (ident["git_dir"], formal)}
    return {"ok": True, "code": "OK", "message": "git binding verified", "identity": ident}


# --------------------------------------------------------------------------- #
# Codes + validation
# --------------------------------------------------------------------------- #

E_PROJECT = "E_PROJECT"
E_EXT_BINDING_UNSAFE = "E_EXT_BINDING_UNSAFE"
E_EXT_CONTRACT_ROOT = "E_EXT_CONTRACT_ROOT"
E_EXT_CONTRACT_PROJECT = "E_EXT_CONTRACT_PROJECT"
E_EXT_SOURCE_ROOT_MISSING = "E_EXT_SOURCE_ROOT_MISSING"
E_EXT_SOURCE_ROOT_BROAD = "E_EXT_SOURCE_ROOT_BROAD"
E_EXT_ALLOWED_PATHS = "E_EXT_ALLOWED_PATHS"
E_EXT_WORKTREE_SOURCE_ROOT = "E_EXT_WORKTREE_SOURCE_ROOT"
E_EXT_WORKTREE_NOT_ALLOWED = "E_EXT_WORKTREE_NOT_ALLOWED"
E_EXT_WORKTREE_BASE = "E_EXT_WORKTREE_BASE"
E_EXT_WORKTREE_IS_FORMAL = "E_EXT_WORKTREE_IS_FORMAL"


def validate_project(
    project, *, package_real, contract_root, context_project, context_source_root,
    context_allowed_paths, worktree, binding=None,
):
    """Static cross-check of a live EXECUTE_CONTRACT task against its binding.

    Every value comes from a TRUSTED source (validated envelope, trusted registry,
    root-frozen contract). Returns ``{"ok","code","message","binding"}``; default deny.
    """

    def reject(code, message):
        return {"ok": False, "code": code, "message": message, "binding": None}

    binding = binding or binding_for(project)
    if binding is None:
        return reject(E_PROJECT, "project %r is not in the allowlist" % (project,))
    if not worktree_bases_are_safe(binding):
        return reject(E_EXT_BINDING_UNSAFE, "binding %r declares unsafe worktree bases" % (project,))

    pkg = _real(package_real)
    if not _under(pkg, _real(contract_root)):
        return reject(E_EXT_CONTRACT_ROOT, "package %s is not under %s" % (pkg, contract_root))
    if not isinstance(context_project, str) or context_project != project:
        return reject(E_EXT_CONTRACT_PROJECT, "contract project %r != task project %r" % (context_project, project))

    src = _real(context_source_root)
    if not src:
        return reject(E_EXT_SOURCE_ROOT_MISSING, "contract source_root is missing")
    if _is_broad_root(src):
        return reject(E_EXT_SOURCE_ROOT_BROAD, "contract source_root %s is a forbidden broad root" % src)

    wt = _real(worktree)
    if not wt:
        return reject(E_EXT_WORKTREE_SOURCE_ROOT, "registry worktree is empty")
    if not _under(wt, src):
        return reject(E_EXT_WORKTREE_SOURCE_ROOT, "worktree %s is not inside contract source_root %s" % (wt, src))

    if not isinstance(context_allowed_paths, list) or not context_allowed_paths:
        return reject(E_EXT_ALLOWED_PATHS, "contract allowed_paths must be a non-empty list")
    rel = os.path.relpath(wt, src).replace(os.sep, "/")
    if not any(rel == a.rstrip("/") or rel.startswith(a.rstrip("/") + "/") for a in context_allowed_paths):
        return reject(E_EXT_WORKTREE_NOT_ALLOWED, "worktree %s is not authorized by allowed_paths" % wt)

    if _under(wt, _real(binding["formal_source_root"])):
        return reject(E_EXT_WORKTREE_IS_FORMAL, "worktree %s is the formal source root" % wt)
    if not any(_under(wt, _real(base)) for base in binding["worktree_bases"]):
        return reject(E_EXT_WORKTREE_BASE, "worktree %s is outside every declared base" % wt)

    return {"ok": True, "code": "OK", "message": "project binding verified", "binding": binding}


if __name__ == "__main__":
    import json
    print(json.dumps(PROJECT_BINDINGS, indent=2, sort_keys=True))

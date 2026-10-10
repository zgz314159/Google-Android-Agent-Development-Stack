#!/usr/bin/env python3
"""Canonical filesystem path contract for the Google Android Agent Development Stack.

Single source of truth for every host path the stack reads or writes. Python callers
import this module; shell callers use the companion query command
``scripts/stack-paths.sh`` (which delegates here), so the resolution logic is never
duplicated.

Contract
--------
    PROJECT_ROOT     = discovered from the checked-out source tree (or $ANDROID_AGENT_STACK_ROOT)
    STACK_STATE_ROOT = ${ANDROID_AGENT_STACK_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/google-android-agent-stack}
    STACK_DATA_ROOT  = ${ANDROID_AGENT_STACK_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/google-android-agent-stack}
    STACK_CACHE_ROOT = ${ANDROID_AGENT_STACK_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/google-android-agent-stack}
    STACK_CONFIG_ROOT= ${ANDROID_AGENT_STACK_CONFIG_ROOT:-${XDG_CONFIG_HOME:-$HOME/.config}/google-android-agent-stack}
    HERMES_HOME      = ${HERMES_HOME:-$HOME/.hermes}

No hard-coded username and no path inside ``PROJECT_ROOT`` is used as a runtime output
root. Generated state, artifacts, caches and host config all live outside the project.

Import idiom for a Python writer (adjust the parent depth to the caller's location)::

    import os, sys
    _REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(_REPO, "scripts", "lib"))
    import stack_paths
    OUTPUT_ROOT = stack_paths.evaluation_output_root()

CLI::

    stack_paths.py                 # JSON of every root
    stack_paths.py query NAME      # one resolved path
    stack_paths.py export          # shell `export NAME=value` lines (eval-able)
    stack_paths.py ensure [NAME...]# create the roots (state/data/cache/config) with 0700
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

APP_DIRNAME = "google-android-agent-stack"

ENV_PROJECT = "ANDROID_AGENT_STACK_ROOT"
ENV_STATE = "ANDROID_AGENT_STACK_STATE_ROOT"
ENV_DATA = "ANDROID_AGENT_STACK_DATA_ROOT"
ENV_CACHE = "ANDROID_AGENT_STACK_CACHE_ROOT"
ENV_CONFIG = "ANDROID_AGENT_STACK_CONFIG_ROOT"
ENV_HERMES = "HERMES_HOME"


def _expand(raw: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(raw)))


def _xdg(env_var: str, xdg_var: str, fallback_rel: str) -> Path:
    override = os.environ.get(env_var)
    if override:
        return _expand(override)
    base = os.environ.get(xdg_var)
    base_path = _expand(base) if base else _expand(fallback_rel)
    return base_path / APP_DIRNAME


def project_root() -> Path:
    """The checked-out Stack root: env override, else discovered from this file's location."""
    override = os.environ.get(ENV_PROJECT)
    if override:
        return _expand(override).resolve()
    # <repo>/scripts/lib/stack_paths.py -> <repo>
    return Path(__file__).resolve().parents[2]


def state_root() -> Path:
    return _xdg(ENV_STATE, "XDG_STATE_HOME", "~/.local/state")


def data_root() -> Path:
    return _xdg(ENV_DATA, "XDG_DATA_HOME", "~/.local/share")


def cache_root() -> Path:
    return _xdg(ENV_CACHE, "XDG_CACHE_HOME", "~/.cache")


def config_root() -> Path:
    return _xdg(ENV_CONFIG, "XDG_CONFIG_HOME", "~/.config")


def hermes_home() -> Path:
    return _expand(os.environ.get(ENV_HERMES) or "~/.hermes")


# --------------------------------------------------------------------------- #
# Derived, contract-named sub-paths
# --------------------------------------------------------------------------- #

def artifacts_root() -> Path:
    return data_root() / "artifacts"


def evaluation_output_root() -> Path:
    """Default destination for the Evaluation / Auto-Finalizer output tree."""
    return artifacts_root() / "evaluation"


def filesystem_hardening_root() -> Path:
    return artifacts_root() / "filesystem-hardening"


def migration_archive_root() -> Path:
    return artifacts_root() / "migration-archive"


def bridge_state_root() -> Path:
    return state_root() / "bridge"


def supervisor_state_root() -> Path:
    return state_root() / "supervisor"


def browser_state_root() -> Path:
    return state_root() / "browser"


def telemetry_root() -> Path:
    return state_root() / "telemetry"


def guard_state_root() -> Path:
    return state_root() / "guard"


# --------------------------------------------------------------------------- #
# Introspection
# --------------------------------------------------------------------------- #

def roots() -> dict[str, str]:
    """Every contract root and derived sub-path, resolved to absolute strings."""
    values = {
        "PROJECT_ROOT": project_root(),
        "STACK_STATE_ROOT": state_root(),
        "STACK_DATA_ROOT": data_root(),
        "STACK_CACHE_ROOT": cache_root(),
        "STACK_CONFIG_ROOT": config_root(),
        "HERMES_HOME": hermes_home(),
        "STACK_ARTIFACTS_ROOT": artifacts_root(),
        "STACK_EVALUATION_OUTPUT_ROOT": evaluation_output_root(),
        "STACK_FILESYSTEM_HARDENING_ROOT": filesystem_hardening_root(),
        "STACK_MIGRATION_ARCHIVE_ROOT": migration_archive_root(),
        "STACK_BRIDGE_STATE_ROOT": bridge_state_root(),
        "STACK_SUPERVISOR_STATE_ROOT": supervisor_state_root(),
        "STACK_BROWSER_STATE_ROOT": browser_state_root(),
        "STACK_TELEMETRY_ROOT": telemetry_root(),
        "STACK_GUARD_STATE_ROOT": guard_state_root(),
    }
    return {name: str(path) for name, path in values.items()}


def resolve(name: str) -> Path:
    """Resolve one contract name; case-insensitive on the leading STACK_/PROJECT_ tokens."""
    table = roots()
    if name in table:
        return Path(table[name])
    upper = name.upper()
    if upper in table:
        return Path(table[upper])
    if not upper.startswith("STACK_") and ("STACK_" + upper) in table:
        return Path(table["STACK_" + upper])
    raise KeyError("unknown path name: %r" % (name,))


SECRET_MODE_ROOTS = (ENV_STATE, ENV_DATA, ENV_CACHE, ENV_CONFIG, ENV_HERMES)


def ensure(names=None) -> list[str]:
    """Create the named roots (default: the four XDG contract roots) with 0700."""
    if names is None:
        names = ["STACK_STATE_ROOT", "STACK_DATA_ROOT", "STACK_CACHE_ROOT", "STACK_CONFIG_ROOT"]
    created: list[str] = []
    for name in names:
        path = resolve(name)
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
        created.append(str(path))
    return created


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="stack_paths", description="Stack filesystem path contract")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("json", help="print every root as JSON (default)")
    p_query = sub.add_parser("query", help="print one resolved path")
    p_query.add_argument("name")
    sub.add_parser("export", help="print eval-able `export NAME=value` lines")
    p_ensure = sub.add_parser("ensure", help="create the contract roots (0700)")
    p_ensure.add_argument("names", nargs="*")

    args = parser.parse_args(argv)

    if args.command == "query":
        try:
            print(resolve(args.name))
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return 0

    if args.command == "export":
        for name, value in sorted(roots().items()):
            print("export %s=%s" % (name, _shell_quote(value)))
        return 0

    if args.command == "ensure":
        for path in ensure(args.names or None):
            print(path)
        return 0

    print(json.dumps(roots(), indent=2, sort_keys=True))
    return 0


def _shell_quote(value: str) -> str:
    if value and all(ch.isalnum() or ch in "/._-:" for ch in value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    raise SystemExit(main())

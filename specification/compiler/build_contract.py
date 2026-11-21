#!/usr/bin/env python3
"""Assemble implementation-contract.json (+ EXECUTOR-PROMPT.md) from a spec package.

Deterministic. Reads only the authored artifacts and the manifest; it writes no prose
of its own beyond fixing references and generating the executor prompt. A missing
required input is a hard failure — it never invents content.

Usage: python3 build_contract.py <spec-package-dir>
Exit: 0 ok, 1 input missing/invalid, 2 error.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spec_lib import (
    CONTRACT_FILE,
    MANIFEST_FILE,
    PROMPT_FILE,
    find_json_block,
    load_json,
    parse_acceptance,
    parse_requirements,
    parse_tasks,
    read_text,
    spec_version,
    write_json,
)

VI_KEYS = [
    "feature_id",
    "journey_id",
    "engine",
    "acceptance_ids",
    "required_selectors",
    "cli_checks",
    "persistence_checks",
    "rotation_checks",
    "search_checks",
    "fixture_intent",
    "oracle_intent",
]


class BuildError(Exception):
    """A required input is missing or unusable."""


def _require(pkg: str, name: str) -> str:
    path = os.path.join(pkg, name)
    if not os.path.exists(path):
        raise BuildError(f"missing required input: {name}")
    return path


def build(pkg: str) -> dict:
    pc = load_json(_require(pkg, "project-context.json"))
    product = find_json_block(read_text(_require(pkg, "PRODUCT.md")))
    design = find_json_block(read_text(_require(pkg, "design.md")))
    requirements = parse_requirements(read_text(_require(pkg, "requirements.md")))
    tasks = parse_tasks(read_text(_require(pkg, "tasks.md")))
    acceptance = parse_acceptance(read_text(_require(pkg, "acceptance.md")))
    verification_intent = load_json(_require(pkg, "verification-intent.json"))
    manifest = load_json(_require(pkg, MANIFEST_FILE))

    if not requirements:
        raise BuildError("requirements.md contains no REQ-* entries")
    if not tasks:
        raise BuildError("tasks.md contains no TASK-* entries")
    if not acceptance:
        raise BuildError("acceptance.md contains no AC-* entries")

    experiment = product["experiment"]
    contract = {
        "contract_version": spec_version(),
        "contract_id": experiment["contract_id"],
        "experiment_id": experiment["experiment_id"],
        "experiment_type": experiment["experiment_type"],
        "matched_control_available": experiment["matched_control_available"],
        "project": pc["project"],
        "mode": experiment["mode"],
        "feature": product["feature"],
        "artifact_refs": [
            {
                "role": entry["role"],
                "path": entry["path"],
                "required": entry["required"],
                "source": entry["source"],
            }
            for entry in manifest["entries"]
        ],
        "artifact_hashes": {entry["path"]: entry["sha256"] for entry in manifest["entries"]},
        "scope": product["scope"],
        "non_goals": product.get("non_goals", []),
        "decisions": design.get("decisions", []),
        "assumptions": design.get("assumptions", []),
        "read_first": pc["read_first"],
        "allowed_paths": pc["allowed_paths"],
        "forbidden_paths": pc.get("forbidden_paths", []),
        "requirements": requirements,
        "acceptance_ids": [item["id"] for item in acceptance],
        "data_change": design["data_change"],
        "ui_change": design["ui_change"],
        "selector_contract": design["selector_contract"],
        "tasks": tasks,
        "verification_intent": {key: verification_intent[key] for key in VI_KEYS if key in verification_intent},
        "stop_conditions": design["stop_conditions"],
        "unresolved_questions": product.get("unresolved_questions", []),
        "readiness": {"status": "NOT_READY", "gates": {}},
    }
    return contract


def _resolve_source_root(source_root: str | None, package_dir: str | None) -> str | None:
    if not source_root:
        return None
    if os.path.isabs(source_root):
        return os.path.abspath(source_root)
    if package_dir:
        return os.path.abspath(os.path.join(package_dir, source_root))
    return source_root


def _under_root(root: str | None, rel: str) -> str:
    if not root:
        return rel
    if os.path.isabs(rel):
        return os.path.abspath(rel)
    return os.path.abspath(os.path.join(root, rel))


def _abs_package(contract_package: str | None, package_dir: str | None) -> str | None:
    for candidate in (contract_package, package_dir):
        if isinstance(candidate, str) and candidate.strip() and os.path.isabs(candidate):
            return os.path.abspath(candidate)
    return None


def render_prompt(
    contract: dict,
    *,
    source_root: str | None = None,
    package_dir: str | None = None,
    contract_package: str | None = None,
    cli_cwd: str | None = None,
) -> str:
    tasks = contract["tasks"]
    task_lines = "\n".join(
        f"  {task['id']}  {task['goal']}  (depends: {', '.join(task['depends']) or 'none'})"
        for task in tasks
    )
    root = _resolve_source_root(source_root, package_dir)
    pkg = _abs_package(contract_package, package_dir)
    allowed = "\n".join(
        f"  - `{_under_root(root, path)}`" if root else f"  - {path}"
        for path in contract["allowed_paths"]
    )
    forbidden = (
        "\n".join(
            f"  - `{_under_root(root, path)}`" if root else f"  - {path}"
            for path in contract["forbidden_paths"]
        )
        or "  - (none declared)"
    )
    stops = "\n".join(f"  - {item}" for item in contract["stop_conditions"])
    if root:
        read_first = "\n".join(
            f"  {i + 1}. `{_under_root(root, item['path'])}`"
            f" (from source_root + `{item['path']}`)"
            for i, item in enumerate(contract["read_first"])
        )
        source_root_line = (
            f"- Frozen `source_root` absolute path: `{root}`.\n"
            "- Use the absolute `read_first` / allowed / forbidden paths listed below with "
            "`read_file` or shell. Do not reinterpret those absolute paths relative to cwd.\n"
        )
    else:
        read_first = "\n".join(
            f"  {i + 1}. {item['path']}" for i, item in enumerate(contract["read_first"])
        )
        source_root_line = (
            "- Resolve `read_first`, allowed paths and forbidden paths against `source_root` "
            "from that package's `project-context.json`, not against the current working directory.\n"
        )
    if isinstance(cli_cwd, str) and cli_cwd.strip() and os.path.isabs(cli_cwd):
        cwd_line = (
            f"- Frozen CLI cwd (absolute): `{os.path.abspath(cli_cwd)}`. "
            "Keep this cwd for declared CLI checks; do not `cd` around to discover it.\n"
        )
    else:
        cwd_line = (
            "- Keep the registered launch working directory for CLI checks unless the frozen "
            "command explicitly changes it. Frozen CLI paths like `src/...` are relative to "
            "that launch cwd.\n"
        )
    if pkg:
        package_lines = (
            f"- Frozen contract package (absolute): `{pkg}`.\n"
            "- Gate already validated this package; do NOT recompute manifest hashes, and do NOT "
            "run `find`/`ls`/`pwd`/`cd` to locate the package.\n"
            f"- Batch-read with `read_file` only these absolute members: "
            f"`{pkg}/READY.json`, `{pkg}/implementation-contract.json`, "
            f"`{pkg}/project-context.json`, `{pkg}/tasks.md`, `{pkg}/verification-intent.json`.\n"
            "- Skip requirements.md / acceptance.md / design.md / DESIGN.md / manifest.json "
            "unless a CONTRACT_GAP requires one named file.\n"
        )
        contract_ref = f"`{pkg}/implementation-contract.json`"
        ready_ref = f"`{pkg}/READY.json`"
    else:
        package_lines = (
            "- The launcher sets `HERMES_CONTRACT_PACKAGE` to the absolute read-only package. "
            "Resolve package members under that directory, never under cwd. If unset, emit "
            "`CONTRACT_GAP` and STOP; do not scan the repository.\n"
            "  Obtain that directory once using `printf '%s\\n' \"$HERMES_CONTRACT_PACKAGE\"`.\n"
            "- Then batch-read only: `\"$HERMES_CONTRACT_PACKAGE/READY.json\"`, "
            "`\"$HERMES_CONTRACT_PACKAGE/implementation-contract.json\"`, "
            "`\"$HERMES_CONTRACT_PACKAGE/project-context.json\"`, "
            "`\"$HERMES_CONTRACT_PACKAGE/tasks.md\"`, "
            "`\"$HERMES_CONTRACT_PACKAGE/verification-intent.json\"`.\n"
            "- Do not run `find`/`ls` to locate the contract package. Do not recompute "
            "manifest hashes; gate already validated them.\n"
        )
        contract_ref = "`$HERMES_CONTRACT_PACKAGE/implementation-contract.json`"
        ready_ref = "`$HERMES_CONTRACT_PACKAGE/READY.json`"
    intent = contract["verification_intent"]
    if intent.get("engine") == "cli":
        checks = "\n".join(
            "  - {step}: `{command}` — expected: {expected}; on failure: {on_failure}".format(
                step=check.get("step", "(missing step)"),
                command=check.get("command", "(missing command)"),
                expected=check.get("expected", "(missing expected result)"),
                on_failure=check.get("on_failure", "(missing failure condition)"),
            )
            for check in intent.get("cli_checks", [])
        ) or "  - (none declared; contract is invalid)"
        verify_steps = f"""1. Run every CLI check below exactly as declared, in order, ONLY AFTER the
   required allowed-path source/test files from section 3 already exist on disk.
2. Record evidence only in the files and format required by the frozen contract. Put expected results, failure conditions, and supplemental reporting in the FINAL ASSISTANT RESPONSE unless the contract explicitly requires them in an artifact.
3. A zero process exit alone is NOT a PASS; the expected result must be observed in the actual output.
4. If any check fails: STOP, report the failure, and do not synthesize or repair evidence.
5. On PASS: make NO further tool call, search, read, audit, repeated verification or exploratory check. Produce the Phase C report in the FINAL ASSISTANT RESPONSE using only evidence already collected in this session, emit the compact final task result, and STOP immediately.

CLI checks:
{checks}"""
    else:
        verify_steps = f"""1. Run the targeted tests named in `tasks.md` ONLY AFTER section-3 writes exist.
2. Build the Verification Plan (engine `{intent['engine']}`, journey `{intent['journey_id']}`).
3. Run the deterministic Verification Layer exactly once.
4. On PASS: make NO further tool call, search, read, audit, repeated verification or exploratory check. Produce the Phase C report in the FINAL ASSISTANT RESPONSE using only evidence already collected in this session, emit the compact final task result, and STOP immediately.
5. On FAIL: repair only the failed contract item and re-run only the work that repair invalidated. Do not repeat unaffected PASS work."""
    return f"""# EXECUTOR PROMPT — {contract['experiment_id']}

You are the execution agent for a FROZEN Implementation Contract. Work from the contract
and the listed `read_first` files. Do not re-do reconnaissance, re-choose architecture, or
re-plan decisions this contract has already frozen.

## Hard order (do not reorder)
1. Minimal package confirm (section 0) — at most a few `read_file` calls.
2. Read ONLY the listed `read_first` source files (section 2).
3. WRITE / patch the allowed task files immediately (section 3). The first mutating tool
   call after `read_first` must create or update an allowed source/test file.
4. Run CLI checks only after those writes exist (section 6).
5. Forbidden before the first write: `find`, recursive `ls`, `locate`, package discovery,
   hash recomputation, and reading extra markdown beyond section 0/2.

## Path bases
{package_lines}{source_root_line}{cwd_line}
## 0. Minimal package confirm
- Contract: {contract_ref} (contract_id `{contract['contract_id']}`, version `{contract['contract_version']}`)
- Confirm {ready_ref} reports `status == READY`. Do not recompute hashes.

## 1. Optional contract text (skip unless needed)
- Prefer the implementation-contract JSON + `tasks.md` already listed above.
- Open requirements/acceptance/design ONLY for a named CONTRACT_GAP.

## 2. Recon budget
- `broad repo scan = forbidden`.
- Read only these {len(contract['read_first'])} `read_first` files:
{read_first}
- Extend to a targeted search ONLY for `CONTRACT_GAP`, `CONTRACT_CONTRADICTION`, a missing
  dependency, or compile evidence that requires one extra file. Record `EXTRA_RECON_REASON`
  (file + why) for every extension.

## 3. Execute tasks in dependency order (WRITE NEXT)
{task_lines}

## 4. Boundaries
Allowed paths:
{allowed}
Forbidden paths:
{forbidden}
Frozen decisions (do not reopen): {', '.join(d['id'] for d in contract['decisions']) or '(none)'}.

## 5. If the contract is wrong
If a contract fact contradicts the source, a required file is missing, an assumption is
wrong, an acceptance is impossible, or a boundary is unsafe:
  STOP → emit `CONTRACT_DEVIATION` with evidence. Do NOT silently redesign.

## 6. Verify and hand off
{verify_steps}

After this session (POST-SESSION observers, not in-session steps):
- `on_session_finalize` / Auto-Finalizer are POST-SESSION observers.
- Do NOT invoke, inspect, wait for, or verify Auto-Finalizer from inside this Hermes session.
- Auto-Finalizer runs only AFTER this Hermes session exits and is NOT an in-session acceptance
  criterion.

## Stop conditions
{stops}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile an Android Implementation Contract")
    parser.add_argument("package")
    args = parser.parse_args(argv)

    pkg = os.path.abspath(args.package)
    if not os.path.isdir(pkg):
        print(f"ERROR: not a directory: {pkg}", file=sys.stderr)
        return 2

    try:
        contract = build(pkg)
    except (BuildError, KeyError, ValueError) as exc:
        print(f"BUILD_ERROR {exc}", file=sys.stderr)
        return 1

    write_json(os.path.join(pkg, CONTRACT_FILE), contract)
    prompt_path = os.path.join(pkg, PROMPT_FILE)
    tmp = prompt_path + ".tmp"
    pc = load_json(os.path.join(pkg, "project-context.json"))
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(
            render_prompt(
                contract,
                source_root=pc.get("source_root"),
                package_dir=pkg,
                contract_package=pc.get("contract_package"),
                cli_cwd=pc.get("cli_cwd"),
            )
        )
    os.replace(tmp, prompt_path)

    print(
        f"CONTRACT=WROTE id={contract['contract_id']} "
        f"requirements={len(contract['requirements'])} tasks={len(contract['tasks'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

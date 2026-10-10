# Filesystem Boundary Review — Round 2 Corrections

## Verdict on the first pass

The first-pass result remains `PARTIAL`. Do **not** execute its cleanup plan yet and do not claim that all future writes are external.

Verified good facts:

- the migration archive manifest verifies byte-for-byte;
- Hermes `HEAD` equals the locked commit and its working tree is clean;
- the XDG root model is directionally correct;
- no ChatGPT message or campaign transition was performed.

The following review findings must be fixed before cleanup can be approved.

## Blocking findings

### 1. The verifier misses known generated roots

`scripts/verify-layout.sh` does not reject all known output locations. At minimum add correctly scoped detection for:

- `orchestration/hermes/evidence` as a generated artifact root;
- `verification-benchmark/harness/.state`;
- `verification-benchmark/reports/hardening`;
- `reports/migration-recovery`;
- `reports/evidence`;
- the obsolete sibling output root `/home/zhong/Projects/_evaluation` in a Projects-root audit mode.

Do not reject a directory merely because its basename is `evidence`: for example, `verification/android/evidence/layout.sh` is authored source. Detection must be path-specific or classification-driven.

Add a `--projects-root` or equivalent mode that inventories immediate children of the Projects root and flags known output-only siblings. Include `/home/zhong/Projects/KeepLab-Relay-evidence` in the audit and classify it with evidence; do not remove it without a separately verified archive and approval.

### 2. The cleanup plan is non-canonical and incomplete

The first plan contains 647 entries, including both `verification-benchmark/results` and hundreds of children below it. This parent/child duplication is ambiguous and unsafe.

Generate a new plan with non-overlapping minimal roots. Each entry must contain:

- original absolute path;
- classification and reason;
- action;
- file count and byte count;
- external archive destination;
- manifest path and verification status;
- whether the path contains any executable/source-like files;
- exact restore instruction.

The first plan omitted the non-cache content under `orchestration/hermes/evidence`, even though 432 files were copied to the archive. It also omitted generated content under `reports` and `verification-benchmark/reports`. Correct these omissions.

Do not assume everything below `orchestration/hermes/evidence` is disposable. It contains source-like `.py`/`.sh` files. Compare them with canonical source locations. Preserve any unique project implementation as normal project source or a reviewed historical fixture; archive true run evidence externally.

### 3. Test execution still writes caches into the project

The first verification run created new `__pycache__` directories in the live tree. Therefore the statement “all new writes already use external XDG roots” is false.

Provide and use one checked-in test runner that sets, as applicable:

```text
PYTHONPYCACHEPREFIX=$STACK_CACHE_ROOT/python-pycache
PYTEST_ADDOPTS=-p no:cacheprovider
GRADLE_USER_HOME=$STACK_CACHE_ROOT/gradle-user-home
```

Configure probe Gradle build outputs outside the project, not merely its dependency cache. A clean test run must start from a layout-clean project copy, run every offline gate, and finish with the project copy still layout-clean.

Do not weaken the verifier or hide generated material only with `.gitignore`; the physical project tree must remain clean.

### 4. Executable writers still target old in-project evidence paths

Migrate or retire every remaining executable writer, including at minimum:

- `orchestration/hermes/evaluation_adapter/tests/run_guard_verification.sh`;
- `run_p0b_eval_guard_fix_verification.sh`;
- `run_p0b_eval_inspection_context_fix_verification.sh`;
- `run_p0b_eval_wrapper_role_fix_verification.sh`;
- associated compare scripts that read obsolete production paths;
- `evaluation/commandcode/phase_rules.json` and its tests, which currently model writes to `orchestration/hermes/evidence/**` as the live evidence destination.

Historical literal paths may remain only in explicitly identified immutable fixtures. Executable scripts must resolve current paths through the central contract, use temporary directories for tests, and never write to the project.

Remove the unsafe fallback in `verification/integration/autofinalizer/install.sh`:

```text
... || echo "$PROJECTS/_evaluation"
```

If the path contract cannot be resolved, fail closed or resolve the XDG default without using `/home/.../Projects`.

Update active documentation and examples that still instruct users to write to `/mnt/AndroidDev/Projects/_evaluation`. Clearly label any retained historical fixtures as non-executable data.

### 5. Archive and inventory reports are incomplete

The first archive contains `orchestration/hermes/evidence` and `verification-benchmark/reports/hardening`, but not the 19 files under `reports/migration-recovery`. Archive every generated path before proposing removal.

Fix `audit-inventory.json`: its `top_level.*.bytes` values are all zero and therefore do not provide a trustworthy top-level size inventory.

Report both:

- the number of minimal violating roots;
- total violating files and bytes.

Do not describe hundreds of files as merely “35 artifacts” without defining the counting unit.

### 6. Harden host-state export/import

Before calling the migration tools complete:

- reject an export destination inside the project tree;
- require a new or empty destination, preventing stale files from entering a manifest;
- reject symlinks and non-regular files in archives, or safely materialize and validate them under an explicit policy;
- prevent destination traversal through pre-existing symlinked parent directories during import;
- validate manifest digest syntax and reject duplicate paths;
- verify archive metadata/schema and the expected secret-export policy;
- test malicious archive entries, symlink attacks, duplicate entries, checksum failures, and non-empty destinations.

Never print or place actual secrets in the project or generated report.

### 7. Check Gradle portability requirements

Verify that every Gradle wrapper involved in the copied system uses the intended version, checksum verification, and a China-mainland-accessible first-download mirror with a documented official fallback. Do not silently change required Gradle versions. Record the actual wrapper URLs and SHA-256 values in the external report.

## Safe second-pass procedure

1. Preserve the first archive and reports unchanged as audit history.
2. Implement the corrections above without deleting or moving existing originals.
3. Create a new timestamped archive for every newly discovered generated root and verify it.
4. Generate a canonical, non-overlapping cleanup plan.
5. Build a clean source copy outside `/home/zhong/Projects` or in a temporary directory.
6. Run all offline tests through the new clean test runner.
7. Run layout verification both before and after tests; both must return zero violations.
8. Run the Projects-root audit; output-only sibling directories must be reported separately.
9. Do not execute cleanup until a human approves the corrected plan.

## Required result

Write all second-pass logs and generated reports outside the project at:

```text
$STACK_DATA_ROOT/artifacts/filesystem-hardening/<new-timestamp>/
```

End with:

```text
FILESYSTEM_BOUNDARY_REVIEW2_RESULT
verdict: PASS | PARTIAL | FAIL
project_violating_roots: <count>
project_violating_files: <count>
project_violating_bytes: <count>
projects_root_output_siblings: <count and names>
live_writers_remaining: <count>
clean_copy_before_tests: PASS | FAIL
clean_copy_after_tests: PASS | FAIL
cleanup_plan_non_overlapping: YES | NO
all_planned_roots_archived_and_verified: YES | NO
hermes_source_class: CLEAN_PINNED_RUNTIME | PROJECT_CHANGES_PRESERVED | UNRESOLVED
campaign_state_changed: NO
chatgpt_message_sent: NO
cleanup_performed: NO
external_report: <absolute path>
next_human_action: <one sentence>
```

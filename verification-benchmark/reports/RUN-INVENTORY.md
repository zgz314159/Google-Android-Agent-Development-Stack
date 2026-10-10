# RUN INVENTORY — P0 Verification Compression

Generated: 2026-10-03T13:50:50Z · audit over existing artifacts only (no re-run).

**Final frozen APK sha256:** `a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06`

## Counts

- Formal measured **B** runs: **11**
- Formal measured **C** runs: **13**
- Formal **A control** runs: **3**
- **Total normalized runs (measured B/C + control A): 27**
- Excluded (warmup / diagnostic / non-allowlisted): **9**

Discrepancy note: the prior session's terminal summary claimed *B = 15 runs* and *C = 13 runs* (B/C = 28). The artifacts show **B = 11 measured + 3 warm-up + 1 fail-test = 15 B-labelled directories**, and **C = 13 measured**. The formal measured B set is **11**, so the `15` figure conflated warm-up/diagnostic directories with measured runs; `24 measured B/C + 3 A = 27` is the artifact-backed total (matches Stage 1 and `normalized-benchmark.json`).

## Formal measured runs

| run_id | engine | journey | iter | outcome | class | warmup | debug/test | measured | excluded |
|---|---|---|---|---|---|---|---|---|---|
| `J1-B-1` | B | J1 | 1 | PASS | measured | no | no | yes | no |
| `J1-B-2` | B | J1 | 2 | PASS | measured | no | no | yes | no |
| `J1-B-3` | B | J1 | 3 | PASS | measured | no | no | yes | no |
| `J1-C-1` | C | J1 | 1 | PASS | measured | no | no | yes | no |
| `J1-C-2` | C | J1 | 2 | PASS | measured | no | no | yes | no |
| `J1-C-3` | C | J1 | 3 | PASS | measured | no | no | yes | no |
| `J1-C-4` | C | J1 | 4 | PASS | measured | no | no | yes | no |
| `J1-C-5` | C | J1 | 5 | PASS | measured | no | no | yes | no |
| `J2-B-1` | B | J2 | 1 | PASS | measured | no | no | yes | no |
| `J2-B-2` | B | J2 | 2 | PASS | measured | no | no | yes | no |
| `J2-B-3` | B | J2 | 3 | PASS | measured | no | no | yes | no |
| `J2-C-1` | C | J2 | 1 | PASS | measured | no | no | yes | no |
| `J2-C-2` | C | J2 | 2 | PASS | measured | no | no | yes | no |
| `J2-C-3` | C | J2 | 3 | PASS | measured | no | no | yes | no |
| `J3-B-1` | B | J3 | 1 | PASS | measured | no | no | yes | no |
| `J3-B-2` | B | J3 | 2 | PASS | measured | no | no | yes | no |
| `J3-B-3` | B | J3 | 3 | PASS | measured | no | no | yes | no |
| `J3-B-4` | B | J3 | 4 | PASS | measured | no | no | yes | no |
| `J3-B-5` | B | J3 | 5 | PASS | measured | no | no | yes | no |
| `J3-C-1` | C | J3 | 1 | PASS | measured | no | no | yes | no |
| `J3-C-2` | C | J3 | 2 | PASS | measured | no | no | yes | no |
| `J3-C-3` | C | J3 | 3 | PASS | measured | no | no | yes | no |
| `J3-C-4` | C | J3 | 4 | PASS | measured | no | no | yes | no |
| `J3-C-5` | C | J3 | 5 | PASS | measured | no | no | yes | no |

## Control runs (Engine A)

| run_id | engine | journey | iter | outcome | class | warmup | debug/test | measured | excluded |
|---|---|---|---|---|---|---|---|---|---|
| `A-J1` | A | J1 | 1 | PASS | control | no | no | control | no |
| `A-J2` | A | J2 | 1 | PASS | control | no | no | control | no |
| `A-J3` | A | J3 | 1 | PASS | control | no | no | control | no |

## Excluded runs / directories

| run_id | class | apk | reason |
|---|---|---|---|
| `CJ1-test` | diagnostic | n/a | Maestro J1 smoke spike; only maestro.xml retained |
| `FAILTEST-B` | diagnostic | n/a | intentional-failure bundle test (Engine B native) |
| `FAILTEST-C` | diagnostic | n/a | intentional-failure bundle test (Engine C Maestro) |
| `J1-B-WARMUP` | warmup | n/a | discarded warm-up; no benchmark-run.json emitted |
| `J1-C-WARMUP` | warmup | n/a | discarded warm-up; no benchmark-run.json emitted |
| `J2-B-WARMUP` | warmup | n/a | discarded warm-up; no benchmark-run.json emitted |
| `J2-C-WARMUP` | warmup | n/a | discarded warm-up; no benchmark-run.json emitted |
| `J3-B-WARMUP` | warmup | n/a | discarded warm-up; no benchmark-run.json emitted |
| `J3-C-WARMUP` | warmup | n/a | discarded warm-up; no benchmark-run.json emitted |

## Old / intermediate APK hashes (superseded, pre-Stage-1)

- `8e0eafd66c7b77ef02c01e156c4531308b57426d6f19a68afb1e802a5209274f` — first freeze (19,317,529 B, before `testTagsAsResourceId`/testTag selectors).
- `21884d9bd54941ee4ebfaa2dcf31d4d371b2c56156effb429d888d2c41525870` — earlier build (19,317,628 B) attempted with `ui-test-manifest`, discarded before the first freeze.
- **Final:** `a8858bd1f57b328a5042a120023508ced8e1cbbf68446bab3ce0e5e80f6fdf06` (19,358,670 B) — used by all recorded A/B/C measured runs.

## Artifact integrity

- All 27 artifact-bearing runs record `apk_sha256 == final`.
- Warm-up directories carry raw executor/logcat/seed artifacts but **no `benchmark-run.json`**, so they are structurally invisible to the aggregator.
- Diagnostic runs (`FAILTEST-B/C`, `CJ1-test`) are intentional-failure / smoke only.


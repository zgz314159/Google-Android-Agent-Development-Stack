#!/usr/bin/env bash
# Stage 1 screening orchestrator (hardened v1.0).
#
#   * fail-fast: the first failed run aborts the whole stage with a non-zero exit;
#   * engine isolation: ALL Engine B runs complete (then cleanup + a UiAutomation release
#     check) BEFORE any Engine C run starts — B and C never interleave;
#   * a preflight gate runs before any Journey.
#
# Environment:
#   N_ITERS=N   measured iterations per journey (default 3)
#   WARMUP=1    run one discarded warm-up per engine/journey first (default 0)
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HARNESS_DIR/lib.sh"

SERIAL=${SERIAL:-87296ada}; export SERIAL
N_ITERS="${N_ITERS:-3}"
WARMUP="${WARMUP:-0}"
JOURNEYS=(J1 J2 J3)

stage orchestration
with_timeout "$PREFLIGHT_TO" preflight bash "$HARNESS_DIR/preflight.sh" B

# ---- Engine B block ----
if [ "$WARMUP" = "1" ]; then
  for J in "${JOURNEYS[@]}"; do
    echo "warmup B $J"
    bash "$HARNESS_DIR/run_engine_b.sh" "$J" WARMUP >/dev/null 2>&1 || true
  done
fi

B_RUNS=0
for ((i = 1; i <= N_ITERS; i++)); do
  for J in "${JOURNEYS[@]}"; do
    echo "measured B $J #$i"
    bash "$HARNESS_DIR/run_engine_b.sh" "$J" "$i"
    B_RUNS=$((B_RUNS + 1))
  done
done

# engine boundary: cleanup B, then verify UiAutomation is released before C
stage engine_boundary
bash "$HARNESS_DIR/cleanup_engine.sh" B
bash "$HARNESS_DIR/cleanup_engine.sh" C --check-only

# ---- Engine C block ----
if [ "$WARMUP" = "1" ]; then
  for J in "${JOURNEYS[@]}"; do
    echo "warmup C $J"
    bash "$HARNESS_DIR/run_engine_c.sh" "$J" WARMUP >/dev/null 2>&1 || true
  done
fi

C_RUNS=0
for ((i = 1; i <= N_ITERS; i++)); do
  for J in "${JOURNEYS[@]}"; do
    echo "measured C $J #$i"
    bash "$HARNESS_DIR/run_engine_c.sh" "$J" "$i"
    C_RUNS=$((C_RUNS + 1))
  done
done

EXPECTED=$(( N_ITERS * ${#JOURNEYS[@]} ))
if [ "$B_RUNS" -ne "$EXPECTED" ] || [ "$C_RUNS" -ne "$EXPECTED" ]; then
  die "run count mismatch: B=$B_RUNS C=$C_RUNS expected=$EXPECTED each" orchestration
fi

echo "STAGE1_DONE B=$B_RUNS C=$C_RUNS"

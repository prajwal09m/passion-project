#!/bin/sh
# Sharded SIM-2 execution wrapper.
# Launches SIM2_SHARDS (default 8) independent worker processes, each
# computing its strided share of campaigns (c % S == k) with the same
# per-campaign seeds as a sequential run, then assembles the FWER tables
# with the --merge action.  Every worker writes its own log under
# results/.  If any worker dies, its partial checkpoint remains and
# re-running this wrapper resumes it; the merge aborts cleanly on
# incomplete coverage.
cd "$(dirname "$0")/.." || exit 1
S=${SIM2_SHARDS:-8}
LOGDIR=stat_validation_h10/results
echo "[wrapper] starting $S SIM-2 shards $(date -u +%FT%TZ)" > "$LOGDIR/sim2_parallel.log"
k=0
while [ "$k" -lt "$S" ]; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    py -3 -X utf8 stat_validation_h10/run_sim.py sim2 \
    --shards "$S" --shard-index "$k" > "$LOGDIR/sim2_shard${k}.log" 2>&1 &
  k=$((k + 1))
done
wait
echo "[wrapper] all shards exited; merging $(date -u +%FT%TZ)" >> "$LOGDIR/sim2_parallel.log"
py -3 -X utf8 stat_validation_h10/run_sim.py sim2 --merge --shards "$S" \
  >> "$LOGDIR/sim2_parallel.log" 2>&1
rc=$?
echo "[wrapper] done rc=$rc $(date -u +%FT%TZ)" >> "$LOGDIR/sim2_parallel.log"
exit $rc

#!/bin/sh
echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - init.sh started (PID $$)"
echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - sleeping 900s to simulate a hung/slow startup before app is launched"

SLEEP_SECONDS=900
i=0
while [ "$i" -lt "$SLEEP_SECONDS" ]; do
  sleep 60
  i=$((i + 60))
  echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - still sleeping, ${i}s elapsed of ${SLEEP_SECONDS}s"
done

echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - init.sh finished, handing off to app start"

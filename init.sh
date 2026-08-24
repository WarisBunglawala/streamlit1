#!/bin/bash
echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - init.sh started (PID $$)"
echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - sleeping 900s to simulate a hung/slow startup before app is launched"

SLEEP_SECONDS=900
for ((i=0; i<SLEEP_SECONDS; i+=60)); do
  sleep 60
  echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - still sleeping, ${i}s elapsed of ${SLEEP_SECONDS}s"
done

echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - init.sh finished, handing off to app start"

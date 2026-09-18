#!/bin/sh
echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - init.sh started"

# Nothing to do: this app needs no setup beyond requirements.txt, which the
# runner installs. Kept as a no-op so any deploy config still pointing at this
# script continues to work.

echo "[INIT] $(date -u +%Y-%m-%dT%H:%M:%SZ) - init.sh finished, handing off to app start"

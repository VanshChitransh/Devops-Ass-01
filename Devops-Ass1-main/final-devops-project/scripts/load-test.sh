#!/usr/bin/env bash
# Hammers the API to make the HPA and the dashboards move.
# usage: BASE_URL=http://tickethub.local ./scripts/load-test.sh <seconds> <parallel>
BASE="${BASE_URL:-http://localhost:8000}"; SECS="${1:-60}"; PAR="${2:-8}"
echo "[load] $PAR parallel clients for ${SECS}s against $BASE"
END=$((SECONDS + SECS))
worker(){ while [ $SECONDS -lt $END ]; do curl ${CURL_OPTS:-} -s -o /dev/null "$BASE/api/tickets"; curl ${CURL_OPTS:-} -s -o /dev/null "$BASE/api/tickets/stats"; done; }
for _ in $(seq 1 "$PAR"); do worker & done; wait
echo "[load] done"

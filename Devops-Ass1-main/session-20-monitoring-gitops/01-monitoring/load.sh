#!/usr/bin/env bash
# usage: ./load.sh <normal|errors|slow|cpu> <seconds>
# Sends traffic at the demo app so metrics, logs and alerts have something to show.
MODE="${1:-normal}"; SECONDS_TO_RUN="${2:-60}"; BASE="${BASE_URL:-http://localhost:8000}"
case "$MODE" in
  normal) PATHS=(/ /health / /health /);;
  errors) PATHS=(/error /error /error /);;
  slow)   PATHS=(/slow);;
  cpu)    PATHS=(/cpu);;
  *) echo "mode must be normal, errors, slow or cpu"; exit 1;;
esac
END=$((SECONDS + SECONDS_TO_RUN)); COUNT=0
echo "[load] mode=$MODE for ${SECONDS_TO_RUN}s against $BASE"
while [ $SECONDS -lt $END ]; do
  for p in "${PATHS[@]}"; do curl -s -o /dev/null "$BASE$p"; COUNT=$((COUNT+1)); done
  [ "$MODE" = normal ] && sleep 0.2
done
echo "[load] sent $COUNT requests"

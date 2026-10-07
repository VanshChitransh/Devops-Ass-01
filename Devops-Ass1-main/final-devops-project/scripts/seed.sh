#!/usr/bin/env bash
# Creates a handful of realistic tickets. usage: BASE_URL=http://localhost:8000 ./scripts/seed.sh
BASE="${BASE_URL:-http://localhost:8000}"
post(){ curl ${CURL_OPTS:-} -s -o /dev/null -w "created %{http_code}\n" -X POST "$BASE/api/tickets" -H "Content-Type: application/json" -d "$1"; }
post '{"title":"VPN drops every hour","description":"Since the laptop update","priority":"high","requester":"priya@example.com"}'
post '{"title":"Need access to the Grafana dashboard","priority":"medium","requester":"arjun@example.com","assignee":"vansh"}'
post '{"title":"Printer on floor 3 offline","priority":"low","requester":"facilities@example.com","status":"in_progress","assignee":"vansh"}'
post '{"title":"Payment page returns 500","description":"Checkout fails for all users","priority":"urgent","requester":"ops@example.com"}'
post '{"title":"Reset password for new intern","priority":"medium","requester":"hr@example.com","status":"resolved","assignee":"vansh"}'
curl ${CURL_OPTS:-} -s "$BASE/api/tickets/stats"; echo

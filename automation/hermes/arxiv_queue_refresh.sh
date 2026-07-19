#!/usr/bin/env bash
set -euo pipefail

readonly FEED_PATH="/tmp/arxiv-robotics-feed.xml"
readonly QUEUE_TOOL="/root/robot/scripts/arxiv_queue.py"
readonly STATE_PATH="/root/.hermes/state/arxiv-robotics-ledger.json"
readonly API_URL="https://export.arxiv.org/api/query?search_query=cat:cs.RO&sortBy=submittedDate&sortOrder=descending&max_results=30"

curl -fsS --retry 3 --retry-delay 2 --max-time 45 "${API_URL}" -o "${FEED_PATH}"
python3 "${QUEUE_TOOL}" --state "${STATE_PATH}" ingest --feed "${FEED_PATH}"
python3 "${QUEUE_TOOL}" --state "${STATE_PATH}" list --statuses unseen,failed --limit 12

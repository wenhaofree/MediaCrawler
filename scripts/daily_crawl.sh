#!/usr/bin/env bash
# Douyin daily / multi-slot crawl helper for VPS cron.
# Usage:
#   SLOT=morning ./scripts/daily_crawl.sh
#   SLOT=afternoon ./scripts/daily_crawl.sh
#   SLOT=evening ./scripts/daily_crawl.sh

set -euo pipefail

cd "$(dirname "$0")/.."

export PATH="${HOME}/.cargo/bin:${PATH:-}"
SLOT="${SLOT:-morning}"

# Customize creator IDs for your deployment
CREATOR_IDS="${CREATOR_IDS:-MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk}"

if ! curl -s http://127.0.0.1:8999/health > /dev/null; then
  echo "[$(date)] sign service not running, starting..."
  nohup node services/sign_srv/server.js > /tmp/sign_srv.log 2>&1 &
  sleep 2
fi

echo "[$(date)] start douyin crawl slot=${SLOT}"

uv run main.py \
  --platform dy \
  --type creator \
  --max_pages 3 \
  --pure_api true \
  --save_data_option postgres \
  --scheduled_slot "${SLOT}" \
  --creator_id "${CREATOR_IDS}"

echo "[$(date)] finished douyin crawl slot=${SLOT}"

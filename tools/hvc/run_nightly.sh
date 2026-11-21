#!/usr/bin/env bash
# Nightly HVC chart book: newest game plan + standing list -> Massive -> DAS Market Viewer
# lists, local HTML book, and a private Notion page under HVC_NOTION_PARENT.
# Run by systemd/hvc-nightly.timer at 20:15 ET, Mon-Fri.
# No --draw-window / --alerts: those need a live DAS session; run them by hand.
set -euo pipefail
cd "$(dirname "$0")/../.."
exec /usr/bin/python3 tools/hvc/hvc_daily.py \
    --gameplan \
    --symbols tools/hvc/watchlist.local.txt \
    --chartbook \
    --notion

#!/usr/bin/env bash
# fetch_flatfiles.sh START END "TICKERS..." [PARALLEL]
# Download Massive.com (Polygon) us_stocks_sip minute flat files for a date range and
# extract one CSV per ticker per day under ~/market_data/{T}/{T}_{date}_minute.csv
# (the market-data skill's layout). Skips days already extracted. Weekend dates are
# skipped; holidays fail the S3 copy and are logged, not fatal.
#
# Credentials: MASSIVE_S3_ACCESS_KEY / MASSIVE_S3_SECRET_KEY (or MASSIVE_ACCESS_KEY /
# MASSIVE_SECRET_ACCESS_KEY) from the environment or ~/.claude/.env. Never printed.
set -u
START=$1; END=$2; TICKERS=$3; PAR=${4:-4}
DATA="${MARKET_DATA_DIR:-$HOME/market_data}"
TMP="${TMPDIR:-/tmp}/massive_flatfiles"; mkdir -p "$TMP"
LOG="$DATA/fetch_flatfiles.log"

envval() { grep -E "^(export )?$1=" ~/.claude/.env 2>/dev/null | head -1 | cut -d= -f2- | sed 's/ #.*//' | tr -d '"'"'"; }
AK="${MASSIVE_S3_ACCESS_KEY:-${MASSIVE_ACCESS_KEY:-$(envval MASSIVE_S3_ACCESS_KEY)}}"
[ -z "$AK" ] && AK=$(envval MASSIVE_ACCESS_KEY)
SK="${MASSIVE_S3_SECRET_KEY:-${MASSIVE_SECRET_ACCESS_KEY:-$(envval MASSIVE_S3_SECRET_KEY)}}"
[ -z "$SK" ] && SK=$(envval MASSIVE_SECRET_ACCESS_KEY)
export AWS_ACCESS_KEY_ID="$AK" AWS_SECRET_ACCESS_KEY="$SK"
ENDPOINT="${MASSIVE_S3_ENDPOINT:-https://files.massive.com}"
RE=$(echo "$TICKERS" | tr ' ' '|')
for TK in $TICKERS; do mkdir -p "$DATA/$TK"; done

one_day() {
  local DATE=$1 Y=${1:0:4} M=${1:5:2}
  local probe="$DATA/${TICKERS%% *}/${TICKERS%% *}_${DATE}_minute.csv"
  if [ -s "$probe" ] && [ "$(wc -l < "$probe")" -gt 1 ]; then echo "$DATE cached"; return 0; fi
  local gz="$TMP/$DATE.csv.gz" sel="$TMP/$DATE.sel"
  if ! aws s3 cp "s3://flatfiles/us_stocks_sip/minute_aggs_v1/$Y/$M/$DATE.csv.gz" "$gz" \
        --endpoint-url "$ENDPOINT" --only-show-errors 2>>"$LOG"; then
    echo "$DATE no file (holiday?)"; rm -f "$gz"; return 0
  fi
  local HDR; HDR=$(zcat "$gz" | head -1)
  zcat "$gz" | grep -E "^($RE)," > "$sel"
  for TK in $TICKERS; do
    { echo "$HDR"; grep "^$TK," "$sel"; } > "$DATA/$TK/${TK}_${DATE}_minute.csv"
  done
  echo "$DATE $(wc -l < "$sel") rows"
  rm -f "$gz" "$sel"
}
export -f one_day; export DATA TMP LOG TICKERS RE ENDPOINT AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

python3 - "$START" "$END" <<'EOF' | xargs -P "$PAR" -I{} bash -c 'one_day {}' | tee -a "$LOG"
import sys
from datetime import date, timedelta
d, end = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
while d <= end:
    if d.weekday() < 5:
        print(d.isoformat())
    d += timedelta(days=1)
EOF
echo "DONE $START..$END" | tee -a "$LOG"

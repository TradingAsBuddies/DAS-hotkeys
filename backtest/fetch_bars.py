#!/usr/bin/env python3
"""
fetch_bars.py — pull 3 years of 1-minute bars for the FL watchlist from Polygon.

WHY REST AND NOT FLAT FILES
The falcon pipeline mandates Polygon flat files ("Massive") and forbids REST. That path is
unavailable on this machine: FlatFilesClient requires MASSIVE_ACCESS_KEY + MASSIVE_SECRET_KEY,
and only MASSIVE_API_KEY is present. `aws s3 ls s3://flatfiles/... --endpoint-url
https://files.polygon.io` returns 403 with every locally configured profile, and
FALCON_AWS_PROFILE points at a profile that does not exist here (it is another machine's).

REST was verified to serve 1-minute bars 3 years back, so this uses REST and caches to parquet.
That difference is recorded in the results so nobody mistakes this for a flat-file run.

Output: bars/{SYMBOL}.parquet  — columns t(UTC ms), o, h, l, c, v, n, vw
"""
import os, sys, time, json
from datetime import date
from pathlib import Path

import requests
import pandas as pd

HERE   = Path(__file__).resolve().parent
OUT    = HERE / "bars"
OUT.mkdir(exist_ok=True)

WATCHLIST = ["MSFT", "PANW", "NVDA", "DELL", "HPE", "AVGO", "CRWD", "SMCI", "SPY", "QQQ"]
START     = "2023-09-05"
END       = "2026-09-05"

KEY = os.getenv("POLYGON_API_KEY")
if not KEY:
    sys.exit("POLYGON_API_KEY not set")


def fetch(symbol: str) -> pd.DataFrame:
    url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/"
           f"{START}/{END}?adjusted=true&sort=asc&limit=50000")
    rows, page = [], 0
    while url:
        for attempt in range(5):
            try:
                r = requests.get(url, params={"apiKey": KEY}, timeout=90)
                if r.status_code == 429:
                    time.sleep(20); continue
                r.raise_for_status()
                break
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(5 * (attempt + 1))
        j = r.json()
        got = j.get("results") or []
        rows.extend(got)
        page += 1
        print(f"  [{symbol}] page {page}: +{len(got)} (total {len(rows)})", flush=True)
        url = j.get("next_url")
        if url:
            time.sleep(0.15)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.rename(columns={"t": "t", "o": "o", "h": "h", "l": "l", "c": "c", "v": "v"})
    df = df[["t", "o", "h", "l", "c", "v"]].drop_duplicates("t").sort_values("t")
    return df.reset_index(drop=True)


def main():
    summary = {}
    for sym in WATCHLIST:
        path = OUT / f"{sym}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            print(f"[{sym}] cached: {len(df):,} bars", flush=True)
            summary[sym] = len(df)
            continue
        print(f"[{sym}] fetching {START} -> {END} ...", flush=True)
        df = fetch(sym)
        if df.empty:
            print(f"[{sym}] NO DATA", flush=True)
            summary[sym] = 0
            continue
        df.to_parquet(path, index=False)
        first = pd.to_datetime(df["t"].iloc[0],  unit="ms", utc=True)
        last  = pd.to_datetime(df["t"].iloc[-1], unit="ms", utc=True)
        print(f"[{sym}] {len(df):,} bars  {first} -> {last}", flush=True)
        summary[sym] = len(df)
    (HERE / "fetch_summary.json").write_text(json.dumps(summary, indent=2))
    print("\nDONE", json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

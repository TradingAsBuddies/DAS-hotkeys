"""Daily bars from Massive (Polygon) REST, cached to backtest/bars/daily/ (gitignored:
licensed data, never commit it). Standard library only.

Errors raise MassiveError. An empty result is a real "no bars", never a failure
in disguise.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "backtest" / "bars" / "daily"
API = "https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/day/{start}/{end}"

# Polygon daily aggregates keep accumulating extended-hours prints until 20:00 ET,
# so the current day's bar is not final before then.
CONFIRM_AFTER_ET = (20, 0)


class MassiveError(RuntimeError):
    """Massive/Polygon request failed. Distinct from 'no bars'."""


def api_key(env: dict[str, str] | None = None) -> str:
    env = env or {}
    for k in ("POLYGON_API_KEY", "MASSIVE_API_KEY"):
        v = os.environ.get(k) or env.get(k)
        if v:
            return v
    raise MassiveError("POLYGON_API_KEY / MASSIVE_API_KEY not set (env or ~/.claude/.env)")


def _get(url: str, key: str, tries: int = 5) -> dict:
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}apiKey={urllib.parse.quote(key)}"
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(full, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < tries - 1:
                time.sleep(15)
                continue
            raise MassiveError(f"HTTP {exc.code} from Massive for {url}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise MassiveError(f"Massive unreachable for {url}: {exc}") from None
    raise MassiveError(f"Massive retries exhausted for {url}")


def _to_bar(row: dict, now_et: datetime) -> dict:
    d = datetime.fromtimestamp(row["t"] / 1000, tz=ET).date()
    final = d < now_et.date() or (now_et.hour, now_et.minute) >= CONFIRM_AFTER_ET
    return {"date": d.isoformat(), "o": row["o"], "h": row["h"], "l": row["l"],
            "c": row["c"], "v": row.get("v"), "confirmed": final}


def fetch_daily(symbol: str, years: int = 20, *, env: dict[str, str] | None = None,
                now: datetime | None = None) -> list[dict]:
    """Oldest-first daily bars. Today's unfinished bar is kept with confirmed=False
    (events wait for close; touches of older rays stay live, as in the Pine)."""
    now_et = (now or datetime.now(tz=ET)).astimezone(ET)
    start = (now_et.date() - timedelta(days=365 * years + years // 4)).isoformat()
    url = API.format(sym=urllib.parse.quote(symbol.upper()), start=start,
                     end=now_et.date().isoformat()) + "?adjusted=true&sort=asc&limit=50000"
    key = api_key(env)
    rows: list[dict] = []
    while url:
        j = _get(url, key)
        if j.get("status") not in ("OK", "DELAYED"):
            raise MassiveError(f"{symbol}: Massive status {j.get('status')!r}: {j.get('error') or j.get('message')}")
        rows.extend(j.get("results") or [])
        url = j.get("next_url")
    bars = [_to_bar(r, now_et) for r in rows]
    save_cache(symbol, bars)
    return bars


def save_cache(symbol: str, bars: list[dict]) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{symbol.upper()}.json"
    p.write_text(json.dumps(bars))
    return p


def load_cache(symbol: str) -> list[dict]:
    p = CACHE / f"{symbol.upper()}.json"
    if not p.exists():
        raise MassiveError(f"{symbol}: no cached bars at {p}; run without --offline first")
    return json.loads(p.read_text())


def trim_years(bars: list[dict], years: int | None, today: date | None = None) -> list[dict]:
    """Limit history (e.g. to approximate TradingView's loaded-history HVE)."""
    if not years:
        return bars
    cutoff = ((today or date.today()) - timedelta(days=365 * years)).isoformat()
    return [b for b in bars if b["date"] >= cutoff]

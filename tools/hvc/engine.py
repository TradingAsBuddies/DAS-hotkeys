"""HVC/HVE detection and close-anchored event rays — a port of Major Hayden's
TradingView indicator `hvc_watcher.pine` (Apache-2.0; see NOTICE).

Pure: bars in, per-bar series and retained rays out. No I/O, standard library only.

Semantics mirrored from the Pine source, bar by bar:

* Volume SMA includes the current bar and uses the last `sma_length` *valid*
  (non-missing) samples, like Pine's `ta.sma`; it is None until warmed up.
* HVC: volume > 0, SMA > 0, and volume >= SMA * multiplier (inclusive).
* HVE: volume > 0 and volume strictly greater than every earlier volume.
  The running record updates on every bar, confirmed or not.
* Events (HVC/HVE) only count on confirmed bars.
* Ray touch: before this bar's ray is added, any retained ray from an earlier
  bar with low <= level <= high is touched. Then a confirmed event evicts the
  oldest ray at capacity and appends one ray at its close (HVE kind wins).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

DEFAULT_SMA_LENGTH = 20
DEFAULT_MULT_DAILY = 3.0     # intraday, daily, multi-day
DEFAULT_MULT_WEEKLY = 2.0    # weekly, multi-week
DEFAULT_MULT_MONTHLY = 2.0   # monthly, quarterly, yearly
DEFAULT_RAY_LIMIT = 5


@dataclass(frozen=True)
class Ray:
    bar: int          # index of the event bar
    level: float      # event bar's close
    kind: str         # "HVE" or "HVC"
    date: str | None = None


@dataclass
class Result:
    sma: list[float | None] = field(default_factory=list)
    multiplier: list[float | None] = field(default_factory=list)
    hve_threshold: list[float] = field(default_factory=list)
    hvc: list[bool] = field(default_factory=list)
    hve: list[bool] = field(default_factory=list)
    touched: list[bool] = field(default_factory=list)
    ray_count: list[int] = field(default_factory=list)
    rays: list[Ray] = field(default_factory=list)       # retained after the last bar
    all_rays: list[Ray] = field(default_factory=list)   # every ray ever created

    @property
    def last(self) -> int:
        return len(self.hvc) - 1


def multiplier_for(timeframe: str, daily: float = DEFAULT_MULT_DAILY,
                   weekly: float = DEFAULT_MULT_WEEKLY,
                   monthly: float = DEFAULT_MULT_MONTHLY) -> float:
    """Pick the multiplier the way Pine's timeframe.ismonthly/isweekly does.
    Accepts TradingView strings: '1', '60', 'D', '2D', 'W', '2W', 'M', '3M', '12M'."""
    tf = timeframe.strip().upper()
    if tf.endswith("M") and not tf.endswith("MIN"):
        return monthly
    if tf.endswith("W"):
        return weekly
    return daily


def _num(v) -> float | None:
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else v


def compute(bars: list[dict], *, sma_length: int = DEFAULT_SMA_LENGTH,
            mult: float = DEFAULT_MULT_DAILY,
            ray_limit: int = DEFAULT_RAY_LIMIT, hve_min_bars: int = 0) -> Result:
    """bars: oldest first, dicts with h, l, c, v and optional `confirmed` (default
    True) and `date`. Missing volume may be None or NaN.

    hve_min_bars: suppress HVE on the first N bars (the record still accumulates).
    0 = Pine parity, where the first bars of a short history are trivially records."""
    if sma_length < 1:
        raise ValueError("sma_length must be >= 1")
    if mult < 1.0:
        raise ValueError("mult must be >= 1.0")
    if not 1 <= ray_limit <= 200:
        raise ValueError("ray_limit must be between 1 and 200")

    r = Result()
    window: list[float] = []      # last sma_length valid volumes
    record = 0.0                  # hve_threshold: max volume of all earlier bars
    prev_vol: float | None = None

    for i, b in enumerate(bars):
        vol = _num(b.get("v"))
        hi, lo, close = float(b["h"]), float(b["l"]), float(b["c"])
        confirmed = b.get("confirmed", True)

        if vol is not None:
            window.append(vol)
            if len(window) > sma_length:
                window.pop(0)
        sma = sum(window) / sma_length if len(window) == sma_length else None
        r.sma.append(sma)

        mult_val = vol / sma if vol is not None and sma is not None and sma > 0 else None
        r.multiplier.append(mult_val)

        record = max(record, prev_vol or 0.0)          # math.max(hve, nz(volume[1]))
        r.hve_threshold.append(record)
        prev_vol = vol

        hve_raw = vol is not None and vol > record and vol > 0 and i >= hve_min_bars
        hvc_raw = (vol is not None and vol > 0 and sma is not None and sma > 0
                   and vol >= sma * mult)
        is_hve = hve_raw and confirmed
        is_hvc = hvc_raw and confirmed
        r.hve.append(is_hve)
        r.hvc.append(is_hvc)

        touched = any(i > ray.bar and lo <= ray.level <= hi for ray in r.rays)
        r.touched.append(touched)

        if is_hve or is_hvc:
            if len(r.rays) >= ray_limit:
                r.rays.pop(0)
            ray = Ray(bar=i, level=close, kind="HVE" if is_hve else "HVC", date=b.get("date"))
            r.rays.append(ray)
            r.all_rays.append(ray)
        r.ray_count.append(len(r.rays))

    return r

#!/usr/bin/env python3
"""
backtest_fl.py — replay the Fashionably Late signal over 3 years of 1-minute bars.

Runs the SAME logic as fl_trading_agent._tick(), with the reference line switchable, so the
2026-09-05 change (VWAP -> 34-SMA) can be measured rather than assumed.

  --ref sma34   the new definition
  --ref vwap    the old definition
  --ref both    run both and print them side by side

FIDELITY — read before believing any number here
  1. The live agent updates consec_above/below, conf_carry and prev_gap on 45-SECOND BAR
     REFRESH events, not per bar. This replays one refresh per 1-minute bar. That is the
     closest honest mapping, but it is NOT identical: live gets ~1.3 refreshes per bar, so
     SUSTAINED_BARS=3 is reached sooner in production than here.
  2. Entry fills at the NEXT bar's open plus slippage. The live agent sends a marketable limit
     at last +/- 0.15 and may not fill, may partial, or may fill better.
  3. Stops are checked against bar high/low. Live checks every $Quote tick, so live exits are
     triggered by prints this never sees. Intrabar path is unknown: when a bar's range spans
     both the stop and a favourable extreme, this assumes STOP FIRST (pessimistic).
  4. No commission. Slippage is a flat per-share constant, applied on entry and exit.
  5. Extended-hours bars are included, matching the live 08:00 UTC session start.
"""
import os, sys, json, argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

HERE = Path(__file__).resolve().parent
BARS = HERE / "bars"

# ── Constants mirrored from ~/falcon/dashboard/fl_shared.py ───────────────────
ATR_PERIOD        = 14
SMA_PERIOD        = 34
ATR_MULT          = 2.0
ATR_MULT_STEP     = 0.25
ATR_MULT_FLOOR    = 0.25
VOL_MULT          = 1.5
ATR_CONF_MULT     = 1.5
CONF_CARRY_BARS   = 2
SUSTAINED_BARS    = 3
CANDLE_STOP_EVERY = 3
MAX_RT_PER_TICKER = 2
MAX_BARS          = 200   # matches fl_shared.MAX_BARS — VWAP/EMA see a rolling 200-bar window
BANNED_TICKERS    = {"MU", "CRCL", "UGRO"}
MIN_ENTRY_UTC     = (13, 45)
MAX_EXIT_UTC      = (23, 45)
REGULAR_CLOSE_UTC_H = 20

SLIPPAGE = 0.01   # $/share each side
MIN_RISK = 0.02   # reject signals whose ATR stop is under 2c wide.
                  # Without this, a run of 14 flat premarket bars gives ATR~0, the stop
                  # rounds to the entry price, risk collapses to fractions of a cent, and
                  # R = move/risk explodes to 1e12. Mirrors live invariant I-1 (no entry
                  # without a positive ATR) with a floor that is actually tradeable.


def ema9(closes):
    if len(closes) < 9:
        return None
    k = 2 / 10
    e = sum(closes[:9]) / 9
    for c in closes[9:]:
        e = c * k + e * (1 - k)
    return e

def sma34(closes, period=SMA_PERIOD):
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

def vwap_calc(bars):
    cumtpv = cumv = 0.0
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3
        cumtpv += tp * b["v"]; cumv += b["v"]
    return cumtpv / cumv if cumv else None

def atr_calc(bars, period=ATR_PERIOD):
    w = bars[-period:] if len(bars) >= period else bars
    return sum(b["h"] - b["l"] for b in w) / len(w) if w else None

def avg_vol(bars, period=20):
    w = bars[-period:] if len(bars) >= period else bars
    return sum(b["v"] for b in w) / len(w) if w else None


def run_symbol(sym: str, df: pd.DataFrame, ref_mode: str) -> list:
    """Replay one symbol. Returns a list of closed trades.

    Indicators are computed with O(1) rolling sums over the same windows the live agent
    uses (capped at MAX_BARS). The 9-EMA is carried incrementally across the session
    rather than reseeded on each sliding window; with k=0.2 the seed's contribution after
    ~190 bars is ~1e-19, so the two are numerically identical in float64.
    """
    import numpy as np
    dt = pd.to_datetime(df["t"], unit="ms", utc=True)
    days  = dt.dt.date.values
    hh_a  = dt.dt.hour.values.astype(np.int16)
    mm_a  = dt.dt.minute.values.astype(np.int16)
    o = df["o"].to_numpy(float); h = df["h"].to_numpy(float)
    l = df["l"].to_numpy(float); c = df["c"].to_numpy(float)
    v = df["v"].to_numpy(float); t_ms = df["t"].to_numpy()

    trades = []
    rejected = {}
    # day boundaries
    change = np.flatnonzero(days[1:] != days[:-1]) + 1
    starts = np.concatenate(([0], change))
    ends   = np.concatenate((change, [len(days)]))

    for s0, s1 in zip(starts, ends):
        n = s1 - s0
        if n < SMA_PERIOD + 2:
            continue
        O, H, L, C, V = o[s0:s1], h[s0:s1], l[s0:s1], c[s0:s1], v[s0:s1]
        HH, MM, TT = hh_a[s0:s1], mm_a[s0:s1], t_ms[s0:s1]
        day = days[s0]
        rng = H - L
        tp  = (H + L + C) / 3.0

        # prefix sums for O(1) windows
        cs_c   = np.concatenate(([0.0], np.cumsum(C)))
        cs_rng = np.concatenate(([0.0], np.cumsum(rng)))
        cs_v   = np.concatenate(([0.0], np.cumsum(V)))
        cs_tpv = np.concatenate(([0.0], np.cumsum(tp * V)))

        def wmean(cs, i, k):
            a = max(0, i - k + 1)
            return (cs[i + 1] - cs[a]) / (i + 1 - a)

        # incremental 9-EMA
        ema = None
        k_ema = 2 / 10

        prev_ema = prev_ref = prev_gap = None
        consec_above = consec_below = conf_carry = 0
        seen_cross = False
        in_pos = None
        round_trips = 0

        for i in range(n):
            if i == 8:
                ema = float(C[:9].mean())
            elif i > 8:
                ema = C[i] * k_ema + ema * (1 - k_ema)

            hh, mm = int(HH[i]), int(MM[i])
            after_gate = (hh > MIN_ENTRY_UTC[0]) or (hh == MIN_ENTRY_UTC[0] and mm >= MIN_ENTRY_UTC[1])
            past_exit  = (hh > MAX_EXIT_UTC[0]) or (hh == MAX_EXIT_UTC[0] and mm >= MAX_EXIT_UTC[1])

            if in_pos:
                side = in_pos["side"]
                hit = None
                if side == "LONG" and L[i] <= in_pos["stop"]:
                    hit = in_pos["stop"]
                elif side == "SHORT" and H[i] >= in_pos["stop"]:
                    hit = in_pos["stop"]

                if hit is not None:
                    px = hit - SLIPPAGE if side == "LONG" else hit + SLIPPAGE
                    trades.append(close_trade(in_pos, px, day, "STOP"))
                    in_pos = None; round_trips += 1
                elif past_exit:
                    px = C[i] - SLIPPAGE if side == "LONG" else C[i] + SLIPPAGE
                    trades.append(close_trade(in_pos, px, day, "EOD"))
                    in_pos = None; round_trips += 1
                else:
                    in_pos["candles"] += 1
                    cur_atr_t = wmean(cs_rng, i, ATR_PERIOD)
                    if (in_pos["candles"] - in_pos["last_stop_candle"] >= CANDLE_STOP_EVERY
                            and cur_atr_t > 0 and hh < REGULAR_CLOSE_UTC_H):
                        pnl = (C[i] - in_pos["entry"]) if side == "LONG" else (in_pos["entry"] - C[i])
                        if pnl > 0:
                            nm = max(ATR_MULT_FLOOR, in_pos["mult"] - ATR_MULT_STEP)
                            ns = round(C[i] - nm * cur_atr_t, 2) if side == "LONG" \
                                 else round(C[i] + nm * cur_atr_t, 2)
                            if (side == "LONG" and ns > in_pos["stop"]) or \
                               (side == "SHORT" and ns < in_pos["stop"]):
                                in_pos["stop"] = ns; in_pos["mult"] = nm
                        in_pos["last_stop_candle"] = in_pos["candles"]
                    continue

            if i + 1 < SMA_PERIOD or ema is None:
                continue

            cur_ema = ema
            if ref_mode == "sma34":
                cur_ref = wmean(cs_c, i, SMA_PERIOD)
            else:
                a = max(0, i - MAX_BARS + 1)
                vv = cs_v[i + 1] - cs_v[a]
                if vv <= 0:
                    continue
                cur_ref = (cs_tpv[i + 1] - cs_tpv[a]) / vv
            cur_atr = wmean(cs_rng, i, ATR_PERIOD)
            cur_avv = wmean(cs_v, i, 20)
            if not (cur_ema and cur_ref and cur_atr > 0 and cur_avv > 0):
                continue

            gap = cur_ema - cur_ref
            cross_up   = prev_ema is not None and prev_ema <= (prev_ref if prev_ref is not None else cur_ref) and cur_ema > cur_ref
            cross_down = prev_ema is not None and prev_ema >= (prev_ref if prev_ref is not None else cur_ref) and cur_ema < cur_ref
            if cross_up or cross_down:
                seen_cross = True

            avg_atr   = wmean(cs_rng, i, 20)
            vol_spike = V[i] > cur_avv * VOL_MULT
            atr_spike = rng[i] > avg_atr * ATR_CONF_MULT
            if vol_spike or atr_spike:
                conf_carry = CONF_CARRY_BARS
            elif conf_carry > 0:
                conf_carry -= 1
            confirmed = vol_spike or atr_spike or conf_carry > 0

            if cur_ema > cur_ref:
                consec_above += 1; consec_below = 0
            else:
                consec_below += 1; consec_above = 0

            if not seen_cross and (consec_above >= SUSTAINED_BARS or consec_below >= SUSTAINED_BARS):
                seen_cross = True

            exp_long  = prev_gap is not None and gap > prev_gap and cur_ema > cur_ref
            exp_short = prev_gap is not None and gap < prev_gap and cur_ema < cur_ref
            sustained_long  = seen_cross and consec_above >= SUSTAINED_BARS and exp_long
            sustained_short = seen_cross and consec_below >= SUSTAINED_BARS and exp_short

            sig_long  = ((cross_up   and confirmed) or sustained_long)  and after_gate
            sig_short = ((cross_down and confirmed) or sustained_short) and after_gate
            trig = "cross" if ((cross_up or cross_down) and confirmed) else "sustained"

            prev_ema, prev_ref, prev_gap = cur_ema, cur_ref, gap

            if (sig_long or sig_short) and not in_pos and not past_exit \
               and round_trips < MAX_RT_PER_TICKER and sym not in BANNED_TICKERS \
               and i + 1 < n:
                side  = "LONG" if sig_long else "SHORT"
                entry = O[i + 1] + SLIPPAGE if side == "LONG" else O[i + 1] - SLIPPAGE
                stop  = round(entry - ATR_MULT * cur_atr, 2) if side == "LONG" \
                        else round(entry + ATR_MULT * cur_atr, 2)
                risk  = abs(entry - stop)
                if risk < MIN_RISK:
                    rejected["tiny_risk"] = rejected.get("tiny_risk", 0) + 1
                    continue
                in_pos = {"sym": sym, "side": side, "entry": float(entry), "stop": float(stop),
                          "risk": float(risk), "mult": ATR_MULT, "candles": 0,
                          "last_stop_candle": 0, "trigger": trig,
                          "entry_t": int(TT[i + 1]), "atr": float(cur_atr)}

        if in_pos:
            px = C[-1] - SLIPPAGE if in_pos["side"] == "LONG" else C[-1] + SLIPPAGE
            trades.append(close_trade(in_pos, px, day, "EOD"))

    if rejected:
        print(f"   [{sym}/{ref_mode}] rejected: {rejected}", flush=True)
    return trades


def close_trade(p, exit_px, day, reason):
    move = (exit_px - p["entry"]) if p["side"] == "LONG" else (p["entry"] - exit_px)
    return {"symbol": p["sym"], "day": str(day), "side": p["side"],
            "entry": round(p["entry"], 4), "exit": round(exit_px, 4),
            "stop": p["stop"], "risk": round(p["risk"], 4),
            "R": round(move / p["risk"], 4), "reason": reason,
            "trigger": p["trigger"], "atr": round(p["atr"], 4)}


def summarize(trades, label):
    if not trades:
        return {"ref": label, "n_trades": 0}
    R = pd.Series([t["R"] for t in trades])
    wins = R[R > 0]
    return {
        "ref": label,
        "n_trades": int(len(R)),
        "win_rate": round(float((R > 0).mean()) * 100, 2),
        "mean_R": round(float(R.mean()), 4),
        "median_R": round(float(R.median()), 4),
        "total_R": round(float(R.sum()), 2),
        "expectancy_R": round(float(R.mean()), 4),
        "best_R": round(float(R.max()), 2),
        "worst_R": round(float(R.min()), 2),
        "pct_stopped": round(float(sum(1 for t in trades if t["reason"] == "STOP")) / len(trades) * 100, 2),
        "avg_win_R": round(float(wins.mean()), 4) if len(wins) else 0.0,
        "avg_loss_R": round(float(R[R <= 0].mean()), 4) if (R <= 0).any() else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", choices=["sma34", "vwap", "both"], default="both")
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    outdir = Path(a.out); outdir.mkdir(exist_ok=True)

    files = sorted(BARS.glob("*.parquet"))
    if not files:
        sys.exit("no bars — run fetch_bars.py first")

    modes = ["sma34", "vwap"] if a.ref == "both" else [a.ref]
    allsum, per_sym = [], []

    for mode in modes:
        trades = []
        for f in files:
            sym = f.stem
            df = pd.read_parquet(f)
            t = run_symbol(sym, df, mode)
            trades.extend(t)
            per_sym.append({**summarize(t, mode), "symbol": sym})
            print(f"[{mode}] {sym}: {len(t)} trades", flush=True)
        pd.DataFrame(trades).to_csv(outdir / f"trades_{mode}.csv", index=False)
        allsum.append(summarize(trades, mode))

    print("\n=== SUMMARY ===")
    print(json.dumps(allsum, indent=2))
    (outdir / "summary.json").write_text(json.dumps(
        {"overall": allsum, "per_symbol": per_sym}, indent=2))
    pd.DataFrame(per_sym).to_csv(outdir / "per_symbol.csv", index=False)


if __name__ == "__main__":
    main()

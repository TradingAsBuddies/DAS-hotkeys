#!/usr/bin/env python3
"""Build the two SMB-format PlayBook decks from docs/playbook/build/ (charts + stats.json).

Slide order follows SMB's PlayBook+Template+1.1124: Title · Bigger Picture (SPY, QQQ) · Intraday
Fundamentals · Technical Analysis (+ extra) · Trade Strategy · Trade Management · Reading the Tape ·
Technology · Trade Review · EV Calculator · Score Card.  Lato, bold-caps titles, white charts,
disclosure footer on every slide.  Run: ~/.venvs/playbook/bin/python docs/playbook/make_decks.py
"""
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "docs/playbook/build"
ST = json.loads((BUILD / "stats.json").read_text())
FONT = "Lato"
INK, MUTED, ACCENT = RGBColor(0x1A, 0x1B, 0x26), RGBColor(0x66, 0x66, 0x66), RGBColor(0x2E, 0x7D, 0xE9)
FOOTER = ("Hypothetical backtest results on Massive.com minute data; simulated trades were not executed and do not reflect "
          "slippage, commissions or liquidity except where stated. Not investment advice. PlayBook format after SMB Training.")


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
        self.blank = self.prs.slide_layouts[6]
        self.n = 0

    def _text(self, slide, x, y, w, h, text, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame; tf.word_wrap = True
        lines = text if isinstance(text, list) else [text]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run(); r.text = line
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), bold, color
            p.space_after = Pt(4)
        return tb

    def slide(self, title, subtitle=""):
        s = self.prs.slides.add_slide(self.blank)
        self.n += 1
        self._text(s, Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.7), title.upper(), 26, True)
        if subtitle:
            self._text(s, Inches(0.5), Inches(0.95), Inches(12.3), Inches(0.4), subtitle, 12, False, MUTED)
        self._text(s, Inches(0.5), Inches(7.0), Inches(11.5), Inches(0.4), FOOTER, 7, False, MUTED)
        self._text(s, Inches(12.3), Inches(7.0), Inches(0.6), Inches(0.4), str(self.n), 8, False, MUTED, PP_ALIGN.RIGHT)
        return s

    def bullets(self, slide, items, x=Inches(0.5), y=Inches(1.5), w=Inches(12.3), h=Inches(5.3), size=15):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame; tf.word_wrap = True
        for i, it in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            head, _, rest = it.partition("::")
            r = p.add_run(); r.text = "•  " + head.strip(); r.font.name, r.font.size, r.font.bold = FONT, Pt(size), bool(rest)
            r.font.color.rgb = INK
            if rest:
                r2 = p.add_run(); r2.text = " " + rest.strip(); r2.font.name, r2.font.size = FONT, Pt(size); r2.font.color.rgb = INK
            p.space_after = Pt(8)

    def picture(self, slide, name, x=Inches(0.5), y=Inches(1.45), w=Inches(12.3)):
        slide.shapes.add_picture(str(BUILD / name), x, y, width=w)

    def table(self, slide, rows, x=Inches(0.5), y=Inches(1.5), w=Inches(12.3), col_w=None, size=12):
        n_r, n_c = len(rows), len(rows[0])
        tbl = slide.shapes.add_table(n_r, n_c, x, y, w, Inches(0.36) * n_r).table
        if col_w:
            for i, cw in enumerate(col_w):
                tbl.columns[i].width = Inches(cw)
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                c = tbl.cell(i, j); c.text = str(val)
                for p in c.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.name, r.font.size, r.font.bold = FONT, Pt(size), i == 0
                        r.font.color.rgb = INK
                c.fill.solid(); c.fill.fore_color.rgb = RGBColor(0xF3, 0xF4, 0xF8) if i == 0 else RGBColor(0xFF, 0xFF, 0xFF)
        return tbl

    def save(self, path):
        self.prs.save(path)


def ev_rows(st, slip_r=None):
    wr, aw, al = st["wr"], st["avg_win"], -st["avg_loss"]
    ev = wr * aw - (1 - wr) * al
    rows = [["Input", "Value", "Note"],
            ["Win rate", f"{wr*100:.1f}%", f"{st['n_win']} winners / {st['trades']} trades" + (f" ({st['n_flat']} breakeven scratches)" if st.get("n_flat") else "")],
            ["Average winner", f"+{aw:.2f}R", "1R = the planned stop distance × shares = $75 in SIM"],
            ["Average loser", f"−{al:.2f}R", "smaller than 1R: gap-through and breakeven exits"],
            ["Expectancy per trade", f"{ev:+.3f}R", "wr × avg win − (1 − wr) × avg loss"],
            ["Three-year total", f"{st['r']:+.0f}R", f"max drawdown {st['dd']:.1f}R · daily Sharpe {st['sharpe']:.2f}"]]
    if slip_r is not None:
        rows.append(["With 5¢ adverse slippage on every stop", f"{slip_r:+.0f}R", "the number that decides whether it is tradeable"])
    return rows


def sma34_deck():
    st, ex = ST["sma34"], ST["sma34"]["example"]
    d = Deck()
    s = d.slide("34-SMA Premarket Trend", "SMB PlayBook · davdunc · example trade RKLB · May 11, 2026")
    d.bullets(s, [
        "Setup:: a limit order placed before the bell at the 34-SMA of the extended-hours 15-minute chart, in the direction of the premarket trend.",
        "Trend read:: 15-minute 9-EMA above the premarket VWAP → long; below → short. Read once, pre-open.",
        "Stock selection:: medium and large caps with premarket volume at least 2× their own 20-day median.",
        "Exit:: 1.0×ATR stop, no target; exit on the first 15-minute close back across the 9-EMA. Flat at 15:55.",
        f"Evidence:: {st['trades']} simulated trades over three years on 14 names, {st['r']:+.0f}R, +35R after 5¢ of stop slippage.",
        "Status:: 1R paper experiment. Every element of this rule was chosen after seeing the data; treat the numbers as in-sample.",
    ], size=16)

    o, c = ST["index"]["sma34_SPY"]
    s = d.slide("Bigger Picture", f"$SPY on the example day · open {o:.2f}, close {c:.2f} ({(c/o-1)*100:+.2f}%)")
    d.picture(s, "sma34_spy.png", w=Inches(11.5))
    d._text(s, Inches(0.5), Inches(6.2), Inches(12.3), Inches(0.7),
            "The setup is a single-stock premarket-volume play; the market only has to not fight it. SPY was quiet and slightly higher on the day, "
            "so the RKLB long was trading its own catalyst, not the tape.", 12, False, MUTED)
    o, c = ST["index"]["sma34_QQQ"]
    s = d.slide("Bigger Picture", f"$QQQ on the example day · open {o:.2f}, close {c:.2f} ({(c/o-1)*100:+.2f}%)")
    d.picture(s, "sma34_qqq.png", w=Inches(11.5))
    d._text(s, Inches(0.5), Inches(6.2), Inches(12.3), Inches(0.7),
            "Over three years the rule made money in both directions (shorts 332 trades / +33R, longs 292 / +26R in the intraday form), "
            "so the index direction is context, not a filter.", 12, False, MUTED)

    s = d.slide("Intraday Fundamentals", f"Why {ex['sym']} was on the list on {ex['day']}")
    d.bullets(s, [
        f"Premarket volume {ex['pm_ratio']}× its 20-day median premarket volume:: the only stock-selection filter. Two to three times is the sweet spot; above five it trades worse.",
        "Pre-open read at 09:15:: 9-EMA 105.09 above the premarket VWAP 105.04, so the trend was up and the order was a buy.",
        "Level:: the 34-SMA of the extended-hours 15-minute chart at 104.41, below the 09:29 price, so the limit rested away from the market.",
        "Universe:: AMD BB CRWD DELL DRI INTC IONQ META MSTR NVDA RKLB SMCI TSLA XOM. No ETFs, commodities or small caps: the tight stop needs single-stock range and the premarket-volume filter needs a name with a normal premarket.",
    ], h=Inches(2.6), size=14)
    d.table(s, [["Stat", "Value", "Stat", "Value"],
                ["Trades, 3 years", st["trades"], "Win rate", f"{st['wr']*100:.1f}%"],
                ["Total", f"{st['r']:+.1f}R", "Per trade", f"{st['per']:+.3f}R"],
                ["Average winner", f"+{st['avg_win']:.2f}R", "Average loser", f"{st['avg_loss']:.2f}R"],
                ["Max drawdown", f"{st['dd']:.1f}R", "Daily Sharpe (all days)", f"{st['sharpe']:.2f}"],
                ["By year", ", ".join(f"{k} {v:+.0f}R" for k, v in st["by_year"].items()), "Exits", f"stop {st['exits']['stop']} · 9-EMA close {st['exits']['ema9']} · 15:55 {st['exits']['eod']}"],
                ["Days with a fill", "1 in 3 across 14 names", "One position a day", "+32R on 230 trades"]],
            y=Inches(4.2), col_w=[2.6, 3.5, 2.6, 3.6], size=11)

    s = d.slide("Technical Analysis", f"{ex['sym']} {ex['day']} · 15-minute, extended hours · the level, the read, the fill and the exit")
    d.picture(s, "sma34_example.png", w=Inches(11.8))
    s = d.slide("Technical Analysis (extra)", "The first hour on 1-minute bars: the opening drive fills the resting order; the stop is 1.0×ATR so it survives the opening minute")
    d.picture(s, "sma34_fill.png", w=Inches(11.8))
    d._text(s, Inches(0.5), Inches(6.3), Inches(12.3), Inches(0.6),
            "Why 1.0×ATR and not 0.75: with the 0.75 stop, 344 of 521 first-fifteen-minute fills were stopped, median one minute after the fill. "
            "The opening minute's range is larger than 0.75 of a 15-minute ATR on these names.", 11, False, MUTED)

    s = d.slide("Trade Strategy", "The rule, as backtested (backtest/backtest_sma34_trend.py --preopen --gate 09:30 --exit-ema9-close --target-r 0 --stop-mult 1.0)")
    d.bullets(s, [
        "Scan 09:15:: premarket volume ≥ 2× the name's 20-day median premarket volume. Skip names above 5× (they trade worse) and anything sub-$10 or post reverse-split.",
        "Direction:: 9-EMA on the extended-hours 15-minute chart above the premarket VWAP → long; below → short.",
        "Order:: limit at the 34-SMA value of the last completed 15-minute bar before 09:30. Only if the 09:29 price is on the trade side of it (buy below the market, sell short above it).",
        "Stop:: 1.0 × ATR(14) of the 15-minute chart, entered with the order as a bracket.",
        "Target:: none. Exit on the first 15-minute bar that closes back across the 9-EMA, after at least one bar has closed with the trade.",
        "Time:: order live 09:30 to 15:00; anything still open is flat at 15:55. One entry per name per day; one position per day if that is the account rule.",
        "Size:: shares = 1R ÷ stop distance, 1R = $75 in SIM (TR4425), $28 live, per PREFERENCES.md R-CONFIG. Cap 300 shares.",
        "Do not:: re-price the order intraday, take a second fill, or hold a name that never closes a 15-minute bar with the trade past 12:00.",
    ], size=13)

    s = d.slide("Trade Management", f"{ex['sym']} {ex['day']} as it was simulated")
    d.table(s, [["Step", "Time", "Price", "Detail"],
                ["Pre-open read", "09:15", "9-EMA 105.09 vs PM VWAP 105.04", "long; 34-SMA 104.41; ATR 1.37"],
                ["Order placed", "before 09:30", "buy limit 104.41", f"stop 103.04 (1.0×ATR); {ex['qty']} shares = $75 ÷ 1.37"],
                ["Fill", ex["entry_t"], f"{ex['entry']:.2f}", "opening drive trades down to the level, then reverses"],
                ["Stop check", "09:30–09:45", "low held above 103.04", "the 0.75×ATR stop would have been 103.38: also held here, not in most cases"],
                ["Armed", "09:45", "09:30 bar closed above the 9-EMA", "the 9-EMA exit is now live"],
                ["Exit", ex["exit_t"], f"{ex['exit']:.2f}", "15:15 bar closed below the 9-EMA; sold at the 15:30 open"],
                ["Result", "", f"+${ex['pnl']:.0f}", f"{ex['r_plan']:+.1f}R on the planned risk"]],
            col_w=[2.0, 1.6, 3.6, 5.1], size=12)
    d.bullets(s, [
        "Runner management is the whole P&L:: the ten largest wins are 144% of the net profit. Nothing in the rule takes partial profit; adding a partial at +1R tripled the win rate and removed most of the profit in the sister test.",
        "Stop fills are the risk:: 513 of 733 exits are stops. Five cents of adverse slippage per stop turns +86R into +35R; measure the first twenty live stops before sizing above 1R.",
    ], y=Inches(4.7), h=Inches(2.0), size=12)

    s = d.slide("Reading the Tape", "What to watch at the level between 09:30 and 10:00")
    d.bullets(s, [
        "At the 34-SMA:: does the opening drive stall at the level or trade through it? A fill that comes with size lifting the offer (long) or hitting the bid (short) into the level is the good version; a fill inside a one-minute flush that keeps going is the stop.",
        "Premarket VWAP:: the second reference. For a long, price holding between the 34-SMA and the PM VWAP after the fill is confirmation; a print back below the PM VWAP with the 9-EMA turning is the early warning the 15-minute close will confirm.",
        "The 09:45 close:: the first completed bar. Above the 9-EMA arms the exit and says the drive is real; below it and the trade is living on the stop.",
        "Level to watch on the tape:: the fill price itself. The trade that never comes back to the fill after 09:45 is the runner; the one that keeps testing it is a scratch waiting to happen.",
        "Speed:: median one minute from fill to stop in the losing form. If the first minute after the fill runs against you, there is no decision to make; the stop makes it.",
    ], size=13)

    s = d.slide("Technology", "Everything the trade needs is scripted; the human job is the 09:15 read and the order")
    d.bullets(s, [
        "Scan:: fl_forward_test.py breadth and gameplan reader; premarket-ratio filter is the --pm-vol-mult logic in backtest_sma34_trend.py, to be lifted into the driver.",
        "Order:: DAS bracket via the CMD API (SCRIPT montage1 …): limit at the level, SLP stop at 1.0×ATR, sized by the R-CONFIG unit. Refuses without an ATR value.",
        "Exit:: 9-EMA close monitor on 15-minute bars, same pattern as the FL driver's ema9 exit; breakeven and flatten paths already exist (22-fl-flatten.das).",
        "Chart:: DAS 15-minute with extended hours ON, studies 9-EMA, 34-SMA, VWAP (premarket); the regular-hours chart gives a different level and a worse result for this form.",
        "Safety:: paper account TR4425 only until twenty live stop fills are measured; the driver halts new entries when the montage name is lost (the 09-25 failure).",
        "Reproduce:: docs/forward-tests/sma34-trend-3y.md, backtest/results/sma34-3y-preopen-ext-ema-s10.json.",
    ], size=13)

    s = d.slide("Trade Review", "What the three years say to do better")
    d.bullets(s, [
        "The original form does not work:: 0.75×ATR stop with a 1.8R target is −14R pre-open and −71R re-priced intraday; the opening minute takes the stop before the level can react.",
        "Two changes made it:: a trailing exit on the 9-EMA close instead of the target, and a stop outside the opening minute's range. Together they are the only positive pre-open form found.",
        "It is a runner strategy with a 27% win rate:: four trades in ten stop within minutes, one in four pays. Size for that, not for the win rate.",
        "In-sample:: chart type, stop width and exit were chosen after seeing the data. 2024 was flat; the three months of 2023 supplied 38 of the 86R. A walk-forward that picks the premarket band on 2024 alone is the next test.",
        "Fills:: touch-equals-fill at the limit and clean stop fills are assumed. Requiring a 1¢ trade-through cost 4R; five cents of stop slippage cost 51R.",
        "Next:: measure live stop slippage on TR4425; add --entry-window and the premarket scan to the driver; write the DAS bracket hotkey for the pre-open order.",
    ], x=Inches(0.5), w=Inches(7.6), size=12)
    d.picture(s, "sma34_equity.png", x=Inches(8.2), y=Inches(1.6), w=Inches(4.9))

    s = d.slide("EV Calculator", "Expectancy from the simulated distribution (SMB's EV sheet inputs)")
    d.table(s, ev_rows(st, slip_r=35.3), col_w=[3.6, 2.2, 6.5], size=13)
    d._text(s, Inches(0.5), Inches(5.0), Inches(12.3), Inches(1.2),
            "Read: a +0.12R expectancy on 733 trades is real but thin; it is carried by a 2.6R average winner against a 0.82R average loser. "
            "Any change that raises the win rate by capping winners destroys it. The friction row is the number to beat live.", 12, False, MUTED)

    s = d.slide("Score Card", "Self-graded 1–10 against the SMB rubric")
    d.table(s, [["Area", "Grade", "Reason"],
                ["Big Picture", "6", "Market direction is context only; no index filter was found that helped."],
                ["Intraday Fundamentals", "7", "One clean, testable filter (premarket volume ratio); no news or catalyst layer yet."],
                ["Stock Selection", "7", "Single stocks with range; ETFs and small caps excluded for stated reasons."],
                ["Technical Analysis", "8", "Level, read and exit are all defined on one chart and were simulated without look-ahead."],
                ["Trade Strategy", "7", "Rule is explicit and reproducible; chosen in-sample, so provisional."],
                ["Risk Management", "6", "Stop is defined and sized; stop-fill slippage is unmeasured and decides the edge."],
                ["Reading the Tape", "5", "Tape rules are written from the simulation, not from watching fills yet."],
                ["Technology", "8", "Backtester, driver, CMD API harness and flatten paths exist; pre-open bracket hotkey still to write."],
                ["Review: what can you do better?", "7", "Walk-forward, live slippage, entry window; all listed and scheduled."]],
            col_w=[3.4, 1.0, 7.9], size=12)
    out = ROOT / "docs/playbook/PlayBook-34SMA-Premarket-Trend.pptx"
    d.save(out)
    return out


def fl_deck():
    st, ex = ST["fl"], ST["fl"]["example"]
    d = Deck()
    s = d.slide("Fashionably Late", "SMB PlayBook · davdunc · 15-minute 9-EMA × 34-SMA cross · example trade MSTR · August 27, 2026")
    d.bullets(s, [
        "Setup:: the 15-minute 9-EMA crosses the 34-SMA on a regular-hours chart with volume above 1.5× the 20-bar average. Enter at the next bar's open.",
        "When:: entries from 09:45 to 11:00 only. The first bar after the open carries most of the edge; entries after 11:00 lose.",
        "Stock selection:: single stocks from the gameplan; no ETFs or commodities.",
        "Exit:: 0.75×ATR stop moved to breakeven at +0.5R, hold to the close. No target.",
        f"Evidence:: {st['trades']} simulated trades over three years, {st['r']:+.0f}R, max drawdown {st['dd']:.1f}R, +65R after 5¢ of stop slippage.",
        "Correction 2026-09-27:: an earlier figure of +292R included 387 entries at the 09:30 open on a cross printed on the prior day's last bar; those are a different trade and are removed here.",
    ], size=15)

    o, c = ST["index"]["fl_SPY"]
    s = d.slide("Bigger Picture", f"$SPY on the example day · open {o:.2f}, close {c:.2f} ({(c/o-1)*100:+.2f}%)")
    d.picture(s, "fl_spy.png", w=Inches(11.5))
    d._text(s, Inches(0.5), Inches(6.2), Inches(12.3), Inches(0.7),
            "FL is a first-hour momentum trade in the stock; the market matters through breadth ($TICK, $ADD, $VOLD) at the time of the cross, "
            "which the driver reads, rather than through the index chart.", 12, False, MUTED)
    o, c = ST["index"]["fl_QQQ"]
    s = d.slide("Bigger Picture", f"$QQQ on the example day · open {o:.2f}, close {c:.2f} ({(c/o-1)*100:+.2f}%)")
    d.picture(s, "fl_qqq.png", w=Inches(11.5))
    d._text(s, Inches(0.5), Inches(6.2), Inches(12.3), Inches(0.7),
            "Shorts carried about five times the longs over three years, but longs were not negative; both sides are taken.", 12, False, MUTED)

    s = d.slide("Intraday Fundamentals", f"Why {ex['sym']} qualified on {ex['day']}")
    d.bullets(s, [
        "Gameplan name:: MSTR was on the in-play list; FL is only run on the day's gameplan tickers, single stocks only.",
        "The cross:: on the 09:30–09:45 bar the 9-EMA closed above the 34-SMA on a regular-hours 15-minute chart, with the bar's volume above 1.5× the average of the prior 20 bars.",
        "First bar after the open:: this is where the rule earns. Over three years the 09:45 entries made +150R on 1,073 trades; 10:00 entries +36R on 614; 10:45 entries lost.",
        "Universe:: the 16 single stocks of the gameplans; the seven ETFs and commodities lost money under this rule and are excluded.",
    ], h=Inches(2.6), size=14)
    d.table(s, [["Stat", "Value", "Stat", "Value"],
                ["Trades, 3 years", st["trades"], "Win rate", f"{st['wr']*100:.1f}% ({st['n_flat']} breakeven scratches)"],
                ["Total", f"{st['r']:+.1f}R", "Per trade", f"{st['per']:+.3f}R"],
                ["Average winner", f"+{st['avg_win']:.2f}R", "Average loser", f"{st['avg_loss']:.2f}R"],
                ["Max drawdown", f"{st['dd']:.1f}R", "Daily Sharpe (all days)", f"{st['sharpe']:.2f}"],
                ["By year", ", ".join(f"{k} {v:+.0f}R" for k, v in st["by_year"].items()), "Exits", f"stop {st['exits']['stop']} (incl. breakeven) · close {st['exits']['eod']}"],
                ["First-bar entries only", "1,073 trades, +150R, +82R with 5¢ slip", "With 5¢ stop slippage, all entries", "+65R"]],
            y=Inches(4.2), col_w=[2.6, 3.7, 2.6, 3.4], size=11)

    s = d.slide("Technical Analysis", f"{ex['sym']} {ex['day']} · 15-minute, regular hours · cross, entry, stop, breakeven, close")
    d.picture(s, "fl_example.png", w=Inches(11.8))
    s = d.slide("Technical Analysis (extra)", "The first two hours on 1-minute bars: entry at the 09:45 open, stop 0.75×ATR, breakeven after the first bar shows +0.5R")
    d.picture(s, "fl_fill.png", w=Inches(11.8))

    s = d.slide("Trade Strategy", "The rule, as backtested (backtest_fl_week.py --bar-minutes 15 --rth-only --warmup-days 4 --stop-mult 0.75 --size-mult 1.5 --be-after 0.5 --last-entry 11:00)")
    d.bullets(s, [
        "Chart:: 15-minute, regular hours only, 9-EMA and 34-SMA warm from four prior sessions.",
        "Signal:: a completed bar whose close moves the 9-EMA across the 34-SMA, with that bar's volume above 1.5× the average of the 20 bars before it. Crosses printed on a prior day's bar do not count.",
        "Entry:: market at the open of the next bar, 09:45 to 11:00 only. Two entries per name per day at most.",
        "Stop:: 0.75 × ATR(14) of the 15-minute chart, sized as if it were 1.5×ATR (the SIM convention), 1R = $75 SIM / $28 live.",
        "Breakeven:: once a completed bar has shown +0.5R in favour, move the stop to entry.",
        "Exit:: hold to the close (flat at 15:55). No target, no partials: partial profit at +1R cut the three-year result by 85%.",
        "Do not:: trade the 1-minute cross (−7,680R over three years), enter after 11:00, or use a 9-EMA trail on 1-minute bars (−1,395R).",
        "Breadth gate:: the driver suppresses a signal whose side disagrees with $VOLD; keep it, it filtered direction correctly on 09-25.",
    ], size=13)

    s = d.slide("Trade Management", f"{ex['sym']} {ex['day']} as it was simulated")
    d.table(s, [["Step", "Time", "Price", "Detail"],
                ["Cross", f"{ST['fl']['signal_bar']} bar close", "9-EMA crosses above the 34-SMA", "bar volume above 1.5× the 20-bar average"],
                ["Entry", ex["entry_t"][11:16], f"{ex['entry']:.2f}", f"open of the next bar + 0.15 slip; {ex['qty']} shares"],
                ["Initial stop", ex["entry_t"][11:16], f"{ST['fl']['stop0']:.2f}", f"0.75 × ATR {ex['atr']:.2f}"],
                ["Breakeven", "10:00", f"{ex['entry']:.2f}", "the 09:45 bar showed more than +0.5R; stop to entry"],
                ["Exit", ex["exit_t"][11:16], f"{ex['exit']:.2f}", "flat at the close"],
                ["Result", "", f"+${ex['pnl']:.0f}", f"{ex['pnl']/75:+.1f}R"]],
            col_w=[2.0, 1.8, 3.4, 5.1], size=12)
    d.bullets(s, [
        "Half the trades scratch at breakeven:: 1,134 of 2,282 exits are at entry. That is the design; the stop is inside the noise and breakeven is the real stop.",
        "One in ten pays:: winners average 2.6R and the ten largest are a large share of the total. Never cap them.",
    ], y=Inches(4.4), h=Inches(2.0), size=12)

    s = d.slide("Reading the Tape", "What to watch on the cross bar and the bar after it")
    d.bullets(s, [
        "Volume persistence:: the cross bar's volume must be followed; the 50/2 rule from the LGCL review (each of the next two bars at least half the cross bar's volume) is the tape version of the 1.5× filter.",
        "The 09:45 open:: the entry is at the market; a wide spread or a print far from the 09:45 15-minute open is the slippage the backtest does not model.",
        "First bar after entry:: +0.5R moves the stop to breakeven. On the tape that is the bar that has to hold above the 9-EMA; if it closes back below, the scratch is coming.",
        "Level to watch:: the entry price. After breakeven the trade is free; the runner is the one that never revisits it.",
        "Breadth:: $VOLD sign must agree with the side at the cross; $TICK extremes against the trade at entry are a reason to wait one bar, not to skip.",
    ], size=13)

    s = d.slide("Technology", "Built and tested against DAS on the paper account")
    d.bullets(s, [
        "Driver:: tools/fl_forward_test.py reads the DAS gameplan file, evaluates completed bars, injects entries through the CMD API into montage1, verifies every injection and halts on a lost window name.",
        "Scripts:: 20-fl-long.das / 21-fl-short.das place the entry with the 1.5×ATR stop; 22-fl-flatten.das closes by side and quantity; 00 loads the desktop.",
        "Harness:: tools/das_script_test.py runs, checks and dismisses script errors over the CMD API; docs/CMD-API-TESTING.md.",
        "Backtest:: backtest/backtest_fl_week.py on Massive flat files; gate fixed 2026-09-27 (entry-bar time, no prior-day crosses).",
        "Still to build:: --bar-minutes 15 mode in the driver, breakeven order update through %OrderAct, entry window 09:45–11:00, single-stock filter from the gameplan.",
        "Lesson from 09-25:: name montage1 by hand and File → Save Desktop; the driver now refuses to trade a window it cannot verify.",
    ], size=13)

    s = d.slide("Trade Review", "What the three years say to do better")
    d.bullets(s, [
        "The 1-minute rule as traded on 09-24 has no edge:: 13 of 13 stops live, −7,680R over three years. The 15-minute chart is the setup.",
        "The edge is the first bar:: 09:45 entries carry three quarters of the profit. Everything after 11:00 is negative.",
        "The gate error:: until today the backtest let a cross on yesterday's last bar be bought at the open. Those 387 trades made +242R and are a different, untested idea (see the report). Removing them leaves +201R.",
        "Win rate cannot be bought:: partials raise it and destroy the P&L; the return is the tail of runners into the close.",
        "Friction:: +65R after 5¢ stop slippage; first-bar entries alone +82R. Measure live stop fills before sizing.",
        "Next:: driver flags for the 15-minute rule, breakeven via %OrderAct, walk-forward on the entry window, and a separate test of the overnight cross.",
    ], x=Inches(0.5), w=Inches(7.6), size=12)
    d.picture(s, "fl_equity.png", x=Inches(8.2), y=Inches(1.6), w=Inches(4.9))

    s = d.slide("EV Calculator", "Expectancy from the simulated distribution (SMB's EV sheet inputs)")
    d.table(s, ev_rows(st, slip_r=64.9), col_w=[3.6, 2.2, 6.5], size=13)
    d._text(s, Inches(0.5), Inches(5.0), Inches(12.3), Inches(1.2),
            "Read: +0.09R per trade with half the trades scratched. The average loser is 0.42R because the stop sits inside the noise and most losers are "
            "breakeven or gap-through fills; the average winner is 2.6R. Sharpe 2.2 and a 12R drawdown are the reasons to prefer this over the 34-SMA play for size.",
            12, False, MUTED)

    s = d.slide("Score Card", "Self-graded 1–10 against the SMB rubric")
    d.table(s, [["Area", "Grade", "Reason"],
                ["Big Picture", "6", "Breadth gate exists in the driver; no index-regime filter has been tested."],
                ["Intraday Fundamentals", "6", "Gameplan names only; no catalyst or news scoring yet."],
                ["Stock Selection", "7", "Single stocks only, ETFs excluded on evidence; universe is still today's names run backwards."],
                ["Technical Analysis", "8", "Cross, volume, stop, breakeven and exit are all on one chart and reproducible."],
                ["Trade Strategy", "7", "Explicit and backtested; the gate error shows how a definition can drift from the chart."],
                ["Risk Management", "7", "Breakeven at +0.5R keeps the drawdown to 12R; stop slippage still unmeasured live."],
                ["Reading the Tape", "6", "50/2 volume persistence rule exists and is enforceable; not yet validated across a sample."],
                ["Technology", "8", "Driver, scripts, harness and backtester exist and were exercised live; 15-minute driver mode pending."],
                ["Review: what can you do better?", "8", "Two live days reviewed, both failures diagnosed to cause; corrections shipped as releases."]],
            col_w=[3.4, 1.0, 7.9], size=12)
    out = ROOT / "docs/playbook/PlayBook-Fashionably-Late.pptx"
    d.save(out)
    return out


if __name__ == "__main__":
    for f in (sma34_deck(), fl_deck()):
        p = Presentation(str(f))
        print(f.name, f"{f.stat().st_size/1e6:.2f} MB", len(p.slides), "slides")

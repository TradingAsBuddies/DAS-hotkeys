# KOD — day profile, 2026-09-28

Read-only Level 2 / time-and-sales watch over the DAS CMD API (`tools/das_tape_profile.py`), 07:48 to
16:05 ET. 1.22M tape lines, 595,013 prints, 32.2M regular-session shares seen (DAS day volume 37.8M).
Auto-profile: `KOD-2026-09-28-profile.md` (final rewrite 16:05). Event log: `KOD-2026-09-28-notes.md`.

**Catalyst.** Pivotal DAYBREAK wet-AMD data met endpoints; DAS newsfeed "Breaking" at **07:18 ET**.
Friday close 32.35. Untradeable at our R unit (three shares live); watched for the profile.

## The day in one table

| | |
|---|---|
| Open / High / Low / Close | 61.63 / **95.78** (15:44) / 60.49 (09:30) / **89.92** (closing cross, 279,479 sh) |
| Change | **+178%** on 37.8M shares; premarket alone 5.4M to 65.51 |
| VWAP at the close | 79.40 |
| Point of control | **89.68** (3.39M shares, 10.5%); value area 77.88 – 92.04 |
| Off-exchange (FADF) share | 19.75M of 32.2M seen = **61%** |
| Largest prints | 279,479 closing cross · 100,000 @ 75.64 (09:52) · 51,100 @ 89.97 (14:10) · 33,500 @ 89.47 (13:12) · four of 20–25K in 84–85 (10:09–10:12) · 24,500 @ 95.55 (15:44) |
| Legs | eleven new-high legs 09:32 → 14:27; three corrections of 8–12% (10:13→78.00, 10:47→75.84, 14:27→88.66); last-hour rejection 95.78 → 89.00 |

## 15-minute bars from the tape (aggression = prints at/above ask vs at/below bid)

| Bar | Open | High | Low | Close | Volume | Net flow | Note |
|---|---:|---:|---:|---:|---:|---:|---|
| 09:30 | 61.63 | 74.72 | 60.49 | 73.01 | 4.93M | +61K | flush bought the premarket POC 60.96; 65 wall broke 09:32 |
| 09:45 | 73.22 | 81.29 | 72.77 | 78.82 | 2.83M | **+257K** | 100,000-sh block 75.64 at 09:52, +7% in two minutes |
| 10:00 | 78.52 | 87.83 | 75.97 | 83.60 | 2.53M | +121K | 115K-sh cluster 84–85, high 87.83 |
| 10:15 | 83.46 | 84.76 | 78.00 | 84.17 | 1.62M | +26K | 11% flush to 78 inside the bar, bought back |
| 10:30 | 84.34 | 87.13 | 82.40 | 82.61 | 1.45M | +49K | first lower close |
| 10:45 | 82.86 | 84.85 | 77.21 | 77.36 | 1.01M | **−82K** | first sell-side bar |
| 11:00 | 77.69 | 80.59 | 76.44 | 76.95 | 981K | +28K | |
| 11:15 | 76.92 | 81.52 | **75.84** | 80.21 | 912K | +24K | low 20c above the block price |
| 11:30 | 80.03 | 83.31 | 79.26 | 83.15 | 942K | **+179K** | ~40,000 sh lifted at 80.00 at 11:33 |
| 11:45 | 83.13 | 84.90 | 81.00 | 84.75 | 721K | +74K | |
| 12:00 | 84.73 | 87.51 | 83.33 | 87.20 | 1.13M | +103K | |
| 12:15 | 86.97 | 89.69 | 86.51 | 88.57 | 1.18M | +93K | through 87.83; size buying the breakout |
| 12:30 | 88.48 | 89.90 | 86.55 | 87.66 | 728K | +6K | 25,340 @ 88.00 absorbed |
| 12:45 | 87.57 | 88.85 | 85.50 | 87.45 | 674K | −15K | |
| 13:00 | 87.54 | 90.88 | 86.96 | 90.30 | 681K | +113K | |
| 13:15 | 89.43 | 90.66 | 86.20 | 89.34 | 935K | −48K | 33,500 @ 89.47 plus ~60K more, 87.6–89.6 |
| 13:30 | 89.31 | 92.19 | 87.99 | 90.19 | 744K | +14K | the band was bought |
| 13:45 | 90.34 | 91.40 | 87.63 | 87.85 | 667K | −21K | 67K-sh step-down 90.01→88.39 |
| 14:00 | 87.92 | 92.49 | 87.40 | 90.66 | 775K | +54K | step-down bought; 51,100 @ 89.97 then 21,900 lifted |
| 14:15 | 90.56 | 95.69 | 89.50 | 91.77 | 1.06M | +23K | spike, first rejected within a minute |
| 14:30 | 91.84 | 92.95 | 88.66 | 90.66 | 809K | −34K | |
| 14:45 | 90.73 | 93.31 | 88.31 | 89.66 | 744K | −39K | |
| 15:00 | 89.71 | 93.59 | (84.61 stray 400-sh print) | 91.84 | 703K | +13K | |
| 15:15 | 91.49 | 93.38 | 90.90 | 92.75 | 598K | +10K | |
| 15:30 | 92.90 | **95.78** | 92.28 | 94.75 | 1.00M | +26K | 24,500 @ 95.55 at 15:44:42 |
| 15:45 | 94.50 | 95.27 | 89.00 | 89.97 | 1.51M | +5K | −6% in the last fifteen minutes; 7,901 sold at 90.00 |
| 16:00 | 90.11 | 90.50 | 88.01 | 88.15 | 372K | −23K | closing cross 89.92 and late prints |

## Volume by price (regular session)

| Price | Volume | Share |
|---:|---:|---:|
| **89.68** | 3,390,626 | 10.5% ← POC |
| 87.32 | 2,321,596 | 7.2% |
| 88.50 | 2,123,631 | 6.6% |
| 90.86 | 1,993,875 | 6.2% |
| 71.98 | 1,667,855 | 5.2% |
| 80.24 | 1,655,562 | 5.1% |
| 83.78 | 1,652,292 | 5.1% |
| 92.04 | 1,639,242 | 5.1% |

The morning's volume (60–75) is a minor node; the day's centre of gravity migrated from 60.96 (premarket
POC) to 71.89 (noon) to 87.75 (14:00) to 89.68 at the close. Two thirds of the day's volume traded
between 83 and 93. The close at 89.92 is on the point of control.

## What the tape said, in order

1. **Premarket (07:18–09:30).** 32 → 65.51 in ninety minutes. Four tests of 65 with size lifting
   64.99 (14,917 / 14,444 / 9,421 / 9,365 on ARCA) and no follow-through: absorption. Buyers net
   aggressive in every 15-minute bar while price stayed flat. Value 62.13–64.98 into the bell.
2. **Open (09:30–09:36).** Flush to 60.49, the premarket POC bought, 65 broke at 09:32, 74.72 by
   09:36. First-bar net flow +74K on 1.1M shares. Half the volume off-exchange from the first minute.
3. **The block (09:52:40).** 100,000 shares crossed at 75.64, 4.7% under the high. 81.29 two minutes
   later. The block price was the floor for the whole day: the deepest correction (11:15) came within
   twenty cents of it and turned.
4. **The 84–85 cluster (10:09–10:12).** 115,000 shares crossed in four prints, each a little lower.
   Read live as possible distribution. Followed by 87.83, then the first pullback that broke a lift
   level (11%, to 78.00), then a 12% correction to 75.84 over ninety minutes. So the cluster *did*
   precede the correction, and was *also* bought through by 12:15. Both readings were partly right.
5. **The turn (11:33:09).** ~40,000 shares lifted at 80.00 in one second after a seller had worked
   80.00–80.89 for eight minutes. The 11:30 bar's +179K net flow is that print. Five buying bars
   followed, 75.84 → 89.90.
6. **Three more step-down clusters** (87.6–89.6 at 13:12, 90.0–88.4 at 13:51, 89.97 at 14:10), each
   read live as a seller working an order, each followed by a new high within an hour. **On this tape,
   size printing near the highs was a buyer taking supply.** That is the lesson of the day.
7. **The first rejected spike (14:27).** 95.69 in one print, sold within a minute, 7% pocket to
   88.66. From here the sellers had the aggression (three net-selling bars) and the buyers had the
   levels (every dip to 88.3–88.7 bought).
8. **The close.** A last push to 95.78 at 15:44 with 24,500 crossed at 95.55, then 7,901 sold at
   90.00 four minutes later and a −6% final fifteen minutes; closing cross 89.92, on the POC, under
   the 92.04 top of value. The last-hour high was the second rejection of 95.5–95.8 with size, and the
   only cluster of the day that was not bought before the bell.

## Book

Displayed top-five depth stayed at 8–25 round lots a side all day with a 25–55 cent spread, on a
stock trading 37M shares: the lit book was never where the stock traded. Ask stacks formed under
every high (24 vs 9 at 12:55, 20 vs 8 at 14:35) and were lifted every time until the last hour. Bid
stacks formed into the two big corrections (26 vs 16 at 10:50, 32 vs 16 at 11:35) and held. The
book was a lagging confirmation, never a signal.

## MTEK, the contrast

Same morning, same kind of headline-driven premarket run: 1.94 premarket high, back below Friday's
1.095 close before the bell, 0.93 low at 09:54, 0.97 close (−11%) on 46M shares. Every 15-minute
bar after 09:45 was inside 0.96–1.05; value 0.95–1.00. Its book swung from 6:1 on the offer (13:53)
to 9:1 on the bid (15:21) without the price moving a cent: a dollar stock's book is stacked and
pulled for free. The difference from KOD on the tape was simple: MTEK had no level that was defended
with size, so nothing kept buyers engaged once the premarket run stalled.

## For the playbook

- A news gapper that defends a level with size before the open (KOD's four tests of 65) is a
  different animal from one that does not (MTEK). The premarket tape decides which one you have.
- On a strong day, off-exchange size near the highs was accumulation eleven times and distribution
  twice (the two rejections of 95.5–95.8). Do not fade size at a high on a 100%+ day until a spike
  has been rejected inside a minute; after that, the sellers have the aggression.
- The block price (75.64) and the migrating point of control (60.96 → 71.89 → 87.75 → 89.68) were
  the only levels that mattered for pullbacks. Round numbers were where sellers showed (65, 80, 90,
  94, 95) and every one except the last was lifted.
- Money flow (at-ask minus at-bid) confirmed each leg but thinned before the tops: +257K, +121K,
  +26K into the 10:13 high; +113K, +14K, −21K into the 13:35 high. A leg on falling flow was the tell
  for each correction.
- The stock ignored the index all day: SPY sat on the floor of its 765–770 box, $VOLD ended near
  −200K, VIX 16. A single-stock catalyst of this size does not read the tape.

Reproduce: `~/market_data/tape/KOD_2026-09-28_tape.jsonl` (1.22M lines) replays through
`tools/das_tape_profile.py` on start; the bar and profile tables above are from its final rewrite.

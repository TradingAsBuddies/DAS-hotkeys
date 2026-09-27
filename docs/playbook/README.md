# PlayBooks (SMB format)

Two decks, written to be shared: the rule, the evidence and the caveats, with no account-specific sizing or tooling. SMB PlayBook slide order (Title · Bigger Picture · Intraday Fundamentals · Technical
Analysis · Trade Strategy · Trade Management · Reading the Tape · Technology · Trade Review · EV
Calculator · Score Card), rebuilt from scratch with python-pptx because the 9.7 MB SMB template is
copyright SMB Training and is not in this repo.

- `PlayBook-34SMA-Premarket-Trend.pptx` — pre-open limit at the 34-SMA in the premarket trend, 1.0×ATR stop, 9-EMA close exit.
- `PlayBook-Fashionably-Late.pptx` — 15-minute 9-EMA × 34-SMA cross, 0.75×ATR + breakeven, entries 09:45–11:00 (gate-corrected numbers).

Rebuild: `~/.venvs/playbook/bin/python docs/playbook/make_charts.py && ~/.venvs/playbook/bin/python docs/playbook/make_decks.py`
(venv: `python3 -m venv ~/.venvs/playbook && ~/.venvs/playbook/bin/pip install python-pptx matplotlib`).
Charts and `stats.json` are written to `build/`. All numbers are hypothetical backtest results; see `docs/forward-tests/`.

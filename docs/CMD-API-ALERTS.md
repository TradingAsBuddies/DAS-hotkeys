# Price alerts through the CMD API

How to make, check and audit DAS price alerts from WSL, and the drills that keep the practice
honest. Tool: `tools/das_alerts.py`. Preflight: `tools/das_script_test.py doctor`. Harness
background: `docs/CMD-API-TESTING.md`.

Evidence labels follow `docs/spec/REQUIREMENTS.md`: **[V]** seen on this build with the source
named, **[D]** documented in a manual, **[I]** inferred and untested.

## The one fact that shapes everything

**The CMD API does two things: FIX-style order and account calls, and executing scripts and
hotkeys.** Alerts are not part of the first. They are reached only through the second. The
Frontend CMD API Manual (2021) has no command for creating, listing or deleting alerts, and
no alert push line **[D]**, checked 2026-11-19.

So:

- An alert is a hotkey-script object, made by executing script text with
  `SCRIPT GLOBALSCRIPT <script>`.
- Every answer comes back through `MsgLog` lines in `LOG\YYMMDDLog.txt`, never through the socket.
- **A triggered alert does not reach a client over the socket.** It sounds, speaks or pops up
  inside DAS. A program that must react to the level has to watch the price itself
  (`SB <sym> Lv1`) or find the trigger in the log. Whether DAS logs a trigger is unknown
  (drill 6).

## What is verified on 5.8.4.8 (2026-11-19)

| Fact | Evidence |
|---|---|
| This payload creates an alert, and `GetAlertObj(name)` returns it with `.Symb` and `.name` set: `$a = NewAlertObj(); $a.name = "K0102 ABCD LONG 101.25"; $a.Symb = "ABCD"; $a.AddItem("L1 LAST", ">=", "101.25"); $a.save();` | **[V]** DAS log 09:01:48 to 09:02:02: `ALERTCHK ABCD K0102 ABCD LONG 101.25` |
| `"L1 LAST"` is accepted as an `AddItem` field. The guide only shows `"L1 BID"` | **[V]** same lines; 24 alerts saved that morning with no error |
| **`GetAlertObj("no such name").Symb` is ScriptError:100 "Function return is not Object".** That error opens a dialog that freezes the CMD API until it is dismissed | **[V]** DAS log 09:02:30 |
| Assigning first and guarding with `IsObj()` is safe. A missing name logs `MISSING` and opens no dialog | **[V]** DAS log 09:09:31 to 09:09:33, `das_alerts.py check` |
| `das_alerts.py ... --send` on a name already present sends nothing | **[V]** 09:09, the log still holds one creation line for that name |
| No file in the install changes when an alert is saved. `Alert.xml` is a sample dated 2012 | **[V]** `find -mmin` after the 09:01 saves |
| `$alert.Reset(); $alert.save();` "remove alerts from alert list" | **[D]** advanced hotkey guide p.34. How many it removes is unknown, so **no tool here ever sends `Reset`** |
| Chart-alert hotkeys (`AlertName=…;AlertType=LastPrice;AlertOperator=>;AddAlert`) wait for a mouse click on the chart | **[D]** hotkeys guide p.18. Not usable from the API |

## The tool

```sh
tools/das_script_test.py doctor                    # files only: install, port, scripting, log
tools/das_script_test.py doctor --connect          # + watch-mode login, montage1, hidden_chart1

tools/das_alerts.py add ABCD LONG 101.25 --op ">="           # dry run: prints the payload
tools/das_alerts.py add ABCD LONG 101.25 --op ">=" --send    # create, skip if present, read back
tools/das_alerts.py plan scripts/local/alerts-today.json      # dry run of a plan
tools/das_alerts.py plan scripts/local/alerts-today.json --send
tools/das_alerts.py check "K0102 ABCD LONG 101.25"           # present / missing, live
tools/das_alerts.py log                                        # today's alert activity, no socket
```

- **Names** are `<prefix> <SYMBOL> <TAG> <level>`, for example `K0102 WXYZ PRIOR_LO 50.07`. The
  default prefix is `K` plus month and day, the convention an earlier game plan used. Levels
  print with at least two decimals, so `15` is `15.00` and matches a name made by hand.
- **--send** checks each name, skips one that is present, creates the rest, and reads each back.
  A name it cannot confirm is a FAIL and the exit status is 1.
- **Safety:** each payload is screened for order and desktop tokens, and for `Reset`, before the
  socket opens. The login is the harness's watch-mode login on the paper account. `SCRIPT`
  runs as whatever account DAS itself is logged into, so the screen is the real guard.
- **Plan file** (JSON) belongs in the gitignored `scripts/local/`, because a game plan is
  private:

  ```json
  {"prefix": "K0102",
   "alerts": [{"symbol": "ABCD", "tag": "LONG",     "level": 101.25, "op": ">="},
              {"symbol": "WXYZ",  "tag": "PRIOR_LO", "level": 50.07, "op": "<="}]}
  ```

  `field` is optional: `L1 LAST` by default, `L1 BID` or `L1 ASK` allowed.

**Do not** check an alert with `eval` (`das_script_test.py eval GLOBALSCRIPT 'GetAlertObj("X").Symb'`).
That is the call that froze the API on 11-19. Use `das_alerts.py check`.

## Which way the operator points

A price alert fires when the condition becomes true. Choose the operator from where the level
sits against the current price: `>=` for a level above, `<=` for a level below. That is the
rule `tools/hvc/das_out.alert_payloads` applies automatically. An alert set on the wrong side
is already true and fires at once **[I]** (drill 6 measures this).

## Practice drills

Run them in order. Drills 1 to 4 are reads, or create only what you name. Drills 5 to 7 change
DAS state and are for a quiet moment, not the open. Paper account only.

1. **Preflight.** `das_script_test.py doctor --connect`. All lines `ok`. A FAIL on the DAS
   process line means `DAS_ROOT` in `~/.claude/.env` points at a different install from the
   one running.
2. **Audit.** `das_alerts.py log`. It lists every alert created today, every read-back, and
   every alert error, from the log file alone.
3. **Read back.** `das_alerts.py check "<a name from the audit>" "K0000 NO SUCH 1.00"`.
   Expect `present`, then `missing`, and no dialog.
4. **Dry run a plan.** Write `scripts/local/alerts-today.json` from the game plan, then run
   `plan … ` without `--send`. Read every operator against the current price.
5. **Create and confirm.** Run `plan … --send`. Expect `created` for the new names and
   `present` for any the game plan already made. Run it again: all `present`, nothing sent.
6. **Trigger (UNVERIFIED, run once).** Create a deliberately true alert, for example
   `add SPY DRILL 1.00 --op ">=" --send`. Then record what DAS does:
   - Is there a sound, a speech line, or a popup?
   - Does the log gain a line, and in what form?
   - Does `check` still find it after it fires?
   Write the answers in the table above. This drill decides whether a program can learn
   about a trigger from the log.
7. **Restart (UNVERIFIED).** Restart DAS and run `das_alerts.py check` on today's names.
   This decides whether alerts survive a restart, and so whether the morning plan must
   re-run `plan --send` after one.

## Not known yet

- Whether a fired alert writes anything to the DAS log (drill 6).
- Whether alerts survive a DAS restart, and where DAS keeps them (drill 7).
- How to delete one alert. `Reset` removes "alerts" in a number nobody has measured. Delete
  a drill alert by hand in Tools → Alert & Trigger.
- What a second `save()` under the same name does: replace, or duplicate. `--send` avoids the
  question by checking first.
- Whether `AddItem` takes several conditions in one alert, like the Alert window's
  "Multiple conditions" [D user manual], or the `Code` column of the sample `Alert.xml`.

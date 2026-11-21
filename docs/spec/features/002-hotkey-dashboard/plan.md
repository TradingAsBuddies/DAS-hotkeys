# 002 — Hotkey dashboard: plan for automating its creation

**Status: draft, 2026-11-19.** Spec: `spec.md`. Findings read from the running install
`C:\Cobra Trading_x64-NEW` (build 5.8.4.8) on 2026-11-19, read-only.

## What a script can and cannot build

| Piece | Can it be generated? | Evidence |
|---|---|---|
| A hot button | **No**, not by script | **[V]** 2026-11-18 probe: no command creates one (WISDOM) |
| A button's face (text, colours) | Yes, at runtime | **[V]** `GetCustButObj` writes, `dash_box` |
| Hotkeys | **Yes, as a file** | **[V]** `Hotkey.htk` is plain text (below) |
| A whole desktop with its windows and buttons | Load yes, generate no | **[D]** `SwitchDesktop XXLayout` opens `XXLayout.dsk` (das-hotkeys-guide p.18); `.dsk` is binary |
| A copy of a window with its buttons | Yes, at runtime | **[D]** `DuplicateWindow` copies a montage or chart "including its hot buttons and scripts" (hot buttons guide p.11–12) |

## The `.htk` format, verified

`Config.cfg` names the file: `HOTKEY:FILE:Hotkey.htk`. The file is CRLF text, one record per
hotkey:

```
Key:Name:Script                       short script on one line
Key:Name:~ NNN:Script…                long script, length-prefixed
```

An empty `Key` is a hotkey with no key bound, which a button can still run with `ExecHotkey`.
Inside a prefixed record, `~`, control characters and every byte above 0x7E are stored as `~XX`
in upper-case hex: a typed line break is `~0D~0A`, and an em dash is `~E2~80~94` (its UTF-8
bytes). **`NNN` counts the script's characters, with each escape counting as one, and not
counting the CRLFs DAS inserts to wrap the record.** A wrap follows the token that brings the
line to 51 or more raw characters, and an escape is never split. Scripts of 95 characters or
fewer without an escape use the short form, and scripts of 124 or more use the prefixed form.
No script between those lengths was seen.

**[V]** 2026-11-19: `tools/gen_htk.py selftest` parses and rewrites all eight `.htk` files in
both installs byte for byte, 62 prefixed records among them, including a 2,744-character
script with `~7E` and UTF-8 escapes. Still unknown: whether DAS needs the wraps when it reads.
The generator writes them, so the question only matters for hand-edited files.

## Where buttons live

Not in `Config.cfg`. Not in any text file: `dash_box` appears nowhere in the install outside
`LOG/` **[V]**, and both `.dsk` desktops are binary (`DTSFILE` header, build string, login
ID, fixed-width window records with script text embedded as ASCII). The inference is that
buttons are saved per window inside the `.dsk` when the desktop is saved, and `dash_box` has not
been saved yet **[I]**. Generating `.dsk` bytes is ruled out. The format is undocumented,
versioned, and carries the login ID.

## Recommended path: template once, generate the logic, clone at runtime

1. **The logic is generated.** `tools/gen_htk.py build scripts/htk/dashboard.json` writes the
   dashboard scripts from `scripts/*.das` (a whole file, or one `// BLOCK X` section) into
   `scripts/local/dashboard.htk` as no-key hotkeys named `dash.baf_long`, `dash.baf_short`, and
   so on. It strips comments, keeps line breaks, and runs the static checks of
   `das_script_test.py check` first. The full checker (feature 001) replaces those checks when it
   exists. `--base Hotkey.htk` keeps the operator's existing records and replaces only those
   with the same name, because loading a file may replace every hotkey. BUILT 2026-11-19; the
   manifest holds BAF LONG and BAF SHORT. The roadmap already lists this (*Next*, item 4). The operator loads the file once in
   Setup > Hotkey > Load (das-hotkeys-guide p.2), or swaps `HOTKEY:FILE` while DAS is closed.
2. **The buttons are made by hand, once, and stay thin.** One montage, ten buttons, named per
   `spec.md`. Each button's script is one line, `ExecHotkey("dash.baf_long");`. A change to the
   logic is then a regenerated `.htk`, never a button edit. Display buttons get no script.
3. **The template is saved and cloned.** File > Save Desktop keeps it. A second montage
   gets `DuplicateWindow` plus a rename, and a different strategy's set is a different saved
   desktop reached with `SwitchDesktop`.
4. **The faces are fed.** `four_box_feeder.py` becomes the general dashboard feeder: one
   GLOBALSCRIPT write per cycle paints every tile and sets the gate globals (`spec.md`, *The gate*).
   The systemd service already exists.
5. **Per strategy, a manifest.** A small YAML or JSON file per strategy (FL, 34-SMA, bracket)
   lists its buttons, their hotkey names and its tiles. The generator reads it, writes the
   `.htk`, and prints the checklist of buttons to create by hand: name, label, and the one-line
   script. That checklist is the only manual step left, and it is done once per template.

## Live tests, in order (paper account only)

| # | Question | Pass |
|---|---|---|
| L1 | After File > Save Desktop, does `dash_box` appear in `default.dsk`? | The name is in the file: buttons live in the desktop |
| L2 | Does a DAS restart keep a face the feeder wrote? | Expected no; the feeder repaints within 60 s |
| L3 | Does a generated `.htk` load without wraps, and with them? | No error dialog; scripts listed |
| L4 | Does `ExecHotkey("dash.x")` from a button run a no-key hotkey? | A `MsgLog` line from inside it |
| L5 | Does a global set by GLOBALSCRIPT reach a montage button's script? | The button logs the value |
| L6 | Does `DuplicateWindow` keep button names that `GetCustButObj` finds? | A guarded write to the copy logs ok |
| L7 | Does `SwitchDesktop` from a script or `Exec` switch desktops? | The named desktop opens |
| L8 | After a DAS restart, does `%TRADE` still list the session's earlier fills? | Fills from before the restart appear |

The generated `.htk` goes to the gitignored `scripts/local/`. The operator's own `Hotkey.htk`
holds `ACCOUNT=` strings and never enters the repo (CONSTITUTION §16).

L1, L2 and L5 decide the design. The rest decide how much of the manual step can go.

## Not doing

- Writing `.dsk` bytes.
- UI automation of the button dialog. pywinauto can click it, but a dialog script that clicks
  through DAS setup forms is fragile, and a button is made once per template.

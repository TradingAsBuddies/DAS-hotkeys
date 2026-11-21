# Hotkey forum: from pattern to working button

Operator rule, 2026-11-18. When a trading pattern should be a **hotkey**, a **chart button** or a
**montage button**, it gets a forum topic. This project builds it, the cluster hears what it does,
and the same topic collects every bug and success story after that.

## Lifecycle
1. **Propose.** Open one forum topic per pattern:
   `hotkey_forum.py propose <slug> --kind hotkey|chart-button|montage-button --title "…" --file body.md`
   Use the body template below.
2. **Build here.** Write the script in `scripts/` under the constitution: paper account only
   (§1.1), every entry with a stop or a logged NOSTOP (rule 3), and no ATR means no entry (rule 4).
   Grammar is in `docs/spec/grammar.md`.
3. **Post the build.** `hotkey_forum.py post <slug> --tag BUILD --file …` with the script and how to load it.
4. **Report to the cluster.** `hotkey_forum.py cluster <slug> "what it does now"` posts to Slack #falcon-cluster.
5. **Keep the topic alive.** Post `--tag BUG` for a defect (exact DAS response, build version),
   `--tag WORKS` for a verified success (what was tested and where), and `--tag NOTE` for
   anything else. The **same thread** keeps the history; never open a second topic for one pattern.

## Proposal body template
```
Pattern:   what the tape does, and the playbook it belongs to
Where:     hotkey (key) · chart button (window) · montage button (window)
Trigger:   what the trader sees before pressing it
Action:    what the script must do, step by step (entry, stop, size rule)
Safety:    stop rule, size rule, refusals (no ATR, wrong account, no position)
Source:    review / video / session where the pattern was seen
```

## Public content only
The forum is public, like this repo. Post scripts and behavior, never account IDs, dollar
figures, share counts tied to an account, webhooks or channel IDs. The tool refuses account IDs
and `$` figures. The webhook lives in the private `.env` as `DISCORD_DASHOTKEY_FORUM`. The
slug → thread registry lives in the private LifeOS tree, not in this repo.

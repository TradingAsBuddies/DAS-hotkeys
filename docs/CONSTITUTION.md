# Constitution

The rules that do not change from task to task. A change to this file is its own commit with
its own reason.

## 1. Money

1. Automation touches **one account: TR4425, the paper account**. Any tool that logs in
   refuses every other account string unless overridden on purpose with an environment
   variable, and the override is never the default.
2. **No dry run of an order script exists.** Text injected through the CMD API executes
   inside DAS under DAS's own session. A script that can send an order is tested by sending
   the order, on the paper account, with a far-off limit and a cancel plan.
3. Every entry carries a stop from the same script that entered, or the script logs
   `NOSTOP` and stops. A position with no stop is a defect, not a state.
4. **No ATR, no entry.** A stop distance derived from a default constant is forbidden
   (`fl_monitor_spec.md` invariant I-1, learned from the 2026-05-29 incident).
5. Flatten works at any hour. `Panic` refuses outside market hours, so the primary close is
   per-symbol limit orders; `Panic` is a fallback, never the plan.

## 2. Evidence

6. **Never assert what has not been observed.** "Verified" means a log line, a socket
   reply, or a screenshot exists and is cited. "Documented" means a manual page is cited.
   Everything else is labelled unverified in the file that depends on it.
7. The DAS log file is the ground truth for what a script did. The socket is the ground
   truth for what the API said. Timestamps come from the exchange, never from the host
   clock.
8. A backtest result is reported with its fidelity caveats attached, in the same file.
9. When the manual and the build disagree, the build wins and the disagreement is recorded
   in `WISDOM.md` with the date.

## 3. Code

10. Scripts obey DAS: no single quotes, no `&&` / `\|\|`, no user functions, nested `if`,
    `SetPopOut Y` before `WPos` / `WSize`, `Wait()` after `NewWindow`, one `Send()` per
    second, `MsgLog` not `MsgBox` in anything that may be injected.
11. Windows are addressed by name. `GetWindowObj()` without an argument is not trusted.
12. Per-chart state lives on the chart's `data` object; globals hold operator settings only.
13. Tools read the host and port from the environment and cross-check the port against
    DAS's own configuration. Nothing is hardcoded, nothing is derived from a routing table.
14. A connection failure is reported as a connection failure, never as "no data".
15. Surgical changes. A fix touches the broken line, not the component around it.

## 4. Repository

16. The repository is public. It never contains DAS manuals, the CMD API specification,
    credentials, live account identifiers, or private links.
17. Every change ships as a small increment with its own commit message stating what and
    why. Releases are tags with notes.
18. Every script explains, in its header, what it does, where it is installed, what it
    assumes, and what is unverified.
19. Reviews happen before a tag. A finding that touches money or safety blocks the tag.

## 5. Process

20. Forward tests run against the day's published gameplan and produce one dated results
    file with a verdict, whether or not the verdict is good.
21. The roadmap is updated in the same increment that finishes an item.
22. When a rule here is broken, the fix is a rule change or a code change, recorded, not a
    quiet exception.

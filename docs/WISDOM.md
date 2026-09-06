# EXTRACT WISDOM: The DAS Trader Manual Corpus
> 20 official DAS manuals, 243 pages, read for one purpose — what does it actually take to script variables, montage alignment, and chart alignment?

**A note on voice.** ExtractWisdom is tuned for talks and interviews, where the wisdom is what someone *said*. Here the wisdom is what the syntax *permits*, so the bullets carry real code. Everything below is quoted or derived from the manuals in `docs/manuals/`, cited by file.

---

## DAS Has a Real Programming Language Hiding Behind the Hotkey Dialog

- The thing labeled "hotkeys" is a scripting language with variables, objects, `if`/`while`, and comments. Nothing in the name suggests that.
- It ships **off**. Setup → Other Configuration → *Hotkey Advanced Script*. Until you flip it, none of what follows exists.
- Two tiers, and they're easy to confuse. Basic command script is `ROUTE=LIMIT;Price=10;Share=100;BUY;` — flat, left to right. Advanced adds `$variables` and objects on top.
- The one-liner from the Getting Started page is the whole pitch: `$Account="TRTEST";Price=BID;Share=GetAccountObj($Account).BP/3/Price;Buy;` — position sized to a third of buying power, computed at press time.
- Scripts run from three places, not one: hotkeys, toolbar buttons, and a **Desktop Load Script** that fires on DAS startup with no key press at all.
- There is a **Timer Event** that re-runs your script every second. That is a polling loop inside the platform, and it changes what "hotkey" means entirely.

*Sources: das-advanced-hotkey-guide.pdf pp.3–5, 18, 35; das-hotkey-and-command-script-user-guide.pdf pp.1–2*

## Variables Are Global, Case-Blind, and Can Name Each Other

- Every user variable is global and starts with `$`. Object-owned properties don't. That `$` is the entire namespace distinction.
- **`SAM` and `sam` are the same variable.** Case-insensitive. Pick a naming convention early or you will collide with yourself.
- Four types: Integer, Float, String, Object. Math works as expected, with normal precedence — `$MyInteger*2+$MyNumber/$MyInteger` evaluates `*` and `/` first.
- The sharpest trick in the FAQ, buried on the last page: you can compute a variable's *name*.
  ```
  $VAR1 = "MSFT" + "_LONG";
  SetVar($VAR1, 100);        // creates $MSFT_LONG = 100
  ```
  That is a per-symbol state table built out of nothing but string concatenation. For a multi-ticker script, this is the pattern.
- `GetVar(name)` / `SetVar(name, value)` / `DelVar(a, b, …)` complete the set. `DelVar` matters — global state persists, so scripts leak.
- There's a **Hotkey Script Variable** window that shows every live global. Your debugger.

*Sources: das-advanced-hotkey-guide.pdf pp.3–4, 7, 39–40*

## You Cannot Move a Window Until You Pop It Out

This is the single most important line in the corpus for your montage and chart alignment goal, and it's a footnote repeated a few dozen times in the hotkeys guide:

> "Note: WPos and WSize can only be used with windows that pop out."

- The alignment primitives are `Wpos X Y` (move), `Wsize W H` (resize), and `GetRect` (read top-left and bottom-right back). Real geometry, readable and writable.
- All three are inert on docked windows. The sequence is always **`SetPopOut Y` first**, then position.
- The full opening pattern is one line: `NewWindow Chart; SetPopOut Y; WPos 1920 0; WSize 800 600;`
- `MoveWindowToCursor` and `MovePopoutWindowToCursor` exist for mouse-relative placement. `AlwaysOnTop` and `TitleBar Y|N` finish the layout controls.
- Layout persistence is separate: `SaveLayout` overwrites the current layout, `SaveDesktop` writes the desktop file, `SwitchDesktop` restores default, `ClearDesktop` wipes the front end.

*Sources: das-hotkeys-guide.pdf pp.14–16; das-advanced-hotkey-guide.pdf pp.8–9*

## Every Window Becomes an Object the Moment You Name It

- Right-click a window's title bar, give it a unique name, and `GetWindowObj("thatName")` hands you a handle. That's the whole mechanism.
- **Names must be unique.** Two windows sharing a name and DAS cannot resolve either. The manual asks for this explicitly.
- `GetWindowObj()` with no argument returns the most recently created window — which makes create-then-configure a clean two-liner:
  ```
  NewWindow Montage;
  $m = GetWindowObj();
  $m.name = "montageWindow";
  $m.SYMBOL = "TSLA";
  ```
- Montage exposes `BID ASK L2BID L2ASK ISBBID ISBASK LAST HI LO OPEN PCL POS Price Share SSARE TOGSSARE ROUTE DEFSHARE SHARECAP STOPTYPE STOPPRICE`. Read *and* write — setting `.PRICE`, `.share`, `.route` then calling `.BUY` sends an order.
- `FocusWindow name` is the crude alternative: force focus, then run unqualified commands against whatever is focused. The manual quietly tells you not to prefer it — *"it may be better to use GetWindowObj() to manipulate the objects rather than FocusWindow."*
- Window names survive restart **only if you save the desktop afterward**. Otherwise your Desktop Load Script references a name that no longer exists.

*Sources: das-advanced-hotkey-guide.pdf pp.9, 11–13, 19–21, 35*

## Window Linking Is the One Thing You Can't Fully Script

- `LinkTo` and `Unlink` are in the Window Object command list, which makes them look scriptable. They aren't, not really.
- Both require **holding the left mouse button down** while the hotkey fires — the script starts an anchor-drag, and a human finishes it. Any mouse click aborts the operation mid-flight.
- So "montage alignment" splits cleanly in two: **geometry is fully automatable** (`WPos`/`WSize`/`GetRect`), **symbol-linkage is not**. Plan around that boundary rather than fighting it.
- Windows also carry a `LinkColor` property, and DAS has a color-based linking model documented in the HTML knowledge base — that path may script better than the drag anchor. Worth testing before committing to a design.

*Sources: das-hotkeys-guide.pdf p.11; das-advanced-hotkey-guide.pdf pp.9, 14*

## Chart Alignment Is a Trendline Problem, Not a Geometry Problem

- The interesting alignment on charts isn't window position. It's making the same levels appear on every chart of the same symbol.
- `TrendLineToGlobal` promotes selected trendlines so they render in **all** chart windows on that symbol. `TrendLineToGlobalTF` restricts that to charts on the same timeframe. `TrendLineToLocal` demotes back.
- `SaveGlobalTrendlines` and `LoadGlobalTrendlines` persist the set to file — which is the hook for generating levels externally and loading them in.
- Scripted drawing works too: `DrawHorzLineWithPrice(price, color)` with either `Color("RED")` or `Color(100,100,100)`. `RemoveAllTrendLines` clears them.
- The cross-window example in the guide is worth copying wholesale — it reads a price out of the montage and draws it on the chart:
  ```
  FocusWindow myMontage;
  $currBid = BID;
  FocusWindow myChart;
  DrawHorzLineWithPrice($currBid, COLOR("RED"));
  ```
- Chart data is readable, not just drawable: `GetStudyVal("vwap")` returns a named study's last value, `GetBar(-5)` returns the fifth-last bar as an object, `GetMousePtPrice()` returns the price under the cursor.
- Study names come from the Study Configure window and are yours to set. `HideStudies "Move*"` accepts wildcards — name your studies deliberately and you get scriptable groups for free.

*Sources: das-hotkeys-guide.pdf pp.15–16; das-advanced-hotkey-guide.pdf pp.6, 36–37*

## The Limits That Will Bite You

- **`while` loops cap at 200 iterations.** Hard ceiling, stated as dead-loop protection. Any iteration over a large symbol list has to be chunked.
- **One `Send()` per second.** Stated flatly: *"We can only send() one order per second due to current restrictions."* Any basket or scale-out logic must pace itself.
- **`GetQuoteObj("TSLA")` returns all zeros unless TSLA is already open in a montage window.** The quote object reads the front-end's subscription, not the server. This will look like a broken script when it's a missing subscription.
- Quote data doesn't refresh on its own inside a script. You need the Timer Event, and the variable itself needs a refresh interval configured (right-click → config → 1 second).
- The Timer Event has a genuinely good safety valve: if a script blocks on input and you don't respond for 5 seconds, the timer stops. Otherwise a `MsgBox` in a timer would be unkillable.
- Chart alert scripts need quoted operators — `AlertOperator="<="`, not `AlertOperator=<=`. Called out as a note, easy to miss.
- Order property names have **no short forms**. `"D+"` works inside the order string; the `.TIF` property wants `DAY`. Mixing them fails quietly.
- Setting `.route` without also setting `.type` is called out as a live foot-gun: *"Only changing the route and not type can lead to unexpected results!"*
- `Send()` must be called **after** every property assignment, never before.

*Sources: das-advanced-hotkey-guide.pdf pp.5, 7, 15, 18, 22, 27–28; das-hotkey-and-command-script-user-guide.pdf p.7*

## You Get Structs and Arrays, Just Not Where You'd Look

- `NewUserObj()` creates an arbitrary property bag. Assign whatever you want to it.
- `.Set(key, value)` / `.Get(key)` accept **numeric** keys, which plain dot-notation refuses. `$obj.1 = 20` is a syntax error; `$obj.Set(1, 20)` works. That distinction is the whole reason arrays are possible:
  ```
  $arr = NewUserObj();
  $i = 0;
  while ($i < 10) { $arr.Set($i, $i); $i = $i + 1; }
  ```
- `.Del(key)` removes one entry, `.Del("*")` empties the object.
- The genuinely clever bit: **every QuoteObject has a `.data` slot you can hang your own object on.** Per-symbol strategy state, stored on the symbol itself:
  ```
  $q = GetQuoteObj("TSLA");
  $q.data = NewUserObj();
  $q.data.strategy   = "opening range";
  $q.data.stopPrice  = $q.BID;
  $q.data.enterPrice = $q.BID - 2;
  ```
- `ShowObject()` on anything dumps its full property list with read/write flags. Use it constantly — it's the only introspection you get, and it's how you discover that most quote properties are read-only.

*Sources: das-advanced-hotkey-guide.pdf pp.14–17, 29–33*

## There Are No Functions, So Everything Routes Through Exec()

- Stated without apology: *"DAS does not allow users to define their own functions."*
- The substitute is string-as-code. Build script text into a variable, then run it:
  ```
  $S1 = "Share=Share+100;";
  $S2 = "Price=Price+0.01;";
  Exec($S1, $S2);
  ```
- Better structure: define named hotkeys with **no key binding at all**, then call them like subroutines with `ExecHotkey("name1", "name2")`. That's your module system.
- `GetHotkeyScript("name")` returns a hotkey's source as a string — so scripts can read, compose, and re-execute each other.
- Quote escaping inside `Exec` is manual: `Exec("MsgBox(\"Hello World\")");`
- `Input("prompt")` prompts the user at runtime, and `exec(Input())` will execute whatever they type. Powerful, and exactly as dangerous as it reads.

*Sources: das-advanced-hotkey-guide.pdf pp.37–40*

## Utilities Worth Knowing Before You Reinvent Them

- `Round(value, precision)` has two magic precisions: **100 rounds down to even lots, 101 rounds to nearest even lot.** Share-size math is already solved.
- `GetAccountObj(name)` exposes `BP`, `NBP`, `Equity`, plus a real bulk-cancel: `$acc.CancelOrder("BUY|P<", "MSFT", 324.1)` cancels every MSFT buy priced under 324.10. Flags combine from `BUY|SELL|FIST|LAST|P>|P<|P=|P>=|P<=`.
- `GetOrderObj()` queries live orders by `Acc, Symb, Oid, RefNum, Price, Share, First, Last` with `>`, `<`, `<=`, `>=` — e.g. `GetOrderObj("Symb=MSFT,Price>=200")`.
- Short-form orders collapse the whole thing to one line: `NewOrderObj("B 100 TSLA ARCAL L 236.8 D+").Send();` Field order is fixed: **Side Share Symbol Route OrderType OtherPrice Price TIF**.
- Anything you omit is filled from Setup → Order Templates → Default. Convenient and a trap — the manual recommends filling every field explicitly, and warns *"Please set a default route!"*
- `Speak(text)` and `PlaySound(file, device, flag)` give audible alerts, with flags for `INTRPT`, `SHARE`, `STOP`, `LOOP`. `Wait(ms)` pauses mid-script.
- `Panic ACCOUNT=TRABC` liquidates an account. It is a one-word command. Treat it accordingly.

*Sources: das-advanced-hotkey-guide.pdf pp.7–8, 10, 24–29*

---

## One-Sentence Takeaway

DAS ships a real scripting language with objects, loops, and window geometry — disabled by default, documented in one 40-page PDF.

## If You Only Have 2 Minutes

- Turn on Setup → Other Configuration → Hotkey Advanced Script. Nothing works until you do.
- `$` marks globals. They're case-insensitive and persist across scripts.
- `SetPopOut Y` before `WPos`/`WSize`. Docked windows cannot be positioned.
- Name a window by right-clicking its title bar, then grab it with `GetWindowObj("name")`.
- `GetQuoteObj` returns zeros unless that symbol is open in a montage.
- 200-iteration loop cap and one order per second. Design around both.
- `ShowObject()` on anything shows every property and whether it's writable.

## References & Rabbit Holes

- **`docs/manuals/das-advanced-hotkey-guide.pdf`** — 40 pages, updated June 2025, the newest document in the corpus. Roughly 80% of everything above comes from here. Read it end to end.
- **`docs/manuals/das-hotkeys-guide.pdf`** — 28 pages, the exhaustive command reference. Where the WPos/pop-out constraint and the trendline commands live.
- **`docs/manuals/das-hotkey-and-command-script-user-guide.pdf`** — 9 pages, the legacy basic-script guide recovered from the forum thread. Explains the pre-Advanced layer everything else builds on.
- **Prebuilt Scripts tab** — second tab of the Hotkey Script Builder. DAS ships working scripts nobody reads. Check there before writing from scratch.
- **Order Script Wizard** — third tab. Generates order script from a form; useful for learning correct field order.
- **`ShowObject()`** — the only introspection in the language. Every design session should start here.
- **Color-based window linking** — documented in the HTML knowledge base, not in these PDFs. The likely workaround for `LinkTo` needing a mouse drag. Unverified; worth a spike.
- **CMD API** — a separate surface from all of this. Certification-gated. See `docs/manuals/MANIFEST.md`.

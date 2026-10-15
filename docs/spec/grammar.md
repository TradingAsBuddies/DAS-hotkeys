# DAS hotkey script — grammar

**Status: draft, 2026-10-15.** The first chapter of the language reference planned in
`INTENT.md`. Later chapters (the built-in function library, objects and their properties,
execution contexts, limits) build on the names and productions defined here.

DAS|Inc has never published a grammar, and its parser is closed. Everything below is
reconstructed from the two DAS manuals that describe the language, from the scripts in
`scripts/`, and from **25 live probes run on 2026-10-15** (§5). Every rule says which of
those it rests on, so the reader can tell what DAS documents from what this repo observed.

## Evidence labels

| Label | Meaning |
|---|---|
| **[D adv p.N]** | Documented: *Advanced Hotkey Guide* (June 2025), page N |
| **[D hk p.N]** | Documented: *DAS Trader Hotkeys Guide* (May 2025), page N |
| **[V date]** | Verified: DAS accepted or rejected it on that date. The source is named, and the build is given when it isn't 5.8.4.4 |
| **[I]** | Inferred: it fits every documented example and every script that has run, but no test has isolated it |
| **[?]** | Open: unknown |

**Two builds.** Verifications up to 2026-09-28 ran on **5.8.2.5** (`C:\Cobra Trading_x64`).
The 2026-10-15 probes ran on **5.8.4.4 Beta** (`C:\Cobra Trading_x64-Beta`), which has
been the running install since 2026-10-07. Where the two builds disagree, §4 says so. The
manuals' examples are older than both.

Where the manual and the build disagree, the build wins (CONSTITUTION §9). The
disagreements are in [§4](#4-where-the-manual-and-the-build-disagree).

## How this grammar was checked

1. **Against DAS.** Each open question became a one-line probe injected into `montage1`
   through `tools/das_script_test.py run`, on the TR4425 paper session. None sent an order.
   §5 lists every probe and the log line it produced.
2. **Against the repo.** The EBNF in §3 was transcribed into a throwaway Lark (Earley)
   grammar. All 13 files in `scripts/` and 20 examples quoted from the manuals parse. The
   inputs DAS rejected in §5 are rejected. That parser stays out of the repo, because repo
   tools are standard-library only (`docs/TECH-STACK.md`).

## The execution model, before the syntax

**DAS executes as it parses.** Statements before a syntax error have already run by the
time the error dialog opens. `if (1==1) { MsgLog("q6") }` logged `q6` and *then* raised
`ScriptError:100 … should end with ;` [V 2026-10-15, Q6]. A script with a typo near the end
can send an order before DAS reports the typo. **Check syntax before a script reaches DAS.
DAS's own error is not a pre-flight check.**

---

## 1. Two tiers, one script

DAS script has two layers, and one script can mix them freely.

- **Basic command script** is a flat list of settings and actions:
  `ROUTE=LIMIT;Price=10;Share=100;TIF=DAY+;BUY` [D hk p.1]. Values can be raw text such as
  `DAY+` or `RT:STOP STOPTYPE:LIMIT …`, which are not expressions.
- **Advanced script** adds `$` variables, objects, function calls, `if`, `while` and
  `return` [D adv p.3–5]. It is off until *Setup → Other Configuration → Hotkey Advanced
  Script* is enabled [D adv p.3].

Where the two collide (`name = …`), the grammar reads the advanced form first and falls
back to raw text ([§3.6](#36-assignment)).

## 2. Lexical structure

### 2.1 Layout

Spaces, tabs and line breaks between tokens carry no meaning. The manuals spread
statements and long expressions across lines [D adv p.5, p.33]. The CMD API harness joins
a whole file into one line before injection, and DAS runs it [V 2026-09-24, 5.8.2.5]. Every
2026-10-15 probe was a single line, including nested `if`/`else` (§5, F5). **Layout was
never tested inside the hotkey dialog**, where scripts keep their line breaks [?].

### 2.2 Comments

```ebnf
line_comment  = "//" , { any character except line break } ;
block_comment = "/*" , { any character } , "*/" ;
```

- `//` runs to the end of the line [D adv p.5].
- `/* … */` **works**, although neither manual mentions it.
  `/* MsgLog("f2 HIDDEN"); */ MsgLog("f2 shown");` logged only `f2 shown`
  [V 2026-10-15, F2]. Only the single-line case was tested, because the API joins lines.
- A single quote inside a `//` comment survived a live run [V 2026-09-24, 5.8.2.5]. Keep
  single quotes out of comments anyway, because a tool that strips comments differently
  would expose them.

### 2.3 Identifiers and case

```ebnf
name       = letter_ , { letter_ | digit } ;
global_var = "$" , name ;
letter_    = "A"…"Z" | "a"…"z" | "_" ;
digit      = "0"…"9" ;
```

| What | Case | Evidence |
|---|---|---|
| global variables (`$SAM` = `$sam`) | insensitive | [D adv p.4] |
| window names | insensitive | [V 2026-09-24, 5.8.2.5] |
| function names (`msglog`, `MSGLOG`, `MsgLog`) | insensitive | [V 2026-10-15, F8] |
| **keywords `if` `else` `while` `return`** | **lower case only** | `IF (…)` and `If (…)` raise `Function IF not exist!` / `Function If not exist!`; `ELSE` raises `Invalid token` [V 2026-10-15, Q10, F4] |
| properties, commands | mixed case in every manual example (`$montage.share`, `$montage.PRICE` [D adv p.13]) | [I] |

A keyword in the wrong case is read as a function call, so `If (x) { … }` fails twice: once
at runtime (no function `If`) and once at parse time (no `;` after the "call").

### 2.4 Numbers

```ebnf
number = digit , { digit } , [ "." , digit , { digit } ]
       | "." , digit , { digit } ;
```

DAS has integers and decimals [D adv p.4]. No exponent or hex form is documented. Unary
minus works on literals (`GetBar(-5)` [D adv p.36]) and on variables: `$b=-$a` gave `-3`
[V 2026-10-15, Q2]. The `0 - $x` form in the repo's scripts is unnecessary.

### 2.5 Strings

```ebnf
string = '"' , { string_char | escape } , '"' ;
escape = "\" , ( '"' | "n" | "t" ) ;
```

- Strings use **double quotes only** [D adv p.17]. Inside code, a single quote is a parse
  error (`ScriptError:100`, modal dialog, API frozen until dismissed)
  [V 2026-09-24, 5.8.2.5]. This was not re-tested on 5.8.4.4.
- `\"` is an embedded quote [D adv p.37], `\n` a newline [D adv p.33], and `\t` a tab: the log
  line carried a real TAB byte [V 2026-10-15, Q9]. Other escapes are untested.
- The PDFs print many examples with typographic quotes (`“TRTEST”` [D adv p.3, p.10,
  p.40]). That is an artefact of the PDF typesetting. Type straight `"`.
- Assigning `""` to a variable leaves the variable **unregistered**. A later read logs
  `ScriptError:1 variable … not exist! use value 0 instead` [V 2026-09-28, 5.8.2.5].
  Comparing against `""` is fine.

### 2.6 Operators and punctuation

| Token | Use | Evidence |
|---|---|---|
| `=` | assignment | [D adv p.39] |
| `+ - * /` | arithmetic; `+` also concatenates strings | [D adv p.4, p.13]; [V 2026-10-15, P3] |
| `== != < > <= >=` | comparison | `==` `<` [D adv p.5, p.31]; all six [V 2026-10-15, Q12, P7] |
| **`&&` `\|\|`** | logical and/or | [V 2026-10-15, F1]: both evaluate correctly; **not in either manual** |
| `!` | logical not | [V 2026-10-15, Q11, P2] |
| `-` (prefix) | negation | [D adv p.36]; [V 2026-10-15, Q2] |
| `( ) { } . , ;` | grouping, blocks, member access, argument lists, statement end | [D adv p.4–5] |

`%`, `+=` and `++` are undocumented and unused. `%` appears only *inside* order short-form
strings (`"B 100 TSLA TL 1% D+"` [D adv p.28]).

---

## 3. Syntax

### 3.1 The grammar

W3C-style EBNF. `[ x ]` is optional, `{ x }` repeats zero or more times, and `|` separates
alternatives. Keywords are lower case. Other names are matched case-insensitively (§2.3).

```ebnf
script         = { statement } , [ simple ] ;                (* last ";" optional *)

statement      = if_stmt
               | while_stmt
               | simple , ";"
               | ";" ;                                       (* empty statement *)

block          = "{" , { statement } , "}" ;                 (* every ";" required *)

if_stmt        = "if" , "(" , expression , ")" , block ,
                 [ "else" , ( if_stmt | block ) ] ;

while_stmt     = "while" , "(" , expression , ")" , block , [ ";" ] ;

simple         = return_stmt
               | assignment
               | call_stmt
               | member_command
               | command ;

return_stmt    = "return" ;

assignment     = lvalue , "=" , expression
               | name , "=" , raw_value ;                    (* basic tier, §3.6 *)

lvalue         = global_var
               | name                                        (* property of the focused window *)
               | postfix , "." , name ;

call_stmt      = postfix , "(" , [ arguments ] , ")" ;

member_command = postfix , "." , name ;                      (* $montage.BUY *)

command        = name , [ raw_args ] ;                       (* NewWindow Chart *)

expression     = logical ;
logical        = comparison , { ( "&&" | "||" ) , comparison } ;   (* ONE level, left to right *)
comparison     = additive , { rel_op , additive } ;                (* chains, left to right *)
additive       = term , { ( "+" | "-" ) , term } ;
term           = unary , { ( "*" | "/" ) , unary } ;
unary          = ( "-" | "!" ) , unary
               | postfix ;
postfix        = primary , { "." , name | "(" , [ arguments ] , ")" } ;
primary        = number | string | global_var | name | "(" , expression , ")" ;
arguments      = expression , { "," , expression } ;
rel_op         = "==" | "!=" | "<=" | ">=" | "<" | ">" ;

raw_value      = raw_char - white_space , { raw_char } ;
raw_args       = raw_char - ( white_space | "=" | "(" | "." ) , { raw_char } ;
raw_char       = any character except ";" | "{" | "}" | line break ;
```

### 3.2 Statements and `;`

- A `;` ends each statement [D adv p.4: "Separate commands must end with a ;"].
- The **last statement of a script** may leave it out: `…;TIF=DAY+;BUY` [D hk p.1];
  `MsgLog("f9 a"); MsgLog("f9 b")` ran both [V 2026-10-15, F9].
- **Inside a block, every statement needs its `;`**, the last one included.
  `{ MsgLog("q6") }` and `{ $f3=7 }` are both `ScriptError:100` [V 2026-10-15, Q6, F3]. The
  manual's `$abc=1` directly before `}` [D hk p.24] fails as printed.
- No `;` is needed after a closing brace.

### 3.3 `if` / `else`

```
if ($abc==1) {
  MsgBox(" this is 1");
}else if ($abc==2) {
  MsgBox(" this is 2");
}else {
  $abc=1;
}
```

- The form and the `else if` chain are [D adv p.5, D hk p.24]. Braces are required [I].
- `else` works at any depth, including one nested on a single line:
  `if (1==1) { if ($f5 == "none") { … } else { … } }` [V 2026-10-15, F5, Q1]. §4, row 1,
  covers the 09-28 rejection that started the "no one-line else" rule.
- The condition is any expression. A bare value works (`if ($z) {…}` [V 2026-10-15, Q8]),
  and so do `&&`, `||` and `!` (§3.9).

### 3.4 `while`

`while (cond) { … }` [D adv p.5]. The hotkeys guide writes it as `while(){};`, with a
trailing `;` [D hk p.24], so the grammar allows one. **A loop runs at most 200 iterations**
[D adv p.5]. That is a runtime cap, not syntax.

### 3.5 `return`

`return;` stops the current script. In a script started by `Exec` or `ExecHotkey`, control
goes back to the caller [D hk p.25]. Nothing returns a value, and there are no user-defined
functions [D adv p.40].

### 3.6 Assignment

Three kinds of target:

| Target | Example | Evidence |
|---|---|---|
| global variable | `$MaxShare=500;` | [D adv p.5] |
| property of the focused window, unqualified | `Price=12.5; Share=300;` | [D adv p.4] |
| property through an object | `$montage.PRICE = 400;` `$q.data.stopPrice = $q.BID-2;` | [D adv p.13, p.32] |

- A property name must be a `name`. `$myObj.1 = 20` is wrong, and numeric keys go through
  `.Set(1, 20)` / `.Get(1)` [D adv p.30].
- Some properties are read-only. Writing one fails at runtime, not at parse time
  [D adv p.15].
- **An empty right-hand side is accepted by DAS and rejected by this grammar.**
  `$f7 = ;` raised no error on 5.8.4.4 [V 2026-10-15, F7]. `docs/CMD-API-TESTING.md`
  records it as a parse error, from the 5.8.2.5 period. It is never intended, so the grammar
  flags it.
- **Basic-tier raw values.** `TIF=DAY+` [D hk p.1],
  `TriggerOrder=RT:STOP STOPTYPE:LIMIT PX:0.00 …` [D hk p.8] and
  `OCO=RT:STOP … TIF:DAY+` [D hk p.9] are not expressions. When an *unqualified* name is
  assigned something that does not parse as an expression, the grammar takes everything up
  to the next `;` as raw text. How DAS itself decides between the two readings is unknown
  [I].
- **Bare words as values.** `ROUTE=LIMIT`, `$montage.route = ARCAL` [D adv p.13] and
  `SELL=Send` [D hk p.9] all parse as a `name` expression. The meaning is settled at runtime
  [I]. When the value is meant as text, quote it: `$ord.Route = "LIMIT"` [D adv p.23].
- **Operator quoting.** Advanced script must write `AlertOperator="<="`, not
  `AlertOperator=<=` [D adv p.7]. Read as an expression, `=<=` is not valid.

### 3.7 Calls and member commands

- A function call needs `()`, even with no arguments: `GetWindowObj()` [D adv p.13],
  `$ord.send()` [D adv p.23: "Send is a function, thus we need ()"].
- Calls and member access chain: `GetQuoteObj("TSLA").ShowObject();` [D adv p.14],
  `GetWindowObj($f10).GetTicker()` [V 2026-10-15, F10].
- A **member command** has no parentheses and returns nothing: `$montage.BUY;`
  `$montage.CXL;` [D adv p.13]. Syntactically it is a property access used as a statement.
- `Exec` takes script *text*. Quotes inside that text are escaped with `\"` [D adv p.37].

### 3.8 Commands

```
NewWindow Chart; SetPopOut Y; WPos 1920 0; WSize 800 600;
```

A command is a name, optionally followed by arguments, ending at `;`. It needs no `()`
and returns nothing [D adv p.5]. The arguments are **raw text, taken literally**:

| Argument shape | Example | Evidence |
|---|---|---|
| none | `BUY` · `RemoveAllTrendLines` · `GetRect` | [D hk p.1, D adv p.37, p.9] |
| bare words / numbers | `CXL ALL BUY` · `WPos 1920 0` | [D hk p.12, D adv p.9] |
| `key=value` | `PANIC ACCOUNT=myaccount` | [D hk p.13] |
| quoted string | `HideStudies "Price,Volume"` | [D hk p.15] |
| packed fields | `ConfigTrendLine HorzLine DotLine:FFB000:2` | [I, `04-fl-hotkeys.das`] |

**`$variables` are not expanded in command arguments.** `$q5="SPY"; SYMBOL $q5;` loaded the
literal symbol `$`, not SPY [V 2026-10-15, Q5]. To pass a computed argument, build the text
and run it with `Exec`, for example `Exec("LoadSetting " + $file + ";")`. That is
[D adv p.37–40] for `Exec` running built text, and untested for commands.
`02-fl-chart-update.das` uses `LoadSetting $FL_CST_ON` behind `$FL_USE_CST`, which ships
as `0`, so it has never run that way. As written, it would ask for a file named
`$FL_CST_ON`.

**How a statement that starts with a name is read.** The token after the name decides:

| Next token | Reading | Example |
|---|---|---|
| `=` | assignment | `Price=Bid-0.03` |
| `(` | call | `MsgBox("x")` |
| `.` | member access, call or member command | `GetQuoteObj("X").ShowObject()` |
| `;`, `}` or end of script | command with no arguments | `BUY` |
| anything else | command with raw arguments | `PANIC ACCOUNT=x` |

This table explains the keyword-case failure in §2.3: `IF` is not a keyword, so
`IF (1==1)` reads as a call to a function named `IF`.

### 3.9 Expressions

Precedence, from tightest to loosest. Every row is [V 2026-10-15] unless marked otherwise.

| Level | Operators | Associativity | Probe |
|---|---|---|---|
| postfix | `.name` `(args)` | left | [D adv p.14], F10 |
| unary | `-` `!` | right | Q2; P2: `!1==2` is `(!1)==2` → false |
| multiplicative | `*` `/` | left | P3: `1+2*3` → 7 |
| additive | `+` `-` | left | P3: `10-4-3` → 3 |
| comparison | `== != < > <= >=` | left, chains | P7: `3 > 2 > 1` → 0, i.e. `(3>2)>1`; P3: `1<2 && 3<4` → 1 |
| **logical** | **`&&` `\|\|` at the same level** | **left** | P1: `T \|\| F && F` → 0; P1b: `F && F \|\| T` → 1 |

- **`&&` does not bind tighter than `||`.** In C, Java and JavaScript it does. Here
  `a || b && c` means `(a || b) && c`. Parenthesise every mixed condition. This is the
  sharpest surprise in the language.
- A comparison produces `1` or `0`: `$c = (2 > 1)` gave `1` [V 2026-10-15, Q7].
- `/` on two integers gives a float: `7 / 2` → `3.5` [V 2026-10-15, P3].
- `+` with a string on either side concatenates and turns numbers into text
  [D adv p.13, p.31]. Other mixed-type rules (for example `"5" * 2`) are untested.
- Equality and ordering comparisons are shown at one level. No probe has separated them
  [?].

---

## 4. Where the manual, the repo and the build disagree

| # | Said | Build | Evidence |
|---|---|---|---|
| 1 | The repo's rule since 2026-09-28: "DAS rejects a one-line `} else {`" (`WISDOM.md`, `00`, `10`) | On 5.8.4.4, `else` works nested and on one line (F5 used the same shape as the rejected 09-28 line). On 5.8.2.5, `22-fl-flatten.das` (top-level `} else {`) ran live on 09-25, after the harness joined it onto one line. The 09-28 `Missing }` is unexplained: either a build difference, or something else in that script. | rejection [V 2026-09-28, 5.8.2.5, commit `3c007de`]; acceptance F5, Q1 [V 2026-10-15]; [V 2026-09-25, 5.8.2.5, XOM row of `docs/forward-tests/fl-2026-09-24-report.md`] |
| 2 | The repo: "No `&&` or `\|\|`" (README, CONSTITUTION §10, the `check` lint). The manuals are silent. | Both work and evaluate correctly, at one shared precedence level. | F1, P1, P1b [V 2026-10-15]; untested on 5.8.2.5 |
| 3 | Manual: `If ($abc==1) {` [D hk p.24] | `If` is not a keyword. The example fails. | F4 [V 2026-10-15] |
| 4 | Manual: `$abc=1` with no `;` before `}` [D hk p.24] | Every statement in a block needs `;`. | Q6, F3 [V 2026-10-15] |
| 5 | Manual quotes printed `“ ”` [D adv p.3, p.10, p.40] | Straight `"` only. `'` in code is a parse error. | [V 2026-09-24, 5.8.2.5] |
| 6 | `TSLA_QUOTE.BID` with no `$`, after assigning `$TSLA_Quote` [D adv p.16] | Reads as a property of the focused window. Almost certainly a manual error. | [I] |
| 7 | `$x = ;` is a parse error (`docs/CMD-API-TESTING.md`) | Accepted silently on 5.8.4.4 | F7 [V 2026-10-15] |
| 8 | `GetWindowObj()` with no argument returns the window just created [D adv p.13] | Not syntax: it returned nothing until `Wait(500)`. | [V 2026-09-20, 5.8.2.5, `WISDOM.md`] |

## 5. The 2026-10-15 probes

All probes were injected into `montage1` by `tools/das_script_test.py run`, with
`DAS_DIR="/mnt/c/Cobra Trading_x64-Beta"`, on DAS 5.8.4.4, in a session holding TR4425.
Results are the lines DAS wrote to `LOG\261015Log.txt`. `ScriptError:100` dialogs were
dismissed by the harness.

| Probe | Script | DAS logged | Settles |
|---|---|---|---|
| Q1 | `$t=0; if (1==1) { if ($t==0) { MsgLog("q1 A"); } else { MsgLog("q1 B"); } }` | `q1 A` | nested `else` parses |
| Q2 | `$a=3; $b=-$a; MsgLog("q2 ", $b);` | `q2 -3` | unary minus on a variable |
| Q3 | `if (1==1 && 2==2) { MsgLog("q3 and"); }` | `q3 and` | `&&` parses |
| Q4 | `/* x */ MsgLog("q4");` | `q4` | `/* */` parses |
| Q5 | `$q5="SPY"; SYMBOL $q5; Wait(800); MsgLog("q5 ", GetTicker());` | `q5 $` | no `$var` expansion in command arguments |
| Q6 | `if (1==1) { MsgLog("q6") }` | `q6`, then `ScriptError:100 … Function call should end with ;` | block-final `;` required; execution precedes the error |
| Q7 | `$c = (2 > 1); MsgLog("q7 ", $c);` | `q7 1` | comparison value is 1/0 |
| Q8 | `$z=1; if ($z) { MsgLog("q8"); }` | `q8` | bare value as condition |
| Q9 | `MsgLog("q9 a\tb\|");` | `q9 a<TAB>b\|` | `\t` escape |
| Q10 | `IF (1==1) { MsgLog("q10"); }` | `ScriptError:1 Function IF not exist!`, `ScriptError:100` | keywords are lower case |
| Q11 | `if (!(1==2)) { MsgLog("q11"); }` | `q11` | `!` |
| Q12 | `if (1<=1) {…} if (2>=1) {…} if (1!=2) {…}` | `q12 le`, `q12 ge`, `q12 ne` | `<=` `>=` `!=` |
| F1 | `T&&F`, `F\|\|T`, `F\|\|F`, `T&&T` as four `if`s | only `or-true`, `and-true` | `&&` `\|\|` evaluate correctly |
| F2 | `/* MsgLog("f2 HIDDEN"); */ MsgLog("f2 shown");` | `f2 shown` | block comment really comments |
| F3 | `if (1==1) { $f3=7 } MsgLog(…);` | `ScriptError:100 missing ;` | block-final `;` after an assignment too |
| F4a/b | `If (…) {…}` · `… } ELSE {…}` | `Function If not exist!` · `Invalid token` | keyword case |
| F5 | the 09-28 rejected shape, nested in an `if` | `f5 [montage1 ]` | §4 row 1 |
| F7 | `MsgLog("f7 before"); $f7 = ; MsgLog("f7 after");` | `f7 before`, `f7 after` | empty right-hand side accepted |
| F8 | `msglog(…); MSGLOG(…);` | both lines | function names case-insensitive |
| F9 | `MsgLog("f9 a"); MsgLog("f9 b")` | both lines | script-final `;` optional |
| F10 | `GetWindowObj($f10).GetTicker()` | `f10 SPY` | variables work as call arguments |
| P1 | `1==1 \|\| 1==2 && 1==2` | false | `&&`, `\|\|` same level, left to right |
| P1b | `1==2 && 1==2 \|\| 1==1` | true | (confirms P1) |
| P2 | `!1==2` | false | `!` binds tighter than `==` |
| P3 | `1<2 && 3<4`, `1+2*3`, `10-4-3`, `7/2` | `1`, `7`, `3`, `3.5` | precedence, associativity, division |
| P7 | `1 + 1 == 2`, `3 > 2 > 1` | true, `0` | comparison chains left to right |

`montage1` was put back on LQDA after Q5 (`q5 restored LQDA`). Sixteen seconds later the
quote server reconnected, its only reconnect that day apart from startup. Subscribing the
junk symbol `$` may have caused it; that is unconfirmed.

**Still open.**
- Line layout in the hotkey dialog (§2.1, §4 row 1). The API cannot test it, because
  everything arrives on one line.
- Whether equality and ordering comparisons share one precedence level.
- Escapes beyond `\" \n \t`.
- Single quotes and `&&`/`||` on 5.8.2.5, if that install is used again.

## 6. What builds on this

- **Language reference.** The next chapters are built-ins and commands (adv pp.7–9), the
  object model (adv pp.9–17, 21–36), execution contexts (hotkey, hot button, Chart Script,
  Timer Event, Desktop Load Script) and limits.
- **`dastrader-mode`.** Font-lock comes from §2: `//` and `/* */` comments, `"` strings with
  `\` escapes, `$` globals, the four lower-case keywords, and the operators of §2.6.
  Indentation follows the brace structure of §3.
- **A stdlib checker in `tools/`.** Because DAS executes before it rejects (see *The
  execution model*), a pre-flight parser for §3 is a safety tool, not a convenience. It
  would replace the regex lint in `das_script_test.py check`, which today catches only
  single quotes and unparenthesised `&&`/`||` mixes. It is also the parser that `.htk` generation (roadmap item 4) needs.

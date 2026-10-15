# DAS hotkey script — grammar

**Status: draft, 2026-10-15.** The first chapter of the language reference planned in
`INTENT.md`. Later chapters (the built-in function library, objects and their properties,
execution contexts, limits) build on the names and productions defined here.

DAS|Inc has never published a grammar, and its parser is closed. Everything below is
reconstructed from the two DAS manuals that describe the language, from the scripts in
`scripts/`, and from what DAS did when those scripts ran. Every rule says which of those
it rests on, so the reader can tell what DAS documents from what this repo observed or
assumed.

## Evidence labels

| Label | Meaning |
|---|---|
| **[D adv p.N]** | Documented: *Advanced Hotkey Guide* (June 2025), page N |
| **[D hk p.N]** | Documented: *DAS Trader Hotkeys Guide* (May 2025), page N |
| **[V date]** | Verified: DAS accepted or rejected it on David's build (5.8.x, Cobra) on that date; the source is named |
| **[I]** | Inferred: it fits every documented example and every script that has run, but no test has isolated it |
| **[?]** | Open: unknown. Each one has a test in [§5](#5-open-questions-and-how-to-settle-them) |

Where the manual and the build disagree, the build wins (CONSTITUTION §9). The
disagreements are listed in [§4](#4-where-the-manual-and-the-build-disagree).

## How this grammar was checked

The EBNF in §3 was transcribed into a throwaway Lark (Earley) grammar and run against:

- all 13 files in `scripts/` — all parse;
- 20 examples quoted from the two manuals, with their pages listed in §3 — all parse;
- 6 inputs DAS rejects or the manual calls wrong (`&&`, `||`, a single-quoted string,
  `$obj.1 = 20`, a missing `;` between statements, `$x = ;`) — all rejected.

That parser is not in the repo, because repo tools are standard-library only
(`docs/TECH-STACK.md`). Passing it shows the grammar is consistent with the evidence.
It does not show the grammar is DAS's.

---

## 1. Two tiers, one script

DAS script has two layers, and one script can mix them freely.

- **Basic command script** is a flat list of settings and actions:
  `ROUTE=LIMIT;Price=10;Share=100;TIF=DAY+;BUY` [D hk p.1]. Values can be raw text such as
  `DAY+` or `RT:STOP STOPTYPE:LIMIT …`, which are not expressions.
- **Advanced script** adds `$` variables, objects, function calls, `if`, `while` and
  `return` [D adv p.3–5]. It is off until *Setup → Other Configuration → Hotkey Advanced
  Script* is enabled [D adv p.3].

The grammar handles both. Where the two collide (`name = …`), it reads the advanced form
first and falls back to raw text ([§3.6](#36-assignment)).

## 2. Lexical structure

### 2.1 Layout

Spaces, tabs and line breaks between tokens carry no meaning. The manuals spread
statements and long expressions across lines [D adv p.5, p.33]. The CMD API harness joins
a whole file into one line before injection, and DAS runs it [V 2026-09-24,
`docs/CMD-API-TESTING.md`]. Inside command arguments a line break ends the argument text
(§3.8). One layout-related rejection is still unexplained; see §4, row 1.

### 2.2 Comments

```ebnf
comment = "//" , { any character except line break } ;
```

A `//` comment runs to the end of the line [D adv p.5]. Neither manual documents a block
comment form, so `/* … */` is not part of this grammar [?, Q4]. A single quote inside a
comment survived a live run [V 2026-09-24]. Keep single quotes out of comments anyway,
because a tool that strips comments differently would expose them.

### 2.3 Identifiers and case

```ebnf
name       = letter_ , { letter_ | digit } ;
global_var = "$" , name ;
letter_    = "A"…"Z" | "a"…"z" | "_" ;
digit      = "0"…"9" ;
```

- A `$` prefix marks a global variable. Object properties carry no prefix [D adv p.4].
- **Global variable names are case-insensitive**: `SAM` and `sam` are one variable
  [D adv p.4].
- Window names are case-insensitive too [V 2026-09-24: `Hidden_Chart1` and `HIDDEN_CHART1`
  both reached `hidden_chart1`].
- Keywords, functions, properties and commands appear in mixed case throughout the manuals:
  `If`/`if` [D hk p.24], `newUserObj`/`NewUserObj` [D adv p.29, p.31], `exec(Input())`
  [D adv p.39], `$montage.share`/`$montage.PRICE` [D adv p.13]. This grammar treats every
  name as case-insensitive [I]. For keywords specifically, that is still open [?, Q10].
- Keywords are `if`, `else`, `while` and `return` [D adv p.5]. Nothing documents whether
  they are reserved when used as property names.

### 2.4 Numbers

```ebnf
number = digit , { digit } , [ "." , digit , { digit } ]
       | "." , digit , { digit } ;
```

DAS has integers and decimals [D adv p.4]. No exponent or hex form is documented. A negative
value is unary minus applied to a number: `GetBar(-5)` [D adv p.36]. Unary minus on a
variable or call has not been tested. The repo's scripts write `0 - $x` instead
[?, Q2].

### 2.5 Strings

```ebnf
string = '"' , { string_char | escape } , '"' ;
escape = "\" , ( '"' | "n" ) ;
```

- Strings use **double quotes only** [D adv p.17]. Inside code, a single quote is a parse
  error (`ScriptError:100`, modal dialog, API frozen until dismissed)
  [V 2026-09-24, `docs/CMD-API-TESTING.md`].
- `\"` is an embedded quote [D adv p.37] and `\n` is a newline [D adv p.33]. No other escape
  is documented [?, Q9].
- The PDFs print many examples with typographic quotes (`“TRTEST”` [D adv p.3, p.10,
  p.40]). That is an artefact of the PDF typesetting. Type straight `"` [I].
- Assigning `""` to a variable leaves the variable **unregistered**. A later read logs
  `ScriptError:1 variable … not exist! use value 0 instead` [V 2026-09-28, `WISDOM.md`].
  Comparing against `""` is fine (`22-fl-flatten.das`). This is runtime behaviour, but
  every author hits it, so it is listed here.

### 2.6 Operators and punctuation

| Token | Use | Evidence |
|---|---|---|
| `=` | assignment | [D adv p.39] |
| `+ - * /` | arithmetic; `+` also concatenates strings | [D adv p.4, p.13] |
| `==` `<` | comparison | [D adv p.5, p.31] |
| `>` | comparison | [V 2026-09-25: `if ($pos > 0)` in `22-fl-flatten.das` as first committed, which ran live] |
| `<=` `>=` `!=` | comparison | [I: used in `02`, `03`, `22`; no isolated test, Q12] |
| `( ) { } . , ;` | grouping, blocks, member access, argument lists, statement end | [D adv p.4–5] |

**Not tokens.** DAS has no `&&`, no `||` and no single-quote character. Compound conditions
are nested `if`s (CONSTITUTION §10). The manuals never mention logical operators. The repo
has always treated `&&`/`||` as rejected, but no rejection is on record with a date
[?, Q3]. Unary `!`, `%`, `+=` and `++` are undocumented and unused. `%` appears only *inside*
order short-form strings (`"B 100 TSLA TL 1% D+"` [D adv p.28]).

---

## 3. Syntax

### 3.1 The grammar

W3C-style EBNF. `[ x ]` is optional, `{ x }` repeats zero or more times, and `|` separates
alternatives. Terminals are case-insensitive (§2.3).

```ebnf
script         = { statement } , [ simple ] ;                (* last ";" optional *)

statement      = if_stmt
               | while_stmt
               | simple , ";"
               | ";" ;                                       (* empty statement *)

block          = "{" , { statement } , [ simple ] , "}" ;

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

expression     = additive , [ rel_op , additive ] ;
additive       = term , { ( "+" | "-" ) , term } ;
term           = unary , { ( "*" | "/" ) , unary } ;
unary          = "-" , unary
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

- A `;` ends each statement [D adv p.4: "Separate commands must end with a ;"; D adv p.5].
- The **last statement of a script** may leave it out: `…;TIF=DAY+;BUY` [D hk p.1].
- The last statement in a block may leave it out too. The only evidence is one manual
  example, `$abc=1` directly before `}` [D hk p.24], which could be a typo [?, Q6]. The
  repo's scripts always write it.
- Blocks end at `}`. No `;` is needed after a closing brace (every script in `scripts/`).

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

The form and the `else if` chain are [D adv p.5, D hk p.24]. Braces are required: every
example uses them, and no example shows a braceless body [I]. In every documented example
and every script, the condition is a single comparison. Whether a bare value works as a
condition (`if ($flag) {…}`) is open [?, Q8]. See §4, row 1, for the one `else` that DAS
rejected.

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
- **Basic-tier raw values.** `TIF=DAY+` [D hk p.1],
  `TriggerOrder=RT:STOP STOPTYPE:LIMIT PX:0.00 …` [D hk p.8] and
  `OCO=RT:STOP … TIF:DAY+` [D hk p.9] are not expressions. When an *unqualified* name is
  assigned something that does not parse as an expression, the grammar takes everything up
  to the next `;` as raw text. How DAS itself decides between the two readings is unknown.
  This rule only matches what it accepts [I].
- **Bare words as values.** `ROUTE=LIMIT`, `$montage.route = ARCAL` [D adv p.13] and
  `SELL=Send` [D hk p.9] all parse as a `name` expression. Whether `ARCAL` means a property, a
  variable or a literal word is settled at runtime [I]. When the value is meant as text,
  quote it: the advanced guide's order objects use `$ord.Route = "LIMIT"` [D adv p.23].
- **The same boundary decides operator quoting.** Advanced script must write
  `AlertOperator="<="`, not `AlertOperator=<=` [D adv p.7]. Read as an expression, `=<=` is
  not a valid sequence, so the operator has to be a string.

### 3.7 Calls and member commands

- A function call needs `()`, even with no arguments: `GetWindowObj()` [D adv p.13],
  `$ord.send()` [D adv p.23: "Send is a function, thus we need ()"].
- Calls and member access chain: `GetQuoteObj("TSLA").ShowObject();` [D adv p.14],
  `NewOrderObj("B 100 MSFT L 400.5").Send();` [D adv p.24].
- A **member command** has no parentheses and returns nothing: `$montage.BUY;`
  `$montage.CXL;` [D adv p.13]. Syntactically it is a property access used as a statement.
  Whether the name is a command or a function is decided at runtime.
- `Exec` takes script *text*. Quotes inside that text are escaped with `\"` [D adv p.37].

### 3.8 Commands

```
NewWindow Chart; SetPopOut Y; WPos 1920 0; WSize 800 600;
```

A command is a name, optionally followed by arguments, ending at `;`. It needs no `()`
and returns nothing [D adv p.5]. The arguments are **raw text**, not expressions:

| Argument shape | Example | Evidence |
|---|---|---|
| none | `BUY` · `RemoveAllTrendLines` · `GetRect` | [D hk p.1, D adv p.37, p.9] |
| bare words / numbers | `CXL ALL BUY` · `WPos 1920 0` | [D hk p.12, D adv p.9] |
| `key=value` | `PANIC ACCOUNT=myaccount` | [D hk p.13] |
| quoted string | `HideStudies "Price,Volume"` | [D hk p.15] |
| packed fields | `ConfigTrendLine HorzLine DotLine:FFB000:2` | [I, `04-fl-hotkeys.das`] |
| a `$variable` | `LoadSetting $FL_CST_ON` | [?, Q5; `02-fl-chart-update.das`] |

Whether DAS substitutes a `$variable` inside command arguments is untested. Until Q5
settles it, `02-fl-chart-update.das` depends on that behaviour unverified.

**How a statement that starts with a name is read.** The token after the name decides:

| Next token | Reading | Example |
|---|---|---|
| `=` | assignment | `Price=Bid-0.03` |
| `(` | call | `MsgBox("x")` |
| `.` | member access, call or member command | `GetQuoteObj("X").ShowObject()` |
| `;`, `}` or end of script | command with no arguments | `BUY` |
| anything else | command with raw arguments | `PANIC ACCOUNT=x` |

### 3.9 Expressions

Precedence, from tightest to loosest:

| Level | Operators | Associativity | Evidence |
|---|---|---|---|
| postfix | `.name`, `(args)` | left | [D adv p.14] |
| unary | `-` | right | [D adv p.36] for literals; [?, Q2] for anything else |
| multiplicative | `*` `/` | left | [D adv p.4: "* and / are evaluated before + and -"] |
| additive | `+` `-` | left | [D adv p.4] |
| relational | `== != < > <= >=` | none: at most one per expression | [I], [?, Q7] |

- `+` with a string on either side concatenates and turns numbers into text:
  `$montage.HI+ " "+ $montage.LO` [D adv p.13]. In the manual's array example,
  `$result+$myObj.Get($j)+ " "` [D adv p.31] builds a string from integers. Other mixed-type
  rules (for example `"5" * 2`) are not documented.
- `$mynewvalue = $MyInteger*2+$MyNumber/$MyInteger` gives a float [D adv p.4]. Division of
  two integers is not documented [?].
- What a comparison produces as a *value* (`$c = (2 > 1);`) is not documented [?, Q7].

---

## 4. Where the manual and the build disagree

| # | Manual | Build | Evidence |
|---|---|---|---|
| 1 | `}else if (…) {` / `}else {`, with no restriction on where `else` may appear [D adv p.5] | DAS **rejected** `if (c) { a; } else { b; }` written on one line *inside an enclosing `if` block*, with `Missing }`. A **top-level** `} else {` parses even after the harness joins the file onto one line: `22-fl-flatten.das` (with `} else {` since its first commit) ran live and placed the XOM close. So line layout does not explain the rejection. The working hypothesis is that `else` fails inside a nested block. | rejection [V 2026-09-28, commit `3c007de`]; acceptance [V 2026-09-25, `docs/forward-tests/fl-2026-09-24-report.md`, XOM row]; cause [?, Q1] |
| 2 | Quotes printed as `“ ”` in many examples [D adv p.3, p.10, p.40] | Straight `"` only. Any `'` in code is a parse error. | [V 2026-09-24] for `'`; [I] for the typographic quotes |
| 3 | `TSLA_QUOTE.BID` with no `$`, after assigning `$TSLA_Quote` [D adv p.16] | Grammatically that is a property of the focused window named `TSLA_QUOTE`, not the variable. Almost certainly a manual error. | [I] |
| 4 | `GetWindowObj()` with no argument returns the window just created [D adv p.13] | Not syntax, but it breaks the manual's two-liner: it returned nothing until `Wait(500)`, and once returned the montage instead of the new chart. | [V 2026-09-20, `WISDOM.md`] |

## 5. Open questions and how to settle them

Each test is a snippet for `tools/das_script_test.py run montage1 '<snippet>'` on the TR4425
paper account. None of them sends an order. A parse error opens DAS's modal dialog, which
the harness dismisses and logs as an `Error` line. A pass shows up as the `MsgLog` line.

| Q | Question | Snippet | Pass looks like |
|---|---|---|---|
| Q1 | Is `else` rejected only inside a nested block? | `$t=0; if (1==1) { if ($t==0) { MsgLog("q1 A"); } else { MsgLog("q1 B"); } }` | `q1 A` → nested `else` is fine and the 09-28 rejection had another cause; `ScriptError:100` → hypothesis confirmed |
| Q2 | Unary minus on a variable | `$a=3; $b=-$a; MsgLog("q2 ", $b);` | `q2 -3` |
| Q3 | Is `&&` a parse error? | `if (1==1 && 2==2) { MsgLog("q3 and"); }` | `ScriptError:100` confirms the rule |
| Q4 | Block comments | `/* x */ MsgLog("q4");` | `q4` → block comments exist |
| Q5 | `$var` substitution in command arguments | `$q5="hidden_chart1"; FocusWindow $q5; MsgLog("q5 ", GetTicker());` | the hidden chart's ticker, not the montage's |
| Q6 | Final `;` optional inside a block | `if (1==1) { MsgLog("q6") }` | `q6` |
| Q7 | Comparison as a value | `$c = (2 > 1); MsgLog("q7 ", $c);` | `q7 1` (or whatever DAS's true is) |
| Q8 | Bare value as a condition | `$z=1; if ($z) { MsgLog("q8"); }` | `q8` |
| Q9 | Other escapes | `MsgLog("q9 a\tb");` | a tab between `a` and `b` |
| Q10 | Keyword case | `IF (1==1) { MsgLog("q10"); }` | `q10` |
| Q11 | Unary `!` | `if (!(1==2)) { MsgLog("q11"); }` | `q11` |
| Q12 | `<=` `>=` `!=` | `if (1<=1) { MsgLog("q12 le"); } if (2>=1) { MsgLog("q12 ge"); } if (1!=2) { MsgLog("q12 ne"); }` | all three lines |

**Layout can't be tested through the API.** The harness puts every snippet on one line, so
any question about line breaks (row 1 of §4 included) has to be settled by pasting into the
hotkey dialog by hand.

When a question is settled, change its label in this file to **[V date]** and cite the log
line, as CONSTITUTION §6 requires.

## 6. What builds on this

- **Language reference.** The next chapters are the built-in functions and commands
  (adv pp.7–9), the object model (adv pp.9–17, 21–36), execution contexts (hotkey,
  hot button, Chart Script, Timer Event, Desktop Load Script) and limits.
- **`dastrader-mode`.** Font-lock comes straight from §2: `//` comments, `"` strings with
  `\` escapes, `$` globals, the four keywords, and the operators of §2.6. Indentation
  follows the brace structure of §3.
- **A stdlib checker in `tools/`.** A recursive-descent parser for §3 would replace the
  regex lint in `das_script_test.py check`. It is also the parser that `.htk` generation
  (roadmap item 4) needs.

# Intent: DASTRADER Scripts and explanations of scripts. 

Author: David Duncan <davdunc@gmail.com> 
Status: Draft
 
## Problem

DAS Trader hotkey scripts are a domain-specific language used to configure and
submit trading actions from keyboard shortcuts, buttons, alerts, timers, and
other DAS execution contexts.

A script can set order route, price, share quantity, account, time-in-force,
trigger orders, and other state before ultimately issuing an action such as
`BUY=Send`, `SELL=Send`, or a cancellation command.

The language is compact and operationally powerful, but authoring is error-prone:

- Commands are chained in a semicolon-delimited string.
- Some identifiers and commands are case-sensitive.
- Script order matters because later commands depend on prior field assignments.
- Variables, market-data references, montage fields, trigger orders, and account
  constraints may interact in non-obvious ways.
- A syntactically valid script can still be unsafe because of an unintended route,
  account, share quantity, stop price, or live-order action.
- The default editing environment does not provide the code-oriented feedback
  expected for a safety-sensitive scripting language.

## Proposed outcome 
A DSL Documentation project with grammar rules, syntax specs, and usage examples including, but not limited to the following documents: 
  - A language reference for developers that is similar in content and character to the java specification manual found at https://docs.oracle.com/javase/specs/jls/se8/html/index.html
  - A Cookbook for various structures that users might want to create. It should be similar in function (not in web presentation) to https://javacookbook.org/
  - A Tutorial for domain experts

### Developer-experience outcome: 
#### Emacs editing mode

Provide enough language metadata and tooling to support a community-maintained or
first-party Emacs major mode, tentatively named `dastrader-mode`.

The intended editing experience includes:

- Syntax highlighting for keywords, declarations, operators, literals, comments,
  rule names, fields, functions, and named signal values.
- Automatic activation for `.htk` files.
- Indentation rules matching the canonical formatter.
- Comment commands for single-line and block comments.
- Optional `eglot` integration if a Language Server Protocol implementation is
  introduced.
- Navigation or completion support for known fields, built-in functions, and
  diagnostic codes when the language server is available.
  

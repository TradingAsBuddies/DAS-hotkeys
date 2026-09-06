# DAS Trader Manual Collection

Retrieved **2026-09-03**. Every file fetched over HTTPS, HTTP 200, verified `%PDF-` magic
bytes, deduplicated by MD5. All 20 are hosted on dastrader.com.

## Current manuals index

Linked from https://dastrader.com/docs/das-user-guide-and-manuals/

| File | Title | Pages | Bytes | Source URL |
|------|-------|------:|------:|------------|
| `das-trader-pro-user-manual.pdf` | DAS Trader Pro User Manual (current edition) | 52 | 1728937 | https://dastrader.com/wp-content/uploads/2020/07/DASTRADER-USER-MANUAL.pdf |
| `das-advanced-hotkey-guide.pdf` | Advanced Hotkey Guide | 40 | 1073108 | https://dastrader.com/documents/AdvancedHotkeyGuide.pdf |
| `das-hotkeys-guide.pdf` | Hotkeys Guide | 28 | 810529 | https://dastrader.com/documents/DASTraderHotkeys-Guide.pdf |
| `das-hot-buttons-guide-v5.8.0.2.pdf` | Hot Buttons Guide v5.8.0.2 | 21 | 1015251 | https://dastrader.com/documents/DASNewHotButtonsGuide-v5.8.0.2.pdf |
| `das-tradesignal-user-guide.pdf` | TradeSignal User Guide (advanced scanner) | 13 | 1438134 | https://dastrader.com/documents/TradeSignalUserGuide.pdf |
| `das-active-web-guide.pdf` | Active Web Guide | 10 | 959046 | https://dastrader.com/documents/ActiveWebGuide.pdf |
| `das-chart-studies.pdf` | Chart Studies in DAS Trader | 7 | 390912 | https://dastrader.com/documents/ChartStudies.pdf |
| `das-order-objects-v2.pdf` | DAS Order Objects V2 | 5 | 296741 | https://dastrader.com/documents/DASOrderObjectsV2.pdf |
| `das-complex-options-guide.pdf` | Complex Options Guide | 4 | 568738 | https://dastrader.com/documents/DASComplexOptionsGuide.pdf |
| `das-futures-symbols-guide.pdf` | Futures Symbol Guide | 3 | 183833 | https://dastrader.com/documents/DASTraderFutureSymbolsGuide.pdf |
| `das-scanner-guide.pdf` | DAS Scanner Guide | 3 | 200288 | https://dastrader.com/documents/DASScanner-Guide.pdf |
| `das-midpoint-order-types.pdf` | Pegged/MidPoint Order Types (BATS, ARCA, EDGA, EDGX) | 3 | 209118 | https://dastrader.com/documents/MidpointOrderTypes.pdf |
| `das-allocation-guide.pdf` | Allocation Guide | 2 | 269639 | https://dastrader.com/documents/DASTraderAllocationGuide.pdf |
| `das-indices-symbol-guide.pdf` | Indices Symbol Guide | 1 | 224110 | https://dastrader.com/documents/DASIndicesList.pdf |
| `das-options-symbology-guide.pdf` | Options Symbology Guide | 1 | 6389 | https://dastrader.com/documents/OptionSymbols.pdf |

## Legacy documents — still live, no longer linked from the index

These URLs came from the Bear Bull Traders manuals thread. They are **not** reachable from
dastrader.com's own navigation any more, but the files still serve 200. They cover ground the
current set does not.

| File | Title | Pages | Bytes | Source URL |
|------|-------|------:|------:|------------|
| `das-trader-user-manual-legacy.pdf` | DAS Trader User Manual (older edition — different content, not a subset) | 33 | 1301863 | https://dastrader.com/documents/DAS%20Trader%20User%20Manual.pdf |
| `das-hotkey-and-command-script-user-guide.pdf` | Hot Key and Command Script User Guide | 9 | 403237 | https://dastrader.com/documents/HotKeys.pdf |
| `das-trigger-orders-guide.pdf` | Trigger Order Guide | 4 | 338097 | https://dastrader.com/documents/Triggerorders.pdf |
| `das-add-new-routes-to-montage.pdf` | Add Routes to Your Montage | 2 | 229372 | https://dastrader.com/documents/addnewroutestomontage.pdf |
| `das-run-pro-on-non-windows-os.pdf` | Running DAS Trader Pro from Non-Windows OS (2014) | 2 | 367919 | https://dastrader.com/documents/How-to-run-PRO-on-Non-Windows-OS.pdf |

**20 files, 243 pages, ~10.0 MB.**

Two legacy URLs from that thread are dead (404) and were discarded rather than kept as empty
files: `DASScanner.pdf` and `allocationguide.pdf`. Both are superseded by
`das-scanner-guide.pdf` and `das-allocation-guide.pdf` above.

A CenterPoint Securities mirror was also fetched and then **deleted** — MD5 `60122278…` proved
it byte-identical to `das-trader-user-manual-legacy.pdf`. The DAS-hosted copy is kept as the
authoritative one.

## Sources

- https://dastrader.com/docs/das-user-guide-and-manuals/ — the 15 current PDFs
- https://dastrader.com/kb-category/download-links/ — Guides and Manuals category index
- https://dastrader.com/kb/ — full KB index (HTML articles, not PDFs)
- https://forums.bearbulltraders.com/topic/3-das-trader-manuals/ — the 5 legacy URLs

## What is NOT here

### CMD API specification — certification-gated, not downloadable

The document specifying the CMD API command set is not public. Per
https://dastrader.com/docs/how-do-i-get-approved-for-api-access/ :

> "Access is not automatically granted with a DAS subscription."

Path: valid DAS login + signed market-data exchange agreements → API Request Portal at
https://dastrader.com/das-api-services/ → certification form → DAS review → permissions
enabled and the API document released for your usage type (retail and institutional tiers
get different documents).

Per https://dastrader.com/docs/which-api-should-i-use-cmd-net-or-fix/ , CMD is the
language/OS-agnostic socket API and requires DAS Trader Pro to be running — consistent with
how the scripts in `~/.claude/Tools/` and `~/falcon/dashboard/` already talk to DAS.

Until certification completes, the unofficial reference is
https://github.com/misantroop/das-bridge (Python CMD API client). Community
reverse-engineering, not a spec.

### HTML-only knowledge base articles

Montage and chart *alignment* is documented mainly in KB web pages, not PDFs — notably
*Linking Windows by Color*, *How do I link the Montage window to other windows?*, *How do I
set up a default desktop or layout?*, *How do I use Multiple Layouts?*, *How do I save
trendlines and have them appear on other charts (Global Trendlines)?*, *How to assign hotkeys
to specific Montage or trading window?*, and *How can I lock the Montage window?*.
Catalogued this pass, not archived.

## Full text — `docs/text/`

Every PDF is extracted to plain text in `docs/text/`, one `.txt` per PDF, with `===== [file p.N] =====`
page markers so any hit can be traced back to a page. Regenerate with:

```bash
python3 -c '
from pypdf import PdfReader; import glob
for f in sorted(glob.glob("docs/manuals/*.pdf")):
    r=PdfReader(f)
    open("docs/text/"+f.split("/")[-1].replace(".pdf",".txt"),"w").write(
      "".join(f"\n\n===== [{f} p.{i}] =====\n"+(p.extract_text() or "") for i,p in enumerate(r.pages,1)))
'
```

**373,384 characters extracted, all 20 documents.** `pypdf` (6.14.2) is installed and handles this
corpus cleanly. `pdftotext`/`pdfinfo` (poppler-utils) are *not* installed and are not needed.

Grep the corpus, not the PDFs: `grep -in 'wpos' docs/text/*.txt`

## Topical starting points (verified against extracted text)

| Goal | Start here |
|------|-----------|
| Variables / scripting | `das-advanced-hotkey-guide.pdf` pp.3-4, 39-40 — **the primary source**, updated June 2025 |
| Montage alignment | `das-advanced-hotkey-guide.pdf` pp.8-13 (WPos/WSize/GetRect), `das-hotkeys-guide.pdf` pp.14-16 |
| Chart alignment | `das-hotkeys-guide.pdf` pp.15-16 (global trendlines), `das-advanced-hotkey-guide.pdf` pp.36-37 |
| Order construction | `das-order-objects-v2.pdf`, `das-trigger-orders-guide.pdf`, `das-midpoint-order-types.pdf` |
| Scanning / signals | `das-tradesignal-user-guide.pdf`, `das-scanner-guide.pdf` |

See `docs/WISDOM.md` for the extracted synthesis of all of the above.

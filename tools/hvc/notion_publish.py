#!/usr/bin/env python3
"""Publish an HVC chart book to Notion: one private page per day under a parent page.

    notion_publish.py                    # newest tools/hvc/out/<date>.json
    notion_publish.py --report tools/hvc/out/2026-11-10.json --dry-run

Needs, in ~/.claude/.env:
  NOTION_API_KEY       internal integration token with access to the parent page
  HVC_NOTION_PARENT    page id of "HVC Chart Books"

Re-running for a date archives that date's existing page (Notion trash, restorable
for 30 days) and creates a fresh one, so the newest run always wins.
The pages carry licensed market data: the parent must stay private.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import chartbook  # noqa: E402
from das_script_test import load_env  # noqa: E402

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
UPSTREAM = "https://github.com/major/tradingview/tree/main/hvc_watcher"
LWC_HOME = "https://www.tradingview.com/lightweight-charts/"


class NotionError(RuntimeError):
    pass


# ── HTTP ─────────────────────────────────────────────────────────────────────

class Notion:
    def __init__(self, token: str):
        self.token = token

    def _req(self, method: str, path: str, body: bytes | None, ctype: str | None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}", "Notion-Version": VERSION}
        if ctype:
            headers["Content-Type"] = ctype
        req = urllib.request.Request(API + path, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise NotionError(f"{method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}") from None
        except urllib.error.URLError as e:
            raise NotionError(f"{method} {path}: {e.reason}") from None

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        return self._req(method, path, data, "application/json" if data else None)

    def upload_png(self, png: Path) -> str:
        fu = self.call("POST", "/file_uploads", {"mode": "single_part", "filename": png.name,
                                                  "content_type": "image/png"})
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{png.name}\"\r\n"
                f"Content-Type: image/png\r\n\r\n").encode() + png.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        sent = self._req("POST", f"/file_uploads/{fu['id']}/send", body, f"multipart/form-data; boundary={boundary}")
        if sent.get("status") != "uploaded":
            raise NotionError(f"{png.name}: upload status {sent.get('status')!r}")
        return fu["id"]

    def child_pages(self, parent: str) -> list[dict]:
        out, cursor = [], None
        while True:
            q = f"/blocks/{parent}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            d = self.call("GET", q)
            out += [b for b in d["results"] if b["type"] == "child_page"]
            if not d.get("has_more"):
                return out
            cursor = d["next_cursor"]


# ── blocks ───────────────────────────────────────────────────────────────────

def rt(text: str, *, bold=False, code=False, color="default", link: str | None = None) -> dict:
    return {"type": "text", "text": {"content": text, "link": {"url": link} if link else None},
            "annotations": {"bold": bold, "italic": False, "strikethrough": False, "underline": False,
                            "code": code, "color": color}}


def para(*parts: dict) -> dict:
    return {"type": "paragraph", "paragraph": {"rich_text": list(parts)}}


def h2(text: str) -> dict:
    return {"type": "heading_2", "heading_2": {"rich_text": [rt(text)]}}


def callout(emoji: str, color: str, *parts: dict) -> dict:
    return {"type": "callout", "callout": {"rich_text": list(parts), "icon": {"type": "emoji", "emoji": emoji},
                                           "color": color}}


def table(header: list[str], rows: list[list[str]]) -> dict:
    mk = lambda cells: {"type": "table_row", "table_row": {"cells": [[rt(c)] for c in cells]}}  # noqa: E731
    return {"type": "table", "table": {"table_width": len(header), "has_column_header": True,
                                       "has_row_header": False, "children": [mk(header)] + [mk(r) for r in rows]}}


def image(upload_id: str, caption: str) -> dict:
    return {"type": "image", "image": {"type": "file_upload", "file_upload": {"id": upload_id},
                                       "caption": [rt(caption)]}}


def _mult(s: dict) -> str:
    return "N/A" if s.get("multiplier") is None else f"{s['multiplier']:.1f}x"


def ordered(report: dict) -> list[dict]:
    ev, tc = set(report["events"]), set(report["touches"])
    return sorted(report["symbols"], key=lambda s: (0 if s["symbol"] in ev else 1 if s["symbol"] in tc else 2,
                                                    s["symbol"]))


def page_blocks(report: dict, uploads: dict[str, str]) -> list[dict]:
    p, syms = report["params"], ordered(report)
    since = min((s.get("since") for s in syms if s.get("since")), default="?")
    last = max((s.get("date") for s in syms if s.get("date")), default="?")
    open_bar = any(not s.get("confirmed", True) for s in syms)
    blocks = [
        callout("📊", "gray_background", rt(
            f"Daily scan of {len(syms)} symbols, last bar {last}. "),
            rt(f"{len(report['events'])}", bold=True), rt(" with an HVC/HVE on the last bar, "),
            rt(f"{len(report['touches'])}", bold=True), rt(
                f" touching a retained ray. SMA {p['sma']}, {p['mult']}x, {p['ray_limit']} rays, "
                f"HVE warm-up {p.get('hve_warmup', 0)} bars. HVE history from {since}."
                + (" Last bar was still open at scan time." if open_bar else ""))),
        callout("🔒", "red_background", rt(
            "Contains licensed Polygon/Massive market data. Personal use only: keep private, do not share.")),
    ]
    if report.get("errors"):
        blocks.append(callout("⚠️", "yellow_background",
                              rt("Data errors: " + "; ".join(f"{k}: {v}" for k, v in report["errors"].items()))))
    rows = []
    for s in syms:
        near = min(s["rays"], key=lambda x: abs(x["level"] - s["close"]), default=None)
        rows.append([s["symbol"], f"{s['close']:g}", _mult(s), s["event"] or "-", "yes" if s["touched"] else "-",
                     f"{near['kind']} {near['level']:g} ({near['date']})" if near else "-"])
    blocks += [h2("Summary"), table(["Symbol", "Close", "Vol / SMA", "Last-bar event", "Touch", "Nearest ray"], rows),
               para(rt("● HVE", color="green"), rt(" volume record · "), rt("● HVC", color="orange"),
                    rt(f" volume ≥ {p['mult']}× the {p['sma']}-bar SMA · "), rt("▲", color="blue"),
                    rt(" later bar touched a retained ray · dashed line in the volume pane = HVC threshold."))]
    for s in syms:
        sym = s["symbol"]
        blocks += [h2(sym), para(rt(f"Close {s['close']:g} · volume {_mult(s)} of SMA · event: "
                                    f"{s['event'] or 'none'} · touch: {'yes' if s['touched'] else 'no'}"))]
        if sym in uploads:
            blocks.append(image(uploads[sym], f"{sym} daily, last ~260 bars"))
        if s["rays"]:
            blocks.append(table(["Retained ray", "Date", "Level", "vs close"],
                                [[x["kind"], x["date"], f"{x['level']:g}",
                                  f"{(x['level'] / s['close'] - 1) * 100:+.1f}%"] for x in s["rays"]]))
        else:
            blocks.append(para(rt("No retained rays.")))
    blocks += [{"type": "divider", "divider": {}},
               para(rt("Generated by "), rt("tools/hvc/hvc_daily.py --notion", code=True),
                    rt(" in DAS-hotkeys. Signals ported from Major Hayden's "), rt("hvc_watcher", link=UPSTREAM),
                    rt(" (Apache-2.0). Charts drawn with "), rt("TradingView Lightweight Charts™", link=LWC_HOME),
                    rt(f" v{chartbook.LWC_VERSION} (Apache-2.0)."))]
    return blocks


def title_for(report: dict) -> str:
    return f"HVC Chart Book · {report['date']}"


# ── publish ──────────────────────────────────────────────────────────────────

def publish(report_path: Path, *, env: dict | None = None, client: Notion | None = None,
            render=chartbook.render_pngs, dry_run: bool = False) -> str:
    """Returns the new page URL (or a summary line for --dry-run)."""
    env = env if env is not None else load_env()
    parent = env.get("HVC_NOTION_PARENT")
    if not parent:
        raise NotionError("HVC_NOTION_PARENT not set in ~/.claude/.env")
    report = json.loads(report_path.read_text())
    title = title_for(report)

    with tempfile.TemporaryDirectory(prefix="hvc-notion-") as tmp:
        pngs = render(report_path, Path(tmp))
        if dry_run:
            blocks = page_blocks(report, {s: "dry-run" for s in pngs})
            return f"[dry-run] {title}: {len(blocks)} blocks, {len(pngs)} images under {parent}"
        if client is None:
            token = env.get("NOTION_API_KEY")
            if not token:
                raise NotionError("NOTION_API_KEY not set in ~/.claude/.env")
            client = Notion(token)
        uploads = {sym: client.upload_png(p) for sym, p in pngs.items()}

    for old in client.child_pages(parent):
        if old["child_page"]["title"] == title:
            client.call("PATCH", f"/pages/{old['id']}", {"archived": True})

    blocks = page_blocks(report, uploads)
    page = client.call("POST", "/pages", {
        "parent": {"type": "page_id", "page_id": parent},
        "icon": {"type": "emoji", "emoji": "📊"},
        "properties": {"title": {"title": [rt(title)]}},
        "children": blocks[:100],
    })
    for i in range(100, len(blocks), 100):      # API caps a request at 100 top-level blocks
        client.call("PATCH", f"/blocks/{page['id']}/children", {"children": blocks[i:i + 100]})
    return page["url"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", type=Path, help="default: newest tools/hvc/out/<date>.json")
    ap.add_argument("--dry-run", action="store_true", help="render screenshots and blocks; no Notion calls")
    a = ap.parse_args(argv)
    try:
        print(publish(a.report or chartbook.newest_report(), dry_run=a.dry_run))
    except (NotionError, RuntimeError) as exc:
        print(f"[notion] FAILED: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

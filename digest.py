"""Nightly task digest: snapshot -> diff -> (optional LLM summary) -> deliver.

    python3 digest.py --source json --print
    python3 digest.py --source lark --webhook      # needs env, see .env.example
"""
import utils.transport
import utils.session
import argparse
import importlib
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import core

STATE = os.environ.get("DIGEST_STATE", "state")
TZ = ZoneInfo(os.environ.get("DIGEST_TIMEZONE", "UTC"))
HANDLE = os.environ.get("DIGEST_HANDLE", "@lead")
MODEL = os.environ.get("DIGEST_MODEL", "claude-sonnet-4-6")
BATCH = 12  # one giant LLM call across ~60 tasks timed out and killed the whole digest


def today():
    return datetime.now(TZ).strftime("%Y-%m-%d")


def load_prev():
    try:
        with open(f"{STATE}/latest.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def to_snapshot(tasks):
    return {t["id"]: {"title": t["title"], "status": t["status"],
                      "comment_sig": core.comment_signature(t["comments"]),
                      "comments": t["comments"][-5:],
                      "created_day": t.get("created_day")} for t in tasks}


def save(snap, day):
    os.makedirs(f"{STATE}/archive", exist_ok=True)
    for path in (f"{STATE}/latest.json", f"{STATE}/archive/{day}.json"):
        with open(path, "w") as f:
            json.dump(snap, f, indent=1)


def summarise(items):
    """One-line bullets per task via the Anthropic API; titles on any failure."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    out = {tid: t["title"] for tid, t in items.items()}
    if not key:
        return out
    ids = list(items)
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        payload = {tid: {"title": items[tid]["title"],
                         "recent_comments": items[tid]["comments"][-5:]} for tid in chunk}
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=60,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": MODEL, "max_tokens": 2000, "messages": [{"role": "user",
                      "content": "Return ONLY JSON mapping each key to a one-line "
                                 "status summary based solely on its own comments:\n"
                                 + json.dumps(payload)}]})
            text = "".join(b.get("text", "") for b in r.json()["content"])
            out.update({k: v for k, v in json.loads(text).items() if k in chunk})
        except Exception as e:  # a failed batch loses only its own tasks
            print(f"! summary batch failed: {e}", file=sys.stderr)
    return out


def render(day, groups, tasks, summaries, asks):
    def block(title, ids):
        if not ids:
            return ""
        lines = [f"**{title}** ({len(ids)})"]
        lines += [f"- {tasks[i]['title']}: {summaries.get(i, '')}" for i in ids]
        return "\n".join(lines) + "\n\n"
    md = f"# Digest for {day}\n\n"
    md += block("Needs your decision", asks["decision"])
    md += block("Pending your review", asks["review"])
    md += block("Waiting on the team first", asks["pending"])
    md += block("Blocked", groups["blocked"])
    md += block("Completed today", groups["completed"])
    md += block("Advanced today", groups["advanced"][:15])  # backstop against a detection bug dumping the board
    return md.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="json", choices=["json", "lark"])
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--webhook", action="store_true", help="POST to DIGEST_WEBHOOK_URL")
    a = ap.parse_args()

    tasks_list = importlib.import_module(f"sources.{'json_file' if a.source == 'json' else 'lark'}").fetch()
    tasks = {t["id"]: t for t in tasks_list}
    curr, prev, day = to_snapshot(tasks_list), load_prev(), today()

    if prev is None:
        save(curr, day)
        print("Baseline saved. Nothing to diff yet; digest starts tomorrow.")
        return

    groups = core.diff(prev, curr, day)
    asks = {"decision": [], "review": [], "pending": []}
    for tid, t in tasks.items():
        if t["status"].strip().lower() in core.DONE_STATES or not t["comments"]:
            continue
        kind = core.classify_ask(t["comments"][-1], HANDLE)  # latest comment only: history can never clear a flag
        if kind:
            asks[kind].append(tid)

    shown = {i for g in list(groups.values()) + list(asks.values()) for i in g}
    summaries = summarise({i: tasks[i] for i in shown})
    md = render(day, groups, tasks, summaries, asks)
    save(curr, day)
    if a.print or not a.webhook:
        print(md)
    if a.webhook:
        requests.post(os.environ["DIGEST_WEBHOOK_URL"], json={"text": md}, timeout=30).raise_for_status()


if __name__ == "__main__":
    main()

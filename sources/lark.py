"""Lark/Feishu Tasks v2 adapter. Needs LARK_APP_ID and LARK_APP_SECRET.

Lark has no 'what changed today' feed (updated_at moves on any edit), which
is the whole reason this project keeps its own snapshots.
"""
import os
import requests

BASE = os.environ.get("LARK_BASE", "https://open.larksuite.com")


def _token():
    r = requests.post(f"{BASE}/open-apis/auth/v3/tenant_access_token/internal",
                      json={"app_id": os.environ["LARK_APP_ID"],
                            "app_secret": os.environ["LARK_APP_SECRET"]}, timeout=30)
    d = r.json()
    if d.get("code") != 0:
        raise RuntimeError(f"auth failed: {d.get('msg')}")
    return d["tenant_access_token"]


def _get(tok, path, **params):
    r = requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {tok}"},
                     params=params, timeout=30)
    return r.json().get("data", {})


def fetch():
    tok = _token()
    tasks = {}
    for tl in _get(tok, "/open-apis/task/v2/tasklists", page_size=50).get("items", []):
        sections = {s["guid"]: s["name"] for s in _get(
            tok, "/open-apis/task/v2/sections", resource_type="tasklist",
            resource_id=tl["guid"], page_size=50).get("items", [])}
        page = None
        while True:
            d = _get(tok, "/open-apis/task/v2/tasks", tasklist_guid=tl["guid"],
                     page_size=50, **({"page_token": page} if page else {}))
            for t in d.get("items", []):
                sec = next((sections.get(m.get("section_guid"))
                            for m in t.get("tasklists", [])
                            if m.get("tasklist_guid") == tl["guid"]), None)
                comments = [c.get("content", "") for c in _get(
                    tok, "/open-apis/task/v2/comments", resource_type="task",
                    resource_id=t["guid"], page_size=20).get("items", [])]
                prev = tasks.get(t["guid"])
                # Multi-board tasks: a blank section must never clobber a real one.
                if prev and not sec:
                    continue
                tasks[t["guid"]] = {
                    "id": t["guid"], "title": t.get("summary", ""),
                    "status": sec or "(none)", "comments": comments,
                    "url": t.get("url", ""), "created_day": None,
                }
            if not d.get("has_more"):
                break
            page = d.get("page_token")
    return list(tasks.values())

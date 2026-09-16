"""Capture snapshots of new (or all, with --refresh) URLs using single-file-cli.

Snapshots are stored by URL, not by school, so relabeling a page in the
sheet never requires recapturing it:
    snapshots/<url-id>/<YYYY-MM-DD>.html

State lives in data/captures.json:
    { url: {id, status, attempts, error, title, versions: [{date, file}]} }
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "data" / "entries.json"
STATE = ROOT / "data" / "captures.json"
SNAPS = ROOT / "snapshots"

MAX_ATTEMPTS = 3          # stop retrying a failing URL after this many runs
MAX_PER_RUN = 40          # keep each Actions run reasonably short
KEEP_VERSIONS = 2         # latest plus one previous
TIMEOUT_S = 180
MIN_BYTES = 2000          # smaller than this is almost certainly an error page

# Extra CLI flags can be tuned from the workflow without editing this file.
DEFAULT_ARGS = "--browser-executable-path=/usr/bin/google-chrome"
EXTRA_ARGS = shlex.split(os.environ.get("SINGLEFILE_ARGS", DEFAULT_ARGS))


def url_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:10]


def page_title(path):
    head = path.read_bytes()[:200_000].decode("utf-8", "ignore")
    m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
    return html.unescape(" ".join(m.group(1).split())) if m else ""


def capture(url, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["single-file", url, str(out), *EXTRA_ARGS]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return "timed out"
    if r.returncode != 0:
        return (r.stderr or r.stdout or f"exit {r.returncode}").strip()[-300:]
    if not out.exists() or out.stat().st_size < MIN_BYTES:
        out.unlink(missing_ok=True)
        return "page saved empty (site may block automated visits)"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="recapture every URL")
    args = ap.parse_args()

    entries = json.loads(ENTRIES.read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    today = dt.date.today().isoformat()

    urls = list(dict.fromkeys(e["url"] for e in entries))
    todo = []
    for u in urls:
        s = state.get(u)
        if s is None:
            todo.append(u)
        elif args.refresh and not any(v["date"] == today for v in s.get("versions", [])):
            s["attempts"] = 0
            todo.append(u)
        elif s["status"] == "failed" and s.get("attempts", 0) < MAX_ATTEMPTS:
            todo.append(u)

    print(f"{len(todo)} to capture ({len(urls)} URLs total)")
    for n, u in enumerate(todo[:MAX_PER_RUN]):
        uid = url_id(u)
        s = state.setdefault(u, {"id": uid, "status": "pending", "attempts": 0, "versions": []})
        rel = f"snapshots/{uid}/{today}.html"
        err = capture(u, ROOT / rel)
        s["attempts"] = s.get("attempts", 0) + 1
        if err:
            s["error"] = err
            if not s["versions"]:
                s["status"] = "failed"
            print(f"  FAIL {u}: {err}")
        else:
            s.update(status="ok", error="", title=page_title(ROOT / rel), attempts=0)
            s["versions"] = [v for v in s["versions"] if v["date"] != today]
            s["versions"].append({"date": today, "file": rel})
            s["versions"].sort(key=lambda v: v["date"])
            for old in s["versions"][:-KEEP_VERSIONS]:
                (ROOT / old["file"]).unlink(missing_ok=True)
            s["versions"] = s["versions"][-KEEP_VERSIONS:]
            print(f"  ok   {u}")
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        if n < len(todo) - 1:
            time.sleep(3)  # be polite to school servers

    if len(todo) > MAX_PER_RUN:
        print(f"{len(todo) - MAX_PER_RUN} left for the next run")


if __name__ == "__main__":
    main()

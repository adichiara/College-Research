"""Build the readable static site into build/ from entries.json + captures.json.

Organization comes entirely from the sheet (School -> Major -> Info Type),
so relabeling in the sheet and rebuilding regroups everything.
"""
import json
import re
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "build"   # readable output; the workflow encrypts it into dist/
TEMPLATE = ROOT / "site" / "index.html"
# Injected into each snapshot: keep it out of search engines, and open any
# link clicked inside a saved page in a new tab instead of inside the viewer.
NOINDEX = (b'<meta name="robots" content="noindex, nofollow, noarchive">'
           b'<base target="_blank">')


def copy_snapshot(rel):
    """Copy a snapshot into dist/p/, adding a noindex tag."""
    src = ROOT / rel
    if not src.exists():
        return None
    dest_rel = "p/" + rel.split("/", 1)[1]
    dest = DIST / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    data, n = re.subn(rb"(<head[^>]*>)", rb"\1" + NOINDEX, data, count=1, flags=re.I)
    if n == 0:
        data = NOINDEX + data
    dest.write_bytes(data)
    return dest_rel


def main():
    entries = json.loads((ROOT / "data" / "entries.json").read_text())
    cap = ROOT / "data" / "captures.json"
    state = json.loads(cap.read_text()) if cap.exists() else {}

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    copied = {}
    items = []
    for e in entries:
        s = state.get(e["url"], {})
        versions = []
        for v in reversed(s.get("versions", [])):   # newest first
            if v["file"] not in copied:
                copied[v["file"]] = copy_snapshot(v["file"])
            if copied[v["file"]]:
                versions.append({"date": v["date"], "file": copied[v["file"]]})
        items.append({
            "url": e["url"],
            "school": e.get("school", ""),
            "major": e.get("major", ""),
            "info": e.get("info_type", ""),
            "tags": e.get("tags", []),
            "notes": e.get("notes", ""),
            "addedBy": e.get("added_by", ""),
            "title": s.get("title") or "",
            "status": "ok" if versions else s.get("status", "pending"),
            "error": s.get("error", "") if not versions else "",
            "versions": versions,
        })

    # Column order: most-used info types first, then alphabetical.
    counts = Counter(i["info"] for i in items if i["info"])
    info_types = sorted(counts, key=lambda k: (-counts[k], k.lower()))

    data = {"items": items, "infoTypes": info_types}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*__DATA__*/null", payload)
    (DIST / "index.html").write_text(page)
    (DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (DIST / ".nojekyll").write_text("")

    print(f"Built {len(items)} items, {sum(1 for v in copied.values() if v)} snapshots")


if __name__ == "__main__":
    main()

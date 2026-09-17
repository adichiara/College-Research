"""Build the readable static site into build/ from data/entries.json.

Organization comes entirely from the sheet (School -> Major -> Info Type).
The workflow encrypts build/ into dist/ before publishing.
"""
import json
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
TEMPLATE = ROOT / "site" / "index.html"


def short_label(url):
    """unh.edu > animal-science, from https://www.unh.edu/program/.../animal-science"""
    u = urlparse(url)
    host = u.netloc.removeprefix("www.")
    parts = [p for p in unquote(u.path).split("/") if p]
    last = parts[-1].rsplit(".", 1)[0].replace("-", " ").replace("_", " ") if parts else ""
    return f"{host} › {last}" if last else host


def main():
    entries = json.loads((ROOT / "data" / "entries.json").read_text())

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()

    items = [{
        "url": e["url"],
        "label": short_label(e["url"]),
        "school": e.get("school", ""),
        "major": e.get("major", ""),
        "info": e.get("info_type", ""),
        "tags": e.get("tags", []),
        "keyText": e.get("key_text", ""),
        "notes": e.get("notes", ""),
        "addedBy": e.get("added_by", ""),
        "added": e.get("timestamp", ""),
    } for e in entries]

    # Column order: most-used info types first, then alphabetical.
    counts = Counter(i["info"] for i in items if i["info"])
    info_types = sorted(counts, key=lambda k: (-counts[k], k.lower()))

    payload = json.dumps({"items": items, "infoTypes": info_types}, ensure_ascii=False).replace("</", "<\\/")
    (BUILD / "index.html").write_text(TEMPLATE.read_text().replace("/*__DATA__*/null", payload))
    (BUILD / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (BUILD / ".nojekyll").write_text("")
    print(f"Built {len(items)} items")


if __name__ == "__main__":
    main()

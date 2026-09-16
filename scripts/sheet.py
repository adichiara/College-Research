"""Read the family's Google Form responses and write data/entries.json (git-ignored).

Expects the Form's response sheet as the first tab. Optional tab named
"Aliases" with columns: Field | From | To  (Field = School, Major or Info Type)
maps variant spellings to one canonical label at build time.

Environment:
  GOOGLE_SERVICE_ACCOUNT_JSON  full JSON key of a service account the sheet is shared with
  SHEET_ID                     the long id from the sheet's URL
"""
import json
import os
import sys
from pathlib import Path

import gspread

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "entries.json"

# Form question titles -> internal keys. Matching is case-insensitive and
# ignores extra words, so "School name" or "Info type (e.g. Curriculum)" still match.
COLUMN_KEYS = [
    ("url", ["url", "link", "web address"]),
    # notes / added_by are checked before school and major so a question like
    # "Why this school?" is treated as a note, not as the school name.
    ("notes", ["note", "why", "comment"]),
    ("added_by", ["your name", "added by", "who"]),
    ("info_type", ["info type", "type of info", "page type"]),
    ("school", ["school", "college", "university"]),
    ("major", ["major", "program"]),
    ("tags", ["tag"]),
    ("timestamp", ["timestamp"]),
]
# data/entries.json is git-ignored: notes and names never reach the public repo.


def match_columns(headers):
    mapping = {}
    for i, h in enumerate(headers):
        low = h.strip().lower()
        for key, needles in COLUMN_KEYS:
            if key in mapping.values():
                continue
            if any(n in low for n in needles):
                mapping[i] = key
                break
    return mapping


def clean(s):
    return " ".join(str(s or "").split())


def main():
    key_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("SHEET_ID")
    if not key_json or not sheet_id:
        sys.exit("GOOGLE_SERVICE_ACCOUNT_JSON and SHEET_ID must be set")

    gc = gspread.service_account_from_dict(json.loads(key_json))
    book = gc.open_by_key(sheet_id)

    rows = book.sheet1.get_all_values()
    if not rows:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text("[]\n")
        return
    mapping = match_columns(rows[0])
    if "url" not in mapping.values():
        sys.exit(f"No URL column found in headers: {rows[0]}")

    aliases = {"school": {}, "major": {}, "info_type": {}}
    try:
        for r in book.worksheet("Aliases").get_all_values()[1:]:
            if len(r) < 3:
                continue
            field = clean(r[0]).lower().replace(" ", "_")
            if field in aliases and clean(r[1]):
                aliases[field][clean(r[1]).lower()] = clean(r[2])
    except gspread.WorksheetNotFound:
        pass

    entries = []
    for n, r in enumerate(rows[1:], start=2):
        e = {key: clean(r[i]) if i < len(r) else "" for i, key in mapping.items()}
        url = e.get("url", "")
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        e["url"] = url
        for field, table in aliases.items():
            val = e.get(field, "")
            e[field] = table.get(val.lower(), val)
        e["tags"] = [t.strip() for t in e.get("tags", "").split(",") if t.strip()]
        e["row"] = n
        entries.append(e)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(entries)} entries written")


if __name__ == "__main__":
    main()

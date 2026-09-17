# College Research

A family hub for comparing college programs, organized by **School → Major → Info Type**.
Each entry is a link to a school's page plus the key text pasted from it, in the school's own words,
with optional notes and tags.

Family members add entries through a Google Form. A GitHub Actions workflow reads the form's
sheet, builds the site, encrypts it with StatiCrypt, and publishes it on GitHub Pages.

```
Google Form ─► Sheet ─► Actions: sheet.py ─► build.py ─► StatiCrypt ─► GitHub Pages
```

| Path | What it is |
|---|---|
| `scripts/sheet.py` | Reads the sheet into `data/entries.json` (never committed) and applies aliases |
| `scripts/build.py` | Builds the readable site into `build/`; the workflow encrypts it into `dist/` |
| `site/index.html` | The viewer page template |
| `.github/workflows/update.yml` | Builds and publishes nightly, on demand, and when the sheet's script triggers it |

## Privacy

The repo is public, but it contains only code. Sheet data (text, notes, names) is read fresh on
every run and exists only inside the run and the encrypted site. The site uses one family
password; "Remember me" keeps each device unlocked for 180 days. The workflow refuses to publish
an unencrypted page, and `noindex`/`robots.txt` are kept as a second layer.

Anyone can download the encrypted page and try passwords offline, so use a long passphrase.

## Setup

### Google Form and Sheet

Questions:

- **URL** (required)
- **School**
- **Major**
- **Info Type** (for example Overview, Curriculum, Admissions, Cost)
- **Key text** (paragraph): text copied from the page
- **Tags** (optional, comma-separated)
- **Notes** (optional, paragraph)
- **Your name** (optional)

Link the Form to a Sheet. Optional second tab named **Aliases** with columns `Field | From | To`
(e.g. `School | UMass | UMass Amherst`) fixes variant spellings at build time.
Once labels settle, turn School and Info Type into dropdowns with an "Other" option.

Share the Sheet (Viewer) with the Google service account's email.

### GitHub

**Settings → Secrets and variables → Actions → Secrets:**

- `GOOGLE_SERVICE_ACCOUNT_JSON`: the service account's JSON key
- `SHEET_ID`: the long string between `/d/` and `/edit` in the sheet URL
- `SITE_PASSWORD`: the family passphrase
- `STATICRYPT_SALT`: 32 hex characters (`openssl rand -hex 16`)

**Settings → Pages:** Source = GitHub Actions.

### Update on each form submission (optional)

An Apps Script on the sheet calls GitHub's workflow-dispatch API on every form submission, and
adds an "Update site now" menu for after editing the sheet directly. It needs a fine-grained
GitHub token limited to this repo with **Actions: Read and write**, stored as the script property
`GITHUB_TOKEN`. Tokens expire, so renew it yearly.

## Everyday use

- **Open the site:** enter the password once per device with "Remember me" checked.
- **Add a page:** fill in the Form. Copy the most useful paragraph or two into Key text.
- **Edit text, notes, or labels:** change them in the sheet, then use *College site → Update site now*.
- **Compare:** open any cell, then use the ‹ › buttons to step through the same info type at other schools.
- **Broken link:** each entry has an *Archived copy* button that opens the Internet Archive's
  most recent snapshot of the page, if one exists.
- **Rows missing School, Major, or Info Type** appear under *Unsorted*.

## Notes

- GitHub disables scheduled workflows in public repos after 60 days without repository activity.
  Manual runs and the sheet's trigger keep working; re-enable the schedule from the Actions tab
  if GitHub emails you about it.
- Changing `SITE_PASSWORD` or `STATICRYPT_SALT` asks every device for the password again.

## Local preview

```bash
pip install -r scripts/requirements.txt
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat service-account.json)" SHEET_ID=...
python scripts/sheet.py && python scripts/build.py
python -m http.server -d build     # readable, local only
```

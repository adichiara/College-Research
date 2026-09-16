# College Research

A family scrapbook of schools' own web pages, organized by **School → Major → Info Type**.

Family members add links through a Google Form. Every night, GitHub Actions reads the
form's sheet, saves a copy of each new page with [SingleFile](https://github.com/gildas-lormeau/SingleFile),
and rebuilds the site on GitHub Pages.

```
Google Form ─► Sheet ─► Actions: vault unlock ─► sheet.py ─► capture.py ─► vault lock + commit
                                  ─► build.py ─► StatiCrypt ─► GitHub Pages
```

## How it's organized

| Path | What it is |
|---|---|
| `scripts/sheet.py` | Reads the sheet (including notes) into `data/entries.json` and applies aliases |
| `scripts/vault.py` | Encrypts/decrypts saved pages so only ciphertext is ever committed |
| `scripts/capture.py` | Saves new pages to `snapshots/<url-id>/<date>.html`, tracks results in `data/captures.json` |
| `scripts/build.py` | Builds the readable site into `build/`; the workflow encrypts it into `dist/` |
| `vault/` | The only data in the repo: encrypted snapshots and capture records |
| `site/index.html` | The viewer page template |
| `.github/workflows/update.yml` | Nightly job, plus a manual button with a "recapture everything" option |

Snapshots are filed by URL, not by school, so fixing a label in the sheet regroups
the site on the next build without recapturing anything.

## Privacy

The repo is public, so nothing readable is ever committed:

- **Sheet data** (notes, names) is read fresh on every run and never committed.
- **Saved pages and capture records** are committed only as AES-GCM ciphertext in `vault/`.
- **The published site** is encrypted with StatiCrypt. Everyone uses one family password,
  and "Remember me" keeps each device unlocked for 180 days. The workflow refuses to publish
  if any page isn't encrypted.
- `noindex` tags and `robots.txt` are kept as a second layer.

Anyone can download the encrypted site and try passwords offline, so use a long passphrase
(four or more random words), not a short family password.

**Keep a copy of `VAULT_KEY` somewhere safe (a password manager).** GitHub won't show a
secret again. If it's lost, the saved pages can't be decrypted, though the sheet survives
and everything can be recaptured.

## One-time setup

### 1. Google Form and Sheet

Create a Form with these questions (plain short-answer for now):

- **URL** (required)
- **School**
- **Major**
- **Info Type** (for example Overview, Curriculum, Admissions, Cost)
- **Tags** (optional, comma-separated)
- **Notes** (optional, paragraph)
- **Your name** (optional)

In the Form's Responses tab, link it to a new Sheet. Copy the Sheet ID: the long string
between `/d/` and `/edit` in the sheet's URL.

Optional: add a second tab named **Aliases** with columns `Field | From | To`, e.g.
`School | UMass | UMass Amherst`. Field is `School`, `Major`, or `Info Type`.

Later, once labels settle, switch School and Info Type to dropdown questions with an "Other" option.

### 2. Google service account

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project.
2. Enable the **Google Sheets API** and **Google Drive API** for it.
3. Under *IAM & Admin → Service Accounts*, create a service account (no roles needed).
4. On its *Keys* tab, add a JSON key and download it.
5. Share the Sheet with the service account's email address (Viewer is enough).

Don't commit the key file. `.gitignore` excludes `service-account*.json` as a safety net.

### 3. GitHub

In the repo's *Settings*:

- **Secrets and variables → Actions → Secrets**
  - `GOOGLE_SERVICE_ACCOUNT_JSON`: the entire contents of the JSON key file
  - `SHEET_ID`: the Sheet ID
  - `SITE_PASSWORD`: the family passphrase
  - `STATICRYPT_SALT`: 32 hex characters, from `python -c "import secrets;print(secrets.token_hex(16))"`
  - `VAULT_KEY`: from `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"`
- **Pages**: Source = **GitHub Actions**
- **Actions → General → Workflow permissions**: Read and write

Then run *Actions → Update site → Run workflow*. The site appears at
`https://adichiara.github.io/College-Research/`.

## Everyday use

- **Opening the site:** enter the family password once per device with "Remember me" checked.
- **Adding pages:** anyone fills in the Form. The page shows up after the next nightly run,
  or run the workflow manually to see it sooner.
- **Notes:** edit or add them in the sheet any time; they appear after the next run.
  Cells with notes show a pencil mark, and search covers notes too.
- **Cleanup:** fix labels directly in the sheet, or add an alias. Rows missing School,
  Major, or Info Type appear under *Unsorted*.
- **Yearly refresh:** run the workflow with *Recapture every page* checked. The site keeps
  the latest and one earlier copy of each page.
- **Failures:** pages that couldn't be saved are listed under *Not saved yet* with the reason.
  Each is retried on up to 3 nightly runs.

- **Changing the password:** update `SITE_PASSWORD` and run the workflow. Everyone re-enters
  the new one. Changing `STATICRYPT_SALT` also logs out every device.

## Local testing

```bash
pip install -r scripts/requirements.txt
npm install -g single-file-cli staticrypt@3
export VAULT_KEY=... GOOGLE_SERVICE_ACCOUNT_JSON="$(cat service-account.json)" SHEET_ID=...
python scripts/vault.py unlock
python scripts/sheet.py
SINGLEFILE_ARGS="--browser-executable-path=/path/to/chrome" python scripts/capture.py
python scripts/build.py
python -m http.server -d build     # readable preview, local only
```

Run `python scripts/vault.py lock` before committing if you captured anything locally,
and never commit `build/`, `data/`, or `snapshots/` (all git-ignored).

## Troubleshooting

- **Every capture fails:** the SingleFile CLI's options change between versions. Run
  `single-file --help` to check flag names. Set a repo *variable* (not secret) named
  `SINGLEFILE_ARGS` to override the defaults without editing code. If Chrome fails to launch
  on the Actions runner, try adding `--browser-args='["--no-sandbox"]'`.
- **A page saves blank or incomplete:** some school sites block automated visits or load
  content only when clicked. Save that page by hand with the SingleFile browser extension,
  then locally: `vault.py unlock`, put the file at `snapshots/<url-id>/<date>.html`,
  add its entry to `data/captures.json`, `vault.py lock`, and commit `vault/`.
- **Repo getting large:** each snapshot is typically a few MB, and the encrypted site copy
  is roughly a third larger again. Only two versions per page are kept, but git history keeps old ones; GitHub recommends repos stay under about 1 GB.

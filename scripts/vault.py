"""Keep snapshots and capture records encrypted in the (public) repo.

    python scripts/vault.py unlock   # vault/**.enc  ->  readable working files
    python scripts/vault.py lock     # changed working files -> vault/**.enc

Readable files (snapshots/, data/captures.json) are git-ignored and only exist
inside a workflow run or on your machine. Only changed files are re-encrypted,
so git history grows by new or updated pages, not the whole collection.

Environment:
  VAULT_KEY  base64 of 32 random bytes  (python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())")
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "vault"
MANIFEST = ROOT / ".vault-manifest.json"   # hashes at unlock time (git-ignored)
TRACKED_DIRS = ["snapshots"]
TRACKED_FILES = ["data/captures.json"]


def key():
    k = os.environ.get("VAULT_KEY")
    if not k:
        sys.exit("VAULT_KEY is not set")
    raw = base64.b64decode(k)
    if len(raw) != 32:
        sys.exit("VAULT_KEY must be base64 of exactly 32 bytes")
    return AESGCM(raw)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def working_files():
    files = [ROOT / f for f in TRACKED_FILES if (ROOT / f).exists()]
    for d in TRACKED_DIRS:
        files += [p for p in (ROOT / d).rglob("*") if p.is_file() and p.name != ".gitkeep"]
    return {p.relative_to(ROOT).as_posix(): p for p in files}


def unlock():
    aes = key()
    manifest = {}
    for enc in VAULT.rglob("*.enc"):
        rel = enc.relative_to(VAULT).as_posix()[:-4]
        blob = enc.read_bytes()
        data = aes.decrypt(blob[:12], blob[12:], rel.encode())
        out = ROOT / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        manifest[rel] = sha(data)
    MANIFEST.write_text(json.dumps(manifest))
    print(f"unlocked {len(manifest)} files")


def lock():
    aes = key()
    before = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    current = working_files()
    written = removed = 0
    for rel, path in current.items():
        data = path.read_bytes()
        if before.get(rel) == sha(data):
            continue
        nonce = os.urandom(12)
        enc = VAULT / (rel + ".enc")
        enc.parent.mkdir(parents=True, exist_ok=True)
        # The file's path is bound in as associated data, so encrypted files can't be swapped around.
        enc.write_bytes(nonce + aes.encrypt(nonce, data, rel.encode()))
        written += 1
    for rel in set(before) - set(current):
        (VAULT / (rel + ".enc")).unlink(missing_ok=True)
        removed += 1
    for d in sorted(VAULT.rglob("*"), reverse=True):   # tidy empty folders
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    MANIFEST.write_text(json.dumps({r: sha(p.read_bytes()) for r, p in current.items()}))
    print(f"locked: {written} written, {removed} removed")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"unlock": unlock, "lock": lock}.get(cmd, lambda: sys.exit("usage: vault.py unlock|lock"))()

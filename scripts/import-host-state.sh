#!/usr/bin/env bash
# import-host-state.sh (v2) — verify and restore a host-state archive safely.
#
# Safety guarantees:
#   * validates manifest digest syntax and rejects duplicate paths;
#   * rejects absolute paths and any `..` traversal in manifest entries;
#   * rejects symlinks and non-regular files anywhere in the archive;
#   * refuses to write through a pre-existing symlinked parent directory;
#   * verifies every SHA-256 and the archive metadata schema / secret policy;
#   * never advances a bridge/campaign sequence (it only lays down files).
#
# Usage: scripts/import-host-state.sh <archive-dir> [--dry-run] [--accept-secrets]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="${PYTHON:-python3}"
eval "$(PYTHON="$PY" "$REPO/scripts/stack-paths.sh" export)"

ARCHIVE=""
DRY_RUN=0
ACCEPT_SECRETS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --accept-secrets) ACCEPT_SECRETS=1; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) ARCHIVE="$1"; shift ;;
  esac
done
[ -n "$ARCHIVE" ] || { echo "usage: import-host-state.sh <archive-dir> [--dry-run] [--accept-secrets]" >&2; exit 2; }
[ -d "$ARCHIVE" ] || { echo "not a directory: $ARCHIVE" >&2; exit 2; }

echo "import-host-state.sh <- $ARCHIVE  (dry_run=$DRY_RUN accept_secrets=$ACCEPT_SECRETS)"

"$PY" - "$ARCHIVE" "$STACK_STATE_ROOT" "$STACK_CONFIG_ROOT" "$STACK_DATA_ROOT" "$HERMES_HOME" "$DRY_RUN" "$ACCEPT_SECRETS" <<'PY'
import hashlib, json, os, re, shutil, sys

(archive, state_root, config_root, data_root, hermes_home, dry_run, accept_secrets) = sys.argv[1:8]
dry_run = bool(int(dry_run))
accept_secrets = bool(int(accept_secrets))

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
MAP = {
    "state/": state_root,
    "config/": config_root,
    "artifacts/": os.path.join(data_root, "artifacts"),
    "secrets/": hermes_home,
}

# ---- metadata schema / secret policy -------------------------------------- #
meta_path = os.path.join(archive, "metadata.json")
if not os.path.isfile(meta_path):
    print("FATAL: no metadata.json in archive", file=sys.stderr); sys.exit(3)
meta = json.load(open(meta_path, encoding="utf-8"))
if meta.get("schema") != "STACK_HOST_STATE_EXPORT_V1":
    print("FATAL: unexpected archive schema: %r" % meta.get("schema"), file=sys.stderr); sys.exit(3)

manifest_path = os.path.join(archive, "manifest.sha256")
if not os.path.isfile(manifest_path):
    print("FATAL: no manifest.sha256 in archive", file=sys.stderr); sys.exit(3)

# ---- reject symlinks / non-regular files anywhere in the archive ---------- #
for dirpath, dirs, files in os.walk(archive, followlinks=False):
    for d in list(dirs):
        p = os.path.join(dirpath, d)
        if os.path.islink(p):
            print("FATAL: symlink in archive: %s" % p, file=sys.stderr); sys.exit(4)
    for f in files:
        p = os.path.join(dirpath, f)
        if os.path.islink(p):
            print("FATAL: symlink in archive: %s" % p, file=sys.stderr); sys.exit(4)
        if not os.path.isfile(p):
            print("FATAL: non-regular file in archive: %s" % p, file=sys.stderr); sys.exit(4)

# ---- parse + validate the manifest ---------------------------------------- #
entries = []
seen = set()
for raw in open(manifest_path, encoding="utf-8"):
    raw = raw.strip()
    if not raw:
        continue
    digest, sep, rel = raw.partition("  ")
    if not sep or not DIGEST_RE.match(digest):
        print("FATAL: malformed manifest line: %r" % raw, file=sys.stderr); sys.exit(5)
    rel_posix = rel.replace("\\", "/")
    if rel_posix.startswith("/") or os.path.isabs(rel):
        print("FATAL: absolute path in manifest: %r" % rel, file=sys.stderr); sys.exit(5)
    norm = os.path.normpath(rel)
    if norm.startswith("..") or os.path.isabs(norm):
        print("FATAL: path traversal in manifest: %r" % rel, file=sys.stderr); sys.exit(5)
    if rel_posix in seen:
        print("FATAL: duplicate manifest path: %r" % rel, file=sys.stderr); sys.exit(5)
    seen.add(rel_posix)
    src = os.path.join(archive, norm)
    if not os.path.isfile(src):
        print("FATAL: manifest entry missing on disk: %s" % rel, file=sys.stderr); sys.exit(6)
    h = hashlib.sha256()
    with open(src, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != digest:
        print("FATAL: checksum mismatch for %s" % rel, file=sys.stderr); sys.exit(7)
    entries.append((norm, src, rel_posix))

# ---- restore --------------------------------------------------------------- #
def under(child_real, parent_real):
    return child_real == parent_real or child_real.startswith(parent_real + os.sep)

restored = 0
for norm, src, rel_posix in entries:
    top = rel_posix.split("/", 1)[0] + "/"
    if top == "secrets/":
        if not accept_secrets:
            continue
        if not meta.get("includes_secrets"):
            print("FATAL: secrets/ present but metadata says includes_secrets=false", file=sys.stderr)
            sys.exit(8)
    if top not in MAP:
        print("FATAL: unmapped archive subtree: %s" % rel_posix, file=sys.stderr); sys.exit(9)
    root_real = os.path.realpath(MAP[top])
    dest = os.path.join(MAP[top], norm[len(top):])
    parent = os.path.dirname(dest)
    # Refuse to write through a pre-existing symlinked parent that escapes the mapped root.
    parent_real = os.path.realpath(parent)
    if os.path.exists(parent) and not under(parent_real, root_real):
        print("FATAL: destination parent escapes the mapped root (symlink?): %s" % parent,
              file=sys.stderr); sys.exit(10)
    if dry_run:
        restored += 1
        continue
    os.makedirs(parent, exist_ok=True)
    if not under(os.path.realpath(parent), root_real):
        print("FATAL: destination parent escapes the mapped root after mkdir: %s" % parent,
              file=sys.stderr); sys.exit(10)
    shutil.copyfile(src, dest)
    mode = 0o600 if (top == "secrets/" or dest.endswith((".env", ".key", ".pem"))) else 0o644
    os.chmod(dest, mode)
    try:
        os.chmod(parent, 0o700 if top in ("state/", "secrets/") else 0o755)
    except OSError:
        pass
    restored += 1

print("verified=%d restored=%d" % (len(entries), restored))
print("NOTE: campaign/bridge sequences are NOT advanced by import; state files are restored verbatim.")
PY

if [ "$DRY_RUN" = "1" ]; then echo "import-host-state.sh: DRY RUN complete"; else echo "import-host-state.sh: OK"; fi

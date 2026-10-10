#!/usr/bin/env bash
# export-host-state.sh (v2) — checksummed migration archive written OUTSIDE the project.
#
# Safety:
#   * refuses a destination inside the project tree;
#   * requires a new or empty destination (no stale files can leak into the manifest);
#   * does not follow symlinks or non-regular files (skipped and recorded, never archived);
#   * secrets are excluded unless --include-secrets (a clearly separated `secrets/` subtree).
#
# Usage: scripts/export-host-state.sh [--include-secrets] [--with-artifacts] [--dest DIR]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="${PYTHON:-python3}"
eval "$(PYTHON="$PY" "$REPO/scripts/stack-paths.sh" export)"

INCLUDE_SECRETS=0
WITH_ARTIFACTS=0
DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --include-secrets) INCLUDE_SECRETS=1; shift ;;
    --with-artifacts) WITH_ARTIFACTS=1; shift ;;
    --dest) DEST="$2"; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

TS="$(date -u +%Y%m%dT%H%M%SZ)"
[ -n "$DEST" ] || DEST="$STACK_MIGRATION_ARCHIVE_ROOT/host-state-$TS"

"$PY" - "$DEST" "$REPO" "$INCLUDE_SECRETS" "$WITH_ARTIFACTS" "$TS" \
        "$STACK_STATE_ROOT" "$STACK_DATA_ROOT" "$STACK_CONFIG_ROOT" "$HERMES_HOME" <<'PY'
import hashlib, json, os, shutil, sys

(dest, repo, include_secrets, with_artifacts, ts,
 state_root, data_root, config_root, hermes_home) = sys.argv[1:10]
include_secrets = bool(int(include_secrets))
with_artifacts = bool(int(with_artifacts))

dest_real = os.path.realpath(dest)
repo_real = os.path.realpath(repo)
if dest_real == repo_real or dest_real.startswith(repo_real + os.sep):
    print("FATAL: export destination is inside the project tree: %s" % dest, file=sys.stderr)
    sys.exit(3)
if os.path.exists(dest) and os.path.isdir(dest) and os.listdir(dest):
    print("FATAL: export destination is not empty: %s" % dest, file=sys.stderr)
    sys.exit(4)
os.makedirs(dest, mode=0o700, exist_ok=True)

# archive-relative source tree -> absolute source root
TREES = [
    ("state/bridge", os.path.join(state_root, "bridge")),
    ("state/supervisor", os.path.join(state_root, "supervisor")),
    ("state/browser", os.path.join(state_root, "browser")),
    ("state/telemetry", os.path.join(state_root, "telemetry")),
    ("state/guard", os.path.join(state_root, "guard")),
    ("config", config_root),
]
if with_artifacts:
    TREES.append(("artifacts", os.path.join(data_root, "artifacts")))

manifest = []
skipped = {"symlinks": 0, "non_regular": 0}
copy_bytes = 0

for dest_rel, src_root in TREES:
    if not os.path.isdir(src_root):
        continue
    for dirpath, dirs, files in os.walk(src_root, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(dirpath, d))]
        for name in files:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                skipped["symlinks"] += 1
                continue
            if not os.path.isfile(full):
                skipped["non_regular"] += 1
                continue
            rel = os.path.relpath(full, src_root)
            rid = os.path.join(dest_rel, rel)
            out = os.path.join(dest, rid)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(full, out)
            h = hashlib.sha256()
            with open(out, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            manifest.append((rid.replace(os.sep, "/"), h.hexdigest()))
            copy_bytes += os.path.getsize(out)

if include_secrets:
    for f in (os.path.join(hermes_home, ".env"),
              os.path.join(hermes_home, "profiles", "android-stack", ".env")):
        if not os.path.isfile(f) or os.path.islink(f):
            continue
        rel = "secrets/hermes/" + os.path.relpath(f, hermes_home)
        out = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(f, out)
        os.chmod(out, 0o600)
        h = hashlib.sha256()
        with open(out, "rb") as fh:
            h.update(fh.read())
        manifest.append((rel.replace(os.sep, "/"), h.hexdigest()))
    os.chmod(os.path.join(dest, "secrets"), 0o700)

manifest.sort(key=lambda x: x[0])
with open(os.path.join(dest, "manifest.sha256"), "w", encoding="utf-8") as fh:
    fh.write("\n".join("%s  %s" % (h, p) for p, h in manifest) + "\n")
meta = {
    "schema": "STACK_HOST_STATE_EXPORT_V1",
    "exported_at_utc": ts,
    "includes_secrets": include_secrets,
    "includes_artifacts": with_artifacts,
    "file_count": len(manifest),
    "bytes": copy_bytes,
    "symlink_policy": "skipped (never archived)",
    "skipped": skipped,
}
with open(os.path.join(dest, "metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta, fh, indent=2, sort_keys=True)
    fh.write("\n")
print("export-host-state: dest=%s files=%d bytes=%d skipped=%s"
      % (dest, len(manifest), copy_bytes, skipped))
PY

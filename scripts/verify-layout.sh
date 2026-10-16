#!/usr/bin/env bash
# verify-layout.sh (v2) — fail when generated outputs or absolute host paths reappear.
#
# Modes:
#   (default) project audit over a project tree (--root, default this checkout):
#       A. path-specific generated artifact roots / files;
#       B. absolute host paths (/home/<user>, /mnt/AndroidDev) in live executable source.
#   --projects-root DIR : audit the immediate children of a Projects root and report
#       output-only sibling directories separately.
#
# Detection is path-specific / classification-driven: a directory is never rejected merely
# because its basename is `evidence` (e.g. verification/android/evidence/layout.sh is source).
# Exceptions live in scripts/layout-allowlist.txt.
#
# Usage: scripts/verify-layout.sh [--root DIR] [--projects-root DIR] [--allowlist FILE] [--quiet]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="${PYTHON:-python3}"

ROOT="$REPO"
QUIET=0
ALLOWLIST="$HERE/layout-allowlist.txt"
PROJECTS_ROOT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --projects-root) PROJECTS_ROOT="$2"; shift 2 ;;
    --allowlist) ALLOWLIST="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -n "$PROJECTS_ROOT" ]; then
"$PY" - "$PROJECTS_ROOT" "$QUIET" <<'PY'
import os, sys

projects_root, quiet = sys.argv[1], bool(int(sys.argv[2]))
# Known output-only siblings of a Projects root (classification-driven, not basename-based).
OUTPUT_ONLY = {
    "_evaluation": ("PERSISTENT_ARTIFACT", "shared evaluation/Auto-Finalizer output root"),
    "KeepLab-Relay-evidence": ("PERSISTENT_ARTIFACT", "product run evidence for KeepLab-Relay"),
}
# Repositories / product trees that are NOT this stack's output.
KNOWN_PROJECTS = {"Google-Android-Agent-Development-Stack"}  # KeepLab lives under AppProjects
KNOWN_TOOLCHAINS = {"AI-Engineering-Governance-Layer", "AI-System-Bakeoff", "Archon-AI-Software-Factory",
                    "BMAD-Method-TEA", "GitHub-Spec-Kit", "Program"}

def count(path):
    files = 0
    bytes_ = 0
    for dirpath, _d, names in os.walk(path):
        for n in names:
            files += 1
            try:
                bytes_ += os.path.getsize(os.path.join(dirpath, n))
            except OSError:
                pass
    return files, bytes_

siblings = []
for name in sorted(os.listdir(projects_root)):
    full = os.path.join(projects_root, name)
    if not os.path.isdir(full):
        continue
    if name in OUTPUT_ONLY:
        cls, reason = OUTPUT_ONLY[name]
        f, b = count(full)
        siblings.append((name, cls, reason, f, b, True))
    else:
        cls = "PROJECT" if name in KNOWN_PROJECTS else ("TOOLCHAIN" if name in KNOWN_TOOLCHAINS else "OTHER")
        siblings.append((name, cls, "", 0, 0, False))

n_out = 0
if not quiet:
    for name, cls, reason, f, b, out in siblings:
        if out:
            n_out += 1
            print("PROJECTS_OUTPUT_SIBLING %s class=%s files=%d bytes=%d reason=%s"
                  % (name, cls, f, b, reason))
        else:
            print("PROJECTS_SIBLING %s class=%s" % (name, cls))
print("verify-layout(projects-root): output_only_siblings=%d under %s" % (n_out, projects_root))
sys.exit(1 if n_out else 0)
PY
exit $?
fi

"$PY" - "$ROOT" "$ALLOWLIST" "$QUIET" <<'PY'
import fnmatch, os, re, sys

root, allowlist_file, quiet = sys.argv[1], sys.argv[2], bool(int(sys.argv[3]))

# ---- A. path-specific generated roots (never basename "evidence") ---------- #
GENERATED_ROOT_RELS = (
    "orchestration/hermes/evidence",
    "orchestration/hermes/runtime",
    "verification/.runs",
    "verification/.state",
    "verification/reference-replay/.runs",
    "verification/reference-replay/.state",
    "verification-benchmark/results",
    "verification-benchmark/reports/hardening",
    "verification-benchmark/harness/.state",
    "reports/migration-recovery",
    "reports/evidence",
)
CACHE_BASENAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                   ".gradle", ".venv", "venv", "env", "node_modules"}
SKIP_WALK = {".git"}

def is_generated_dir(rel, parts):
    if rel in GENERATED_ROOT_RELS:
        return True
    if any(p in CACHE_BASENAMES for p in parts):
        return True
    if parts and parts[-1] in ("build", "outputs") and "probes" in parts:
        return True
    return False

def is_generated_file(rel):
    base = os.path.basename(rel)
    if base.endswith((".pyc", ".pyo")):
        return True
    if base == "local.properties":
        return True
    if base.endswith(".apk") or base.endswith(".aab"):
        return True
    if rel.startswith("verification-benchmark/results/"):
        return True
    return False

def dir_size(path):
    files = bytes_ = 0
    for dp, _d, names in os.walk(path):
        for n in names:
            files += 1
            try:
                bytes_ += os.path.getsize(os.path.join(dp, n))
            except OSError:
                pass
    return files, bytes_

# ---- B. absolute host paths in live source -------------------------------- #
HOST_RE = re.compile(r"/home/[A-Za-z0-9._-]+/|/mnt/AndroidDev")
SCAN_EXT = (".py", ".sh", ".bash", ".kt", ".kts", ".gradle", ".properties", ".toml", ".cfg", ".json", ".yaml", ".yml")
EXCLUDE_DIRS = ("reference", "references", "evidence", "reports", "node_modules", ".git",
                ".runs", "__pycache__", "build", "docs")

def load_allowlist():
    pats = []
    if not os.path.isfile(allowlist_file):
        return pats
    for line in open(allowlist_file, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pats.append(line.split()[0])
    return pats

ALLOW = load_allowlist()

def allowed(rel):
    rel = rel.replace(os.sep, "/")
    return any(fnmatch.fnmatch(rel, p) for p in ALLOW)

roots = []           # (rel, files, bytes)
files_violations = []
host_paths = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in SKIP_WALK]
    rel_dir = os.path.relpath(dirpath, root)
    rel_dir = "" if rel_dir == "." else rel_dir
    for d in list(dirnames):
        rel = os.path.join(rel_dir, d).replace(os.sep, "/")
        if is_generated_dir(rel, rel.split("/")):
            if allowed(rel):
                continue
            f, b = dir_size(os.path.join(dirpath, d))
            roots.append((rel, f, b))
            dirnames.remove(d)
    for fname in filenames:
        rel = os.path.join(rel_dir, fname).replace(os.sep, "/")
        if is_generated_file(rel):
            if not allowed(rel):
                files_violations.append(rel)
                try:
                    roots.append((rel, 1, os.path.getsize(os.path.join(root, rel))))
                except OSError:
                    roots.append((rel, 1, 0))
            continue
        if not rel.endswith(SCAN_EXT):
            continue
        parts = rel.split("/")
        if parts[0] in EXCLUDE_DIRS or any(p in EXCLUDE_DIRS for p in parts[:-1]):
            continue
        if allowed(rel):
            continue
        try:
            text = open(os.path.join(root, rel), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for m in HOST_RE.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            host_paths.append("%s:%d %s" % (rel, line_no, m.group(0)))
            break

total_files = sum(r[1] for r in roots)
total_bytes = sum(r[2] for r in roots)
n_viol = len(roots) + len(host_paths)

if not quiet:
    for rel, f, b in roots:
        print("VIOLATION GENERATED_ROOT %s files=%d bytes=%d" % (rel, f, b))
    for hp in host_paths:
        print("VIOLATION HOST_PATH      %s" % hp)
print("verify-layout: roots=%d files=%d bytes=%d host_paths=%d violations=%d under %s"
      % (len(roots), total_files, total_bytes, len(host_paths), n_viol, root))
sys.exit(1 if n_viol else 0)
PY

#!/usr/bin/env python3
"""Device-lock exclusivity test (stdlib only).

Proves the host-level device lock is exclusive: while one holder owns
device:<serial>, a second acquire (non-blocking) fails with DEVICE_BUSY, and after
release it succeeds. Uses verification/core/device_lock.sh through bash.
"""
import os
import fcntl
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOCK_SH = os.path.join(ROOT, "core", "device_lock.sh")
LIB = os.path.join(ROOT, "core", "lib_common.sh")
SERIAL = "87296ada"


def probe(lock_dir: str, wait: int) -> subprocess.CompletedProcess:
    snippet = (
        f'set -euo pipefail; source "{LIB}"; source "{LOCK_SH}"; '
        f'device_lock_acquire "{SERIAL}" {wait} "{lock_dir}" && echo OK'
    )
    return subprocess.run(["bash", "-c", snippet], capture_output=True, text=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        lock_dir = os.path.join(d, "locks")
        os.makedirs(lock_dir)
        lock_path = os.path.join(lock_dir, f"device-{SERIAL}.lock")

        # Hold the lock from this process.
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)

        second = probe(lock_dir, 0)
        if second.returncode == 0:
            print("FAIL: second acquire succeeded while lock held")
            print(second.stdout, second.stderr)
            return 1
        if "DEVICE_BUSY" not in second.stderr:
            print("FAIL: second acquire did not report DEVICE_BUSY")
            print(second.stderr)
            return 1
        print("ok: second acquire -> DEVICE_BUSY")

        # Release, then acquire must succeed.
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        third = probe(lock_dir, 0)
        if third.returncode != 0 or "OK" not in third.stdout:
            print("FAIL: acquire after release did not succeed")
            print(third.stdout, third.stderr)
            return 1
        print("ok: acquire after release -> OK")
    print("DEVICE_LOCK_TEST=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

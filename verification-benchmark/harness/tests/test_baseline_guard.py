#!/usr/bin/env python3
"""Frozen-baseline invariants tests (P1 #18 guard)."""
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
import baseline_guard as bg  # noqa: E402


class TestBaselineGuard(unittest.TestCase):
    def test_reduction_pct(self):
        self.assertEqual(bg.reduction_pct(1626352, 55409), 96.6)
        self.assertEqual(bg.reduction_pct(1626352, 172679), 89.4)
        self.assertIsNone(bg.reduction_pct(None, 1))
        self.assertIsNone(bg.reduction_pct(0, 1))

    def test_sha256_stable(self):
        p = Path(tempfile.mkdtemp()) / "x"
        p.write_text("hello")
        self.assertEqual(
            bg.sha256(p),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

    @unittest.skipUnless(bg.MANIFEST.exists(),
                         "frozen baseline dataset absent (generated-output-free copy)")
    def test_frozen_baseline_intact(self):
        """The real frozen baseline must satisfy every invariant (and be unchanged)."""
        rc = bg.main()
        self.assertEqual(rc, 0, "baseline_guard reported a violation")


if __name__ == "__main__":
    unittest.main(verbosity=2)

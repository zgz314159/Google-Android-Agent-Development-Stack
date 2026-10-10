#!/usr/bin/env python3
"""Project bootstrap tests (Verification Layer v1.0.1).

fresh -> INSTALL; second run -> NO-OP (no duplicate dependency, no rewrite);
template drift -> INTEGRATION_DRIFT (never silently overwritten).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFY = Path(__file__).resolve().parents[2]
BOOTSTRAP = VERIFY / "integration/android-project/bootstrap_project.py"
PKG_DIR = "app/src/androidTest/java/dev/androidstack/verification"


def make_project() -> Path:
    root = Path(tempfile.mkdtemp()) / "proj"
    (root / "app/src/main").mkdir(parents=True)
    (root / "app/src/main/AndroidManifest.xml").write_text(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
        'package="com.example.demo"/>')
    (root / "app/build.gradle.kts").write_text(
        'plugins {\n    id("com.android.application")\n}\n\n'
        'android {\n    namespace = "com.example.demo"\n}\n\n'
        'dependencies {\n    implementation("androidx.core:core-ktx:1.0.0")\n}\n')
    return root


def run_bootstrap(root: Path, *extra):
    r = subprocess.run([sys.executable, str(BOOTSTRAP), "--project", str(root), "--json", *extra],
                       capture_output=True, text=True)
    diag = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    return r, diag


class TestBootstrap(unittest.TestCase):
    def test_fresh_install(self):
        root = make_project()
        r, diag = run_bootstrap(root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(diag["status"], "INSTALL")
        for name in ("TimingLogger.kt", "JourneyBase.kt", "UiDriver.kt", "FailureBundleRule.kt"):
            self.assertTrue((root / PKG_DIR / name).is_file(), name)
        self.assertEqual(diag["dependency"]["action"], "ADDED")
        self.assertIn("androidx.test.uiautomator:uiautomator",
                      (root / "app/build.gradle.kts").read_text())
        self.assertTrue((root / ".verification/integration-manifest.json").is_file())

    def test_second_run_is_idempotent_noop(self):
        root = make_project()
        run_bootstrap(root)
        before = (root / "app/build.gradle.kts").read_text()
        r2, diag2 = run_bootstrap(root)
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(diag2["status"], "NO-OP")
        self.assertEqual(diag2["dependency"]["action"], "PRESENT")
        after = (root / "app/build.gradle.kts").read_text()
        self.assertEqual(before, after)
        self.assertEqual(after.count("androidx.test.uiautomator"), 1)

    def test_drift_detected_not_overwritten(self):
        root = make_project()
        run_bootstrap(root)
        target = root / PKG_DIR / "JourneyBase.kt"
        target.write_text("// project-local edit\n")
        r, diag = run_bootstrap(root)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(diag["status"], "INTEGRATION_DRIFT")
        self.assertTrue(any("JourneyBase.kt" in d["file"] for d in diag["drift"]))
        # never silently overwritten
        self.assertEqual(target.read_text(), "// project-local edit\n")

    def test_invalid_project(self):
        root = Path(tempfile.mkdtemp()) / "empty"
        root.mkdir()
        r, diag = run_bootstrap(root)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(diag["status"], "INVALID_PROJECT")

    def test_does_not_add_duplicate_when_alias_present(self):
        root = make_project()
        (root / "app/build.gradle.kts").write_text(
            'dependencies {\n    androidTestImplementation(libs.androidx.test.uiautomator)\n}\n')
        r, diag = run_bootstrap(root)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(diag["dependency"]["action"], "PRESENT")
        text = (root / "app/build.gradle.kts").read_text()
        self.assertEqual(text.count("uiautomator"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

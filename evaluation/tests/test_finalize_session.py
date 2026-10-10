#!/usr/bin/env python3
"""End-to-end Auto-Finalizer regression (task-window v0.2.1 + finalize_session).

Proves the full loop:
  task prompt -> work -> continuation -> plan approval -> device smoke
  -> terminal completion -> Auto-Finalizer triggered -> Evaluation generated
  -> later independent prompt does NOT re-open / pollute the first Evaluation.

Also proves: finalize runs once, outputs are atomic, the raw JSONL is never
modified, and a task outcome is never rewritten by an Evaluation failure.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "commandcode"))
import finalize_session  # noqa: E402
import auto_finalize  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "task_window_v021.jsonl")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_lines():
    with open(FIXTURE, encoding="utf-8") as f:
        return [l for l in f if l.strip()]


def write_session(root, slug, name, lines):
    d = os.path.join(root, slug)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l if l.endswith("\n") else l + "\n")
    return path


class FinalizerE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.projects = os.path.join(self.tmp, "projects")
        self.out = os.path.join(self.tmp, "evaluation")
        os.makedirs(self.projects)
        os.makedirs(self.out)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- helpers -------------------------------------------------------- #
    def _scan(self, **kw):
        return auto_finalize.scan(self.projects, self.out, stable_seconds=0.0,
                                  project="proj", **kw)

    def _run_json(self, run_id):
        return os.path.join(self.out, "proj", run_id, "run.json")

    # 1. full completion -> finalize -> artifacts
    def test_finalize_produces_artifacts_after_completion(self):
        lines = load_lines()  # fixture already includes a later independent task B
        path = write_session(self.projects, "slug", "s1.jsonl", lines)
        raw_before = sha256(path)

        results = self._scan()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "SUCCESS")
        run_id = results[0]["run_id"]
        final_dir = os.path.join(self.out, "proj", run_id)
        for name in ("run.json", "phase-timeline.csv", "analysis.md", "finalization.json"):
            self.assertTrue(os.path.exists(os.path.join(final_dir, name)), name)

        fin = load_json(os.path.join(final_dir, "finalization.json"))
        self.assertTrue(fin["finalized"])
        self.assertTrue(fin["task_completion_detected"])
        self.assertEqual(fin["evaluation_core_version"], "0.2.3")
        self.assertFalse(fin["raw_jsonl_modified"])
        self.assertEqual(fin["task_outcome"], "COMPLETED")
        self.assertEqual(fin["evaluation_outcome"], "SUCCESS")

        # raw JSONL untouched
        self.assertEqual(raw_before, sha256(path))
        # no half-written tmp dir left behind
        self.assertFalse(os.path.exists(final_dir + ".tmp"))

    # 2. later independent task does not enter the first Evaluation
    def test_later_independent_task_excluded(self):
        lines = load_lines()
        path = write_session(self.projects, "slug", "s1.jsonl", lines)
        results = self._scan()
        run = load_json(self._run_json(results[0]["run_id"]))
        tw = run["task_window"]
        self.assertEqual(tw["excluded_independent_tasks"], 1)   # task B
        self.assertEqual(tw["in_task_continuations"], 2)        # steering pings
        # completion is task A's, not task B's
        self.assertEqual(run["task_completion"]["final_assistant_row"], 21)
        self.assertNotIn("TASK-B", run["task_completion"]["evidence"])

    # 3. append a later task after finalize -> ALREADY_FINALIZED, first run unchanged
    def test_idempotent_after_later_append(self):
        lines = load_lines()
        task_a = lines[:23]      # session + prompt + work + terminal completion
        task_b = lines[23:]      # p2 + a11
        path = write_session(self.projects, "slug", "s1.jsonl", task_a)

        first = self._scan()
        self.assertEqual(first[0]["status"], "SUCCESS")
        run_id = first[0]["run_id"]
        run_json = self._run_json(run_id)
        run_sha_before = sha256(run_json)

        # a genuinely independent task arrives later in the same session file
        with open(path, "a", encoding="utf-8") as f:
            for l in task_b:
                f.write(l if l.endswith("\n") else l + "\n")
        raw_after_append = sha256(path)

        second = self._scan()
        self.assertEqual(second[0]["status"], "ALREADY_FINALIZED")
        # the first Evaluation is untouched and still scoped to task A
        self.assertEqual(run_sha_before, sha256(run_json))
        run = load_json(run_json)
        self.assertEqual(run["task_completion"]["final_assistant_row"], 21)
        # and the raw JSONL was never written by the finalizer
        self.assertEqual(raw_after_append, sha256(path))

        # third scan with no change is a cheap stat-only skip
        third = self._scan()
        self.assertEqual(third[0]["status"], "SKIP_UNCHANGED")

    # 4. force overwrites exactly once
    def test_force_overwrites(self):
        lines = load_lines()
        write_session(self.projects, "slug", "s1.jsonl", lines)
        first = self._scan()
        run_id = first[0]["run_id"]
        forced = finalize_session.finalize(session_path=os.path.join(self.projects, "slug", "s1.jsonl"),
                                           project="proj", output_root=self.out,
                                           run_id=run_id, force=True)
        self.assertEqual(forced["evaluation_outcome"], "SUCCESS")
        self.assertFalse(os.path.exists(os.path.join(self.out, "proj", run_id + ".tmp")))

    # 5. an active (recently written) session is not finalized
    def test_active_session_skipped(self):
        lines = load_lines()
        write_session(self.projects, "slug", "s1.jsonl", lines)
        results = auto_finalize.scan(self.projects, self.out, stable_seconds=3600.0, project="proj")
        self.assertEqual(results[0]["status"], "SKIP_ACTIVE")

    # 6. evaluation failure never rewrites the task outcome
    def test_task_evaluation_outcome_isolation(self):
        d = os.path.join(self.projects, "slug")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "s1.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "session", "version": 99, "id": "x",
                                "timestamp": "2026-10-03T14:00:00.000Z", "cwd": "/p"}) + "\n")
            f.write(json.dumps({"type": "message", "id": "p", "timestamp": "2026-10-03T14:00:01.000Z",
                                "message": {"role": "user",
                                            "content": [{"type": "text", "text": "task"}]}}) + "\n")
        diag = finalize_session.finalize(session_path=path, project="proj", output_root=self.out)
        self.assertEqual(diag["evaluation_outcome"], "FAIL")
        self.assertNotEqual(diag["task_outcome"], "FAIL")
        self.assertFalse(diag["finalized"])
        self.assertIsNotNone(diag["evaluation_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

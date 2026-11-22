#!/usr/bin/env python3
"""Control URL resolution + per-project map binding."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRIDGE_DIR))

import chatgpt_adapter as adapter  # noqa: E402

ENV_VAR = "HERMES_CHATGPT_CONTROL_URL"
PC = Path.home() / ".local/share/aegl-dual-link/project_control.py"


def _load_pc():
    spec = importlib.util.spec_from_file_location("project_control", PC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ResolveControlUrl(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop(ENV_VAR, None)

    def tearDown(self):
        if self._saved is not None:
            os.environ[ENV_VAR] = self._saved
        else:
            os.environ.pop(ENV_VAR, None)

    def test_unset_defaults_to_pinned(self):
        self.assertEqual(adapter._resolve_control_url(), adapter._DEFAULT_CONTROL_URL)

    def test_valid_override(self):
        url = "https://chatgpt.com/c/11111111-2222-3333-4444-555555555555"
        self.assertEqual(adapter._resolve_control_url(url), url)
        os.environ[ENV_VAR] = url
        self.assertEqual(adapter.active_control_url(), url)

    def test_invalid_raises(self):
        with self.assertRaises(adapter.AdapterError):
            adapter._resolve_control_url("https://chat.openai.com/c/abc")


class ProjectMap(unittest.TestCase):
    def setUp(self):
        self.pc = _load_pc()
        self.tmp = tempfile.TemporaryDirectory()
        self.map = Path(self.tmp.name) / "map.json"
        os.environ[self.pc.ENV_MAP] = str(self.map)
        self._url = os.environ.pop(ENV_VAR, None)

    def tearDown(self):
        os.environ.pop(self.pc.ENV_MAP, None)
        if self._url is not None:
            os.environ[ENV_VAR] = self._url
        self.tmp.cleanup()

    def test_require_binding_unmapped(self):
        self.map.write_text(json.dumps({"require_binding": True, "projects": {}, "by_aegl_project": {}}))
        with self.assertRaises(self.pc.ControlBindError):
            self.pc.resolve_control_url(cwd="/tmp/unbound-proj", allow_env=False)

    def test_cwd_prefix_and_aegl(self):
        url = "https://chatgpt.com/c/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        root = Path(self.tmp.name) / "proj"
        root.mkdir()
        self.pc.bind_control(cwd=str(root), url=url, aegl_project="DemoProj")
        self.assertEqual(self.pc.resolve_control_url(cwd=str(root / "sub"), allow_env=False), url)
        self.assertEqual(self.pc.resolve_control_url(aegl_project="DemoProj", allow_env=False), url)


if __name__ == "__main__":
    unittest.main()

"""The read-only diagnostic mode cannot fall through to task execution."""
from pathlib import Path
import subprocess
import unittest


class DiagnosticEntryTests(unittest.TestCase):
    def run_parser(self,args):
        text=Path(__file__).resolve().parents[1].joinpath('run_registered_task').read_text()
        start=text.index('TASK_ID=""; PROMPT=""; EXPECTED=""')
        end=text.index('[ -n "$PROMPT" ] ||')
        fragment='set -euo pipefail\n'+text[start:end]+'\necho EXECUTION_FALLTHROUGH\n'
        return subprocess.run(['bash','-c',fragment,'diagnostic-test',*args],capture_output=True,text=True,timeout=5)

    def test_diagnostics_cannot_take_execution_options(self):
        for option,value in [('--prompt-file','/tmp/x'),('--expected-manifest-sha256','a'*64),
                             ('--max-runtime','120'),('--grace','10')]:
            with self.subTest(option=option):
                p=self.run_parser(['--task-id','CAL-DIAG','--diagnostic-summary',option,value])
                self.assertNotEqual(p.returncode,0)
                self.assertIn('diagnostic summary takes only task id',p.stderr)
                self.assertNotIn('EXECUTION_FALLTHROUGH',p.stdout)

    def test_diagnostics_rejects_path_task_before_any_helper(self):
        p=self.run_parser(['--task-id','../CAL-DIAG','--diagnostic-summary'])
        self.assertNotEqual(p.returncode,0)
        self.assertIn('invalid task id',p.stderr)
        self.assertNotIn('EXECUTION_FALLTHROUGH',p.stdout)

    def test_original_execution_options_keep_execution_mode(self):
        p=self.run_parser(['--task-id','CAL-DIAG','--prompt-file','/trusted/EXECUTOR-PROMPT.md',
            '--expected-manifest-sha256','a'*64,'--max-runtime','120','--grace','10'])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('EXECUTION_FALLTHROUGH',p.stdout)


if __name__=='__main__':
    unittest.main()

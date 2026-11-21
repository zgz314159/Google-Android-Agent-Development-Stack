"""NNP rejection must happen before any browser call or task consumption."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bridge_cli as cli
import contract_executor as ce


class LaunchPrivilegeTests(unittest.TestCase):
    def test_nonroot_nnp_is_denied(self):
        with patch.object(ce.os,'geteuid',return_value=1000),patch.object(Path,'read_text',return_value='NoNewPrivs:\t1\n'):
            with self.assertRaises(ce.ControlledLaunchError) as e:
                ce.require_launch_privilege()
            self.assertEqual(e.exception.code,'E_LAUNCH_NO_NEW_PRIVS')

    def test_no_nnp_passes_and_unknown_status_fails_closed(self):
        with patch.object(ce.os,'geteuid',return_value=1000):
            for status in ('NoNewPrivs:\t0\n','Name:\tpython\n'):
                with patch.object(Path,'read_text',return_value=status):
                    if status.startswith('NoNewPrivs:'):
                        ce.require_launch_privilege()
                    else:
                        with self.assertRaises(ce.ControlledLaunchError):
                            ce.require_launch_privilege()

    def test_round_cannot_read_send_or_consume_when_privilege_is_blocked(self):
        with tempfile.TemporaryDirectory(prefix='launch-guard-',dir='/var/tmp') as d:
            root=Path(d)/'bridge'
            calls=[]
            with patch.object(ce,'require_launch_privilege',side_effect=ce.ControlledLaunchError('E_LAUNCH_NO_NEW_PRIVS','blocked')):
                result=cli.run_round(root=root,read_fn=lambda:calls.append('read'),
                    send_fn=lambda *a:calls.append('send'))
            self.assertEqual(result['decision'],'LAUNCH_BLOCKED')
            self.assertFalse(calls)
            self.assertFalse((root/'state.json').exists())
            self.assertFalse((root/'journal.jsonl').exists())


if __name__=='__main__':
    unittest.main()

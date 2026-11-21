"""Submit once through the real send control; preserve exact user-turn authority."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import chatgpt_adapter as a


class Ops:
    def __init__(self,error=None,deliver=True):
        self.body='';self.turns=[];self.calls=0;self.error=error;self.deliver=deliver
    def find_control_tab(self): return {}
    def user_turns(self): return self.turns
    def composer_selector(self): return 'editor'
    def fill_input(self,selector,text): self.body=text
    def composer_text(self,selector): return self.body
    def press_key(self,key): raise AssertionError('must use button, not Enter')
    def submit_once(self,selector):
        self.calls+=1
        if self.error: raise self.error
        if self.deliver: self.turns.append(self.body);self.body=''


class SubmitButtonTests(unittest.TestCase):
    def test_exact_delivery_uses_only_one_submit(self):
        ops=Ops()
        r=a.send_once('RESULT id=unique\nsecond line','unique',ops=ops,exact=True,confirm_timeout_s=0)
        self.assertEqual(r['status'],a.CONFIRMED_SENT)
        self.assertEqual(ops.calls,1)

    def test_unavailable_button_or_transport_error_does_not_retry(self):
        for error,sent in [(a.SubmitNotReady('busy'),False),(RuntimeError('partial click'),True)]:
            ops=Ops(error=error)
            r=a.send_once('RESULT id=unique','unique',ops=ops,exact=True,confirm_timeout_s=0)
            self.assertEqual(r['status'],a.SEND_UNCERTAIN)
            self.assertEqual(r['sent'],sent)
            self.assertEqual(ops.calls,1)

    def test_composer_is_still_not_delivery_authority(self):
        ops=Ops(deliver=False)
        r=a.send_once('RESULT id=unique','unique',ops=ops,exact=True,confirm_timeout_s=0)
        self.assertEqual(r['status'],a.SEND_UNCERTAIN)
        self.assertEqual(ops.calls,1)

    def test_target_must_be_unique_ready_before_click(self):
        ops=a.RealOps.__new__(a.RealOps);clicks=[]
        ops.h={'click_at_xy':lambda *p:clicks.append(p)}
        ops.js=lambda expression:None
        with self.assertRaises(a.SubmitNotReady): ops.submit_once('editor')
        self.assertFalse(clicks)
        ops.js=lambda expression:{'x':10,'y':20}
        ops.submit_once('editor')
        self.assertEqual(clicks,[(10,20)])


if __name__=='__main__': unittest.main()

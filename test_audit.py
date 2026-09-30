"""Synthetic regression probes, not a benchmark of human writing quality."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from slopcheck import SPEC, lint

V = dict(inspected=True, real_asset=True, privacy_checked=True)
ROOT = Path(__file__).parent

class AuditTests(unittest.TestCase):
    def codes(self, text, **kwargs):
        return {i['code'] for i in lint(text, **kwargs)['issues']}
    def test_ordinary_technical_words_not_blocked(self):
        for s in ['The operator restarted the pump.', 'Transform the coordinates before drawing the map.', 'Use Tab to navigate between fields.']:
            self.assertEqual(lint(s)['issues'], [], s)
    def test_common_grammatical_words_not_claims(self):
        for s in ['I live near the station.', 'Read the first line only.']:
            self.assertNotIn('CLAIM_REVIEW', self.codes(s))
    def test_inflected_hype(self):
        self.assertIn('GENERIC_REGISTER', self.codes('Our platform empowers teams and unlocks their potential.'))
    def test_generic_promotional_phrases(self):
        for s in ['Discover a world of possibilities.', 'Take your business to the next level.', 'In an ever-evolving digital landscape, innovation is the key to success.']:
            self.assertIn('GENERIC_REGISTER', self.codes(s))
    def test_curly_apostrophe_regression(self):
        s="@OpenAI’s new safety-case pitch has one test:\nWho gets to stop the run?\nIf that answer’s buried, it’s paperwork."
        self.assertIn('QUESTION_IF_VERDICT', self.codes(s))
    def test_visual_false_string_rejected(self):
        with self.assertRaises(ValueError):
            lint('A clear button.', 'x', dict(inspected='false', real_asset='false', privacy_checked='false'))
    def test_invalid_input_shapes(self):
        for v in [[], True, {'inspected':True}]:
            with self.assertRaises(ValueError): lint('Text', 'x', v)
        for e in [{}, ['url'], [dict(claim=1, source='url', note='note', checked=True)]]:
            with self.assertRaises(ValueError): lint('Text', evidence=e)
    def test_visual_required_configuration(self):
        cfg=copy.deepcopy(SPEC); cfg['social']['visual_required']=False
        self.assertNotIn('VISUAL_UNVERIFIED', self.codes('A clear button.', channel='x', spec=cfg))
    def test_wrapped_paragraph(self):
        self.assertIn('WALL_OF_TEXT', self.codes(('word '*20).strip()+'\n'+('word '*20).strip(), channel='x', visual=V))
        self.assertNotIn('WALL_OF_TEXT', self.codes(('word '*20).strip()+'\n\n'+('word '*20).strip(), channel='x', visual=V))
    def test_fragment_span_with_blank_lines(self):
        s='Ship the thing.\n\nCheck the thing.\n\nFix the thing.'
        i=next(i for i in lint(s,'x',V)['issues'] if i['code']=='FRAGMENT_STACK')
        self.assertEqual(s[slice(*i['span'])], s)
    def test_claim_detection_is_review_not_verdict(self):
        self.assertEqual(lint('We saved 30%.')['status'], 'human_review')
        self.assertIn('CLAIM_REVIEW', self.codes('We saved 30%.'))
    def test_personal_hard_list_still_supported(self):
        cfg=copy.deepcopy(SPEC); cfg['lexicon']['hard']=['operator']
        self.assertEqual(lint('The operator.',spec=cfg)['status'], 'blocked')
    def run_cli(self, *args, text='A clear button.'):
        return subprocess.run([sys.executable,str(ROOT/'slopcheck.py'),*args],input=text,text=True,capture_output=True)
    def test_default_exit_keeps_compatibility(self):
        r=self.run_cli(text='');self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['status'],'blocked')
    def test_gate_exit_codes(self):
        self.assertEqual(self.run_cli('--fail-on','block',text='').returncode,1)
        self.assertEqual(self.run_cli('--fail-on','block',text='Leverage the pump.').returncode,0)
        self.assertEqual(self.run_cli('--fail-on','review',text='Leverage the pump.').returncode,1)
        self.assertEqual(self.run_cli('--fail-on','review').returncode,0)
    def test_cli_invalid_json_no_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{')
            r=self.run_cli('--visual',str(p));self.assertEqual(r.returncode,2);self.assertIn('Input/config error',r.stderr);self.assertNotIn('Traceback',r.stderr)
    def test_cli_invalid_shape_no_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('[]')
            r=self.run_cli('--visual',str(p));self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
    def test_invalid_config_rejected(self):
        for key,value in [('visual_required','false'),('max_sentence_words',True)]:
            cfg=copy.deepcopy(SPEC);cfg['social'][key]=value
            with self.assertRaises(ValueError): lint('Text',spec=cfg)
        with self.assertRaises(ValueError): lint('Text',spec=[])
    def test_known_semantic_misses_remain_visible(self):
        # Document the boundary instead of claiming regexes verify facts.
        for s in ['Acme cut checkout time in half after the migration.', 'The update ships tomorrow and supports every Android phone.']:
            self.assertEqual(lint(s)['claims_detected'], [])

if __name__=='__main__': unittest.main()

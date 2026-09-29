import unittest
from slopcheck import lint

V = dict(inspected=True, real_asset=True, privacy_checked=True)

class TestPreflight(unittest.TestCase):
    def codes(self, text, channel='copy', visual=None, evidence=None):
        return {x['code'] for x in lint(text, channel, visual, evidence)['issues']}
    def test_banned_word_boundary_and_case(self):
        self.assertIn('BANNED_REGISTER', self.codes('Leverage the operator.'))
        self.assertNotIn('BANNED_REGISTER', self.codes('A lever on the door.'))
    def test_real_post_needs_inspected_image(self):
        self.assertIn('VISUAL_UNVERIFIED', self.codes('Pretty photos do not get you booked.', 'x'))
        self.assertNotIn('VISUAL_UNVERIFIED', self.codes('Pretty photos do not get you booked.', 'x', V))
    def test_missing_claim_evidence(self):
        self.assertIn('CLAIM_REVIEW', self.codes('We saved 30% this month.', evidence=[dict(claim='30%',source='https://example.org')]))
    def test_checked_claim_specific_evidence(self):
        e = [dict(claim='30%',source='https://example.org/receipt',note='Receipt states 30%',checked=True), dict(claim='saved',source='https://example.org/receipt',note='Receipt substantiates saving',checked=True)]
        self.assertNotIn('CLAIM_REVIEW', self.codes('We saved 30% this month.', evidence=e))
    def test_linkedin_lane(self):
        self.assertNotIn('LINKEDIN_LANE', self.codes('This is live.', 'linkedin', V))
    def test_long_line(self):
        self.assertIn('WALL_OF_TEXT', self.codes(' '.join(['word']*33), 'x', V))
    def test_never_auto_approves(self):
        self.assertEqual(lint('A clear Book button does.', 'x', V)['status'], 'human_review')

if __name__ == '__main__':
    unittest.main()

class TestGrammarLayer(unittest.TestCase):
    V = dict(inspected=True, real_asset=True, privacy_checked=True)
    def codes(self, text, channel='x'):
        return {i['code'] for i in lint(text, channel, self.V)['issues']}
    def test_user_rejected_openai_draft_must_fail(self):
        draft = "@OpenAI's new safety-case pitch has one test:\nWho gets to stop the run?\nIf that answer's buried, it's paperwork."
        result = lint(draft, 'x', self.V)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('RHETORICAL_SETUP', self.codes(draft))
        self.assertIn('QUESTION_IF_VERDICT', self.codes(draft))
    def test_false_contrast(self):
        self.assertIn('FALSE_CONTRAST', self.codes('Not more dashboards, but better decisions.'))
        self.assertIn('FALSE_CONTRAST', self.codes('Not just a tool, but also a teammate.'))
    def test_em_dash_pivot_and_opener(self):
        self.assertIn('EM_DASH_PIVOT', self.codes('The agent ran—then it stopped.'))
        self.assertIn('AI_OPENER', self.codes("Here's the thing: nobody checked."))
    def test_rule_of_three(self):
        text='We tested one.\nWe tested two.\nWe tested three.'
        self.assertIn('RULE_OF_THREE', self.codes(text))
    def test_short_fragment_stack(self):
        self.assertIn('FRAGMENT_STACK', self.codes('Ship the thing.\nCheck the thing.\nFix the thing.'))
    def test_clean_voice_no_grammar_false_positive(self):
        text="Pretty photos don't get you booked. A clear Book button does."
        self.assertFalse(self.codes(text) & {'RHETORICAL_SETUP','QUESTION_IF_VERDICT','IF_THEN_APHORISM','FALSE_CONTRAST','EM_DASH_PIVOT','AI_OPENER','RULE_OF_THREE','FRAGMENT_STACK'})
    def test_real_critique_long_paragraph_still_detected(self):
        text="Microsoft says Copilot Autopilot will keep working while you're gone. Fine. The test is what it can show you when you get back: what it did, who it contacted, and what it couldn't finish. Private preview expands at month-end."
        self.assertIn('WALL_OF_TEXT', self.codes(text))

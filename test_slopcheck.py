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

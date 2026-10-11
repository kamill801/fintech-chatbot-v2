import unittest
from unittest.mock import patch

from ledger.plan_preview import InvalidPlanPreview, PlanPreviewTokens
from tests.helpers import FERNET_KEY


class PlanPreviewTokenTests(unittest.TestCase):
    def test_review_expires_and_is_bound_to_operation_and_owner(self):
        tokens = PlanPreviewTokens(FERNET_KEY, ttl_seconds=900)
        with patch('time.time', return_value=1_800_000_000):
            receipt = tokens.issue({'user_ref': 'usr_a', 'operation': 'revise', 'plan': {'name': '가상 계획'}})
        with patch('time.time', return_value=1_800_000_100):
            self.assertEqual(tokens.read(receipt, user_ref='usr_a', operation='revise')['plan']['name'], '가상 계획')
            for owner, operation in [('usr_b', 'revise'), ('usr_a', 'activate')]:
                with self.assertRaises(InvalidPlanPreview):
                    tokens.read(receipt, user_ref=owner, operation=operation)
        with patch('time.time', return_value=1_800_000_901):
            with self.assertRaises(InvalidPlanPreview):
                tokens.read(receipt, user_ref='usr_a', operation='revise')

    def test_review_survives_runtime_restart_with_the_same_configured_key(self):
        one, two = PlanPreviewTokens(FERNET_KEY), PlanPreviewTokens(FERNET_KEY)
        receipt = one.issue({'user_ref': 'usr_a', 'operation': 'activate'})
        self.assertEqual(two.read(receipt, user_ref='usr_a', operation='activate')['operation'], 'activate')


if __name__ == '__main__':
    unittest.main()

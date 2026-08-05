from __future__ import annotations

import json
import unittest
import warnings

from ledger.application.signals import SignalInputs, compute_signal_set
from ledger.domain.models import DomainValidationError, FinancialGoal, FinancialProfile
from ledger.privacy import (
    OPENAI_PROMPT_ALLOWLIST,
    PrivacyConfig,
    PrivacyError,
    amount_bucket,
    build_prompt_payload,
    sanitize_free_text,
    sanitize_share_payload,
    sanitize_telemetry_payload,
)
from tests.helpers import FERNET_KEY, USER_REF_SECRET, fixed_privacy, profile_payload, utc


class DomainValidationTests(unittest.TestCase):
    def test_rejects_negative_money_fields(self) -> None:
        payload = profile_payload()
        payload["monthly_income_krw"] = -1
        with self.assertRaises(DomainValidationError):
            FinancialProfile.from_dict({**payload, "user_ref": "usr_test", "created_at": utc(), "updated_at": utc()})

    def test_rejects_non_positive_discretionary_budget(self) -> None:
        payload = profile_payload()
        payload["discretionary_budget_krw"] = 0
        with self.assertRaises(DomainValidationError):
            FinancialProfile.from_dict({**payload, "user_ref": "usr_test", "created_at": utc(), "updated_at": utc()})

    def test_rejects_goal_target_below_current_amount(self) -> None:
        with self.assertRaises(DomainValidationError):
            FinancialGoal(
                goal_id="goal",
                name="비상금",
                target_amount_krw=1000,
                current_amount_krw=2000,
                target_date="2027-12-31",
            )


class SignalPolicyTests(unittest.TestCase):
    def test_computes_documented_risk_formula(self) -> None:
        signals = compute_signal_set(
            SignalInputs(
                transaction_amount_krw=120000,
                discretionary_budget_krw=800000,
                spent_before_transaction_krw=456000,
                category="shopping",
                goal_pressure=0.55,
                baseline_deviation=1.4,
                recurrence_30d=3,
                has_reason=False,
                profile_complete=True,
                history_complete=True,
            )
        )
        self.assertEqual(signals.risk_score, 0.5035)

    def test_requires_reason_at_lower_threshold(self) -> None:
        signals = compute_signal_set(
            SignalInputs(
                transaction_amount_krw=200000,
                discretionary_budget_krw=1000000,
                spent_before_transaction_krw=550000,
                category="shopping",
                goal_pressure=0.5,
                baseline_deviation=1.0,
                recurrence_30d=0,
                has_reason=True,
                history_complete=True,
            )
        )
        self.assertTrue(signals.requires_reason)

    def test_requires_reason_for_unknown_category(self) -> None:
        signals = compute_signal_set(
            SignalInputs(
                transaction_amount_krw=1000,
                discretionary_budget_krw=1000000,
                category="unknown",
                has_reason=True,
                history_complete=True,
            )
        )
        self.assertTrue(signals.requires_reason)

    def test_requires_reason_for_high_budget_share_without_reason(self) -> None:
        signals = compute_signal_set(
            SignalInputs(
                transaction_amount_krw=200000,
                discretionary_budget_krw=1000000,
                category="medical",
                has_reason=False,
                history_complete=True,
            )
        )
        self.assertTrue(signals.requires_reason)

    def test_requires_reason_for_low_data_confidence(self) -> None:
        signals = compute_signal_set(
            SignalInputs(
                transaction_amount_krw=1000,
                discretionary_budget_krw=1000000,
                category="medical",
                has_reason=True,
                history_complete=False,
            )
        )
        self.assertTrue(signals.requires_reason)


class PrivacyTests(unittest.TestCase):
    def test_hmac_user_ref_is_stable_and_pseudonymous(self) -> None:
        privacy = fixed_privacy()
        self.assertEqual(privacy.user_ref("kakao-user"), privacy.user_ref("kakao-user"))
        self.assertNotIn("kakao-user", privacy.user_ref("kakao-user"))

    def test_fernet_round_trips_json_without_plaintext_ciphertext(self) -> None:
        privacy = fixed_privacy()
        ciphertext = privacy.encrypt_json({"merchant": "민감상점", "amount_krw": 12345})
        self.assertNotIn("민감상점", ciphertext)
        self.assertEqual(privacy.decrypt_json(ciphertext)["amount_krw"], 12345)

    def test_production_requires_encryption_key(self) -> None:
        with self.assertRaises(PrivacyError):
            PrivacyConfig.from_env({"APP_ENV": "production", "LEDGER_USER_REF_SECRET": "secret"})

    def test_development_generates_ephemeral_secrets_with_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            config = PrivacyConfig.from_env({"APP_ENV": "development"})
        self.assertIsInstance(config.encryption_key, bytes)
        self.assertGreaterEqual(len(caught), 2)

    def test_sanitizer_redacts_contact_and_long_numbers(self) -> None:
        sanitized = sanitize_free_text("전화 010-1234-5678 mail a@b.com 카드 1234-5678-9012")
        self.assertIn("[redacted-phone]", sanitized)
        self.assertIn("[redacted-email]", sanitized)
        self.assertIn("[redacted-number]", sanitized)

    def test_prompt_payload_allows_only_privacy_safe_fields_with_sanitized_reason(self) -> None:
        signals = compute_signal_set(
            SignalInputs(
                transaction_amount_krw=50000,
                discretionary_budget_krw=500000,
                category="shopping",
                history_complete=True,
            )
        )
        payload = build_prompt_payload(
            amount_krw=50000,
            category="shopping",
            signals=signals.to_dict(),
            user_reason="연락처 010-1234-5678 때문에 샀음",
            policy_version="overspending-v1",
        )
        self.assertLessEqual(set(payload), OPENAI_PROMPT_ALLOWLIST)
        self.assertIn("[redacted-phone]", json.dumps(payload, ensure_ascii=False))

    def test_telemetry_payload_rejects_raw_amount(self) -> None:
        with self.assertRaises(PrivacyError):
            sanitize_telemetry_payload({"event_type": "judgment.completed", "amount_krw": 50000})

    def test_share_payload_rejects_raw_reason(self) -> None:
        with self.assertRaises(PrivacyError):
            sanitize_share_payload({"label": "caution", "reason": "민감 사유"})

    def test_amount_bucket_uses_coarse_ranges(self) -> None:
        self.assertEqual(amount_bucket(9999), "under_10000")
        self.assertEqual(amount_bucket(300000), "300000_plus")


if __name__ == "__main__":
    unittest.main()

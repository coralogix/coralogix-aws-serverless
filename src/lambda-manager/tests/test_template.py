import re
import unittest
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "template.yaml"


class LambdaManagerTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE_PATH.read_text()

    def test_eventbridge_pattern_matches_standard_or_missing_log_group_class(self):
        match = re.search(r"logGroupClass:\n((?:\s+-.*\n)+)", self.template)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(
            ['- "STANDARD"', "- exists: false"],
            [line.strip() for line in match.group(1).splitlines()],
        )

    def test_lambda_execution_policy_can_reconcile_owned_subscriptions(self):
        lambda_function = self.template.split("  LambdaFunction:\n", 1)[1].split(
            "  LambdaTrigger:\n", 1
        )[0]
        policies = lambda_function.split("      Policies:\n", 1)[1].split(
            "      EventInvokeConfig:\n", 1
        )[0]

        for action in (
            "logs:DescribeLogGroups",
            "logs:DescribeSubscriptionFilters",
            "logs:PutSubscriptionFilter",
            "logs:DeleteSubscriptionFilter",
            "logs:TagResource",
            "logs:UntagResource",
            "tag:GetResources",
        ):
            with self.subTest(action=action):
                self.assertIn(f"- {action}", policies)

        self.assertIn("- IsDestinationLambda", policies)
        self.assertIn("- IsDestinationFirehose", policies)
        self.assertNotIn("lambda:UpdateFunctionConfiguration", policies)


if __name__ == "__main__":
    unittest.main()

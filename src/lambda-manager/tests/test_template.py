import re
import unittest
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "template.yaml"


class LambdaManagerTemplateTests(unittest.TestCase):
    def test_eventbridge_pattern_matches_standard_or_missing_log_group_class(self):
        template = TEMPLATE_PATH.read_text()
        match = re.search(r"logGroupClass:\n((?:\s+-.*\n)+)", template)

        self.assertIsNotNone(match)

        log_group_class_pattern = [line.strip() for line in match.group(1).splitlines()]

        self.assertEqual(
            [
                '- "STANDARD"',
                "- exists: false",
            ],
            log_group_class_pattern,
        )


if __name__ == "__main__":
    unittest.main()

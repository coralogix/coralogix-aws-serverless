import unittest
from pathlib import Path

import yaml


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "template.yaml"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def construct_cloudformation_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


CloudFormationLoader.add_multi_constructor("!", construct_cloudformation_tag)


class LambdaManagerTemplateTests(unittest.TestCase):
    def test_eventbridge_pattern_matches_standard_or_missing_log_group_class(self):
        template = yaml.load(TEMPLATE_PATH.read_text(), Loader=CloudFormationLoader)
        event_pattern = (
            template["Resources"]["LambdaFunction"]["Properties"]["Events"]["EventBridgeRule"]["Properties"]["Pattern"]
        )
        log_group_class_pattern = event_pattern["detail"]["requestParameters"]["logGroupClass"]

        self.assertIn("STANDARD", log_group_class_pattern)
        self.assertIn({"exists": False}, log_group_class_pattern)
        self.assertEqual(2, len(log_group_class_pattern))


if __name__ == "__main__":
    unittest.main()

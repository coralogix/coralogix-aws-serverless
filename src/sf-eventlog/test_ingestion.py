import os
import unittest
from unittest.mock import patch

# Keep the package's supported import order used by app.py; importing
# coralogix.http first exposes coralogix_logger 2.1.1's circular imports.
from coralogix.handlers import CoralogixLogger  # noqa: F401
from coralogix.constants import Coralogix
from coralogix.http import CoralogixHTTPSender


class CoralogixIngestionContractTests(unittest.TestCase):
    def test_singles_endpoint_uses_bearer_auth_and_singles_payload(self):
        endpoint = "https://ingress.eu1.coralogix.com/logs/v1/singles"
        bulk = {
            "privateKey": "test-private-key",
            "applicationName": "salesforce",
            "subsystemName": "eventlog",
            "logEntries": [
                {
                    "text": '{"EventType": "Login"}',
                    "timestamp": 1_700_000_000_000,
                    "severity": 3,
                    "category": "External Logger",
                }
            ],
        }

        with (
            patch.dict(os.environ, {"CORALOGIX_LOG_URL": endpoint}, clear=False),
            patch("coralogix.http.requests.post") as post,
        ):
            post.return_value.status_code = 200
            CoralogixHTTPSender.send_request(
                bulk,
                url=Coralogix.get_log_url(),
            )

        post.assert_called_once()
        request = post.call_args.kwargs
        self.assertEqual(request["url"], endpoint)
        self.assertEqual(
            request["headers"]["Authorization"],
            "Bearer test-private-key",
        )
        self.assertEqual(request["headers"]["Content-Type"], "application/json")
        self.assertEqual(
            request["json"],
            [
                {
                    "applicationName": "salesforce",
                    "subsystemName": "eventlog",
                    "text": '{"EventType": "Login"}',
                    "timestamp": 1_700_000_000_000,
                    "severity": 3,
                    "category": "External Logger",
                }
            ],
        )
        self.assertNotIn("privateKey", request["json"][0])
        self.assertNotIn("logEntries", request["json"][0])


if __name__ == "__main__":
    unittest.main()

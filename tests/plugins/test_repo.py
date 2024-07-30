import json
import unittest
from unittest import mock

from app import repo  # Updated import to use 'app'

# Define the mock repo_data
mock_repo_data = {
    "django": ["https://github.com/OWASP-BLT/BLT"],
    "python": [
        "https://github.com/OWASP-BLT/BLT",
        "https://github.com/OWASP-BLT/BLT-Flutter",
        "https://github.com/OWASP-BLT/BLT-Lettuce",
    ],
    "dart": [
        "https://github.com/OWASP-BLT/BLT-Flutter",
        "https://github.com/OWASP-BLT/BLT-Lettuce",
    ],
    "flutter": [
        "https://github.com/OWASP-BLT/BLT-Flutter",
        "https://github.com/OWASP-BLT/BLT-Lettuce",
    ],
    "blockchain": ["https://github.com/OWASP-BLT/BLT-Bacon"],
    "cryptography": ["https://github.com/OWASP-BLT/BLT-Bacon"],
    "javascript": [
        "https://github.com/OWASP-BLT/BLT-Action",
        "https://github.com/OWASP-BLT/BLT-Extension",
        "https://github.com/OWASP-BLT/BLT",
    ],
    "css": ["https://github.com/OWASP-BLT/BLT-Extension", "https://github.com/OWASP-BLT/BLT"],
    "html": ["https://github.com/OWASP-BLT/BLT-Extension", "https://github.com/OWASP-BLT/BLT"],
}


class TestRepoCommand(unittest.TestCase):
    @mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(mock_repo_data)))
    def test_repo_command_known_technology(self):
        mock_ack = mock.Mock()
        mock_say = mock.Mock()
        command = {"text": "python", "channel_id": "channel_id"}

        repo(mock_ack, command, mock_say)

        mock_ack.assert_called_once()
        mock_say.assert_called_once_with(
            text="Hello, you can implement your 'python' knowledge here:\n"
                "https://github.com/OWASP-BLT/BLT\n"
                "https://github.com/OWASP-BLT/BLT-Flutter\n"
                "https://github.com/OWASP-BLT/BLT-Lettuce"
        )

    @mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(mock_repo_data)))
    def test_repo_command_unknown_technology(self):
        mock_ack = mock.Mock()
        mock_say = mock.Mock()
        command = {"text": "unknown", "channel_id": "channel_id"}

        repo(mock_ack, command, mock_say)

        mock_ack.assert_called_once()
        mock_say.assert_called_once_with(
            channel="channel_id",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Here are the available technologies to choose from:",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "tech_select_block",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "django"},
                            "value": "django",
                            "action_id": "plugin_repo_button_django",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "python"},
                            "value": "python",
                            "action_id": "plugin_repo_button_python",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "dart"},
                            "value": "dart",
                            "action_id": "plugin_repo_button_dart",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "flutter"},
                            "value": "flutter",
                            "action_id": "plugin_repo_button_flutter",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "blockchain"},
                            "value": "blockchain",
                            "action_id": "plugin_repo_button_blockchain",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "cryptography"},
                            "value": "cryptography",
                            "action_id": "plugin_repo_button_cryptography",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "javascript"},
                            "value": "javascript",
                            "action_id": "plugin_repo_button_javascript",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "css"},
                            "value": "css",
                            "action_id": "plugin_repo_button_css",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "html"},
                            "value": "html",
                            "action_id": "plugin_repo_button_html",
                        },
                    ],
                },
            ],
            text="Available technologies:",
        )

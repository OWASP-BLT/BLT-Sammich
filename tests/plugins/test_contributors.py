import unittest
from unittest.mock import MagicMock, patch

import requests

from contributors import fetch_github_data


class TestFetchGithubData(unittest.TestCase):
    @patch("requests.get")
    def test_successful_fetch(self, mock_get):
        # Mock successful responses
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: [{"user": {"login": "user1"}}]),
            MagicMock(status_code=200, json=lambda: [{"user": {"login": "user2"}}]),
            MagicMock(status_code=200, json=lambda: [{"user": {"login": "user3"}}]),
        ]

        prs, issues, comments = fetch_github_data("owner", "repo", "2023-07-01")

        self.assertEqual(len(prs), 1)
        self.assertEqual(len(issues), 1)
        self.assertEqual(len(comments), 1)
        self.assertEqual(prs[0]["user"]["login"], "user1")
        self.assertEqual(issues[0]["user"]["login"], "user2")
        self.assertEqual(comments[0]["user"]["login"], "user3")

    @patch("requests.get")
    def test_http_error(self, mock_get):
        # Mock HTTP error
        mock_get.side_effect = requests.exceptions.HTTPError("HTTP error")

        prs, issues, comments = fetch_github_data("owner", "repo", "2023-07-01")

        self.assertEqual(prs, [])
        self.assertEqual(issues, [])
        self.assertEqual(comments, [])

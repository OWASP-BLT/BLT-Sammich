from unittest import mock

import pytest

from app import project
from project import show_project_page

GITHUB_REPOSITORY_OWNER = "OWASP-BLT"
GITHUB_REPOSITORY_NAME = "BLT-Sammich"
PROJECTS_PER_PAGE = 100
PROJECTS_DATA = {
    "project1": ["Detail 1", "Detail 2"],
    "project2": ["Detail 3"],
    "project3": ["Detail 4", "Detail 5", "Detail 6"],
}

REPOS_DATA = {}


@pytest.fixture
def mock_project_data():
    with mock.patch("project.project_data", PROJECTS_DATA):  # Corrected module name
        yield


def test_show_project_page_no_projects(mock_project_data):
    with mock.patch("project.project_data", {}):  # Corrected module name
        mock_say = mock.Mock()
        show_project_page("channel_id", mock_say)
        mock_say.assert_called_once_with(channel="channel_id", text="No projects available.")


def test_show_project_page_with_projects(mock_project_data):
    mock_say = mock.Mock()
    show_project_page("channel_id", mock_say)

    num_dropdowns = (len(PROJECTS_DATA.keys()) + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE
    for i in range(num_dropdowns):
        start_index = i * PROJECTS_PER_PAGE
        end_index = start_index + PROJECTS_PER_PAGE
        project_slice = list(PROJECTS_DATA.keys())[start_index:end_index]

        expected_options = [
            {"text": {"type": "plain_text", "text": project[:75]}, "value": project}
            for project in project_slice
        ]

        expected_block = {
            "type": "section",
            "block_id": f"project_select_block_{i}",
            "text": {
                "type": "mrkdwn",
                "text": f"Select a project (Page {i + 1}):",
            },
            "accessory": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": f"Select a project (Page {i + 1})",
                },
                "options": expected_options,
                "action_id": f"project_select_action_{i}",
            },
        }

        mock_say.assert_any_call(
            channel="channel_id", blocks=[expected_block], text="Available Projects"
        )


def test_project_command_found(mock_project_data):
    mock_ack = mock.Mock()
    mock_say = mock.Mock()
    command = {"text": "project1", "channel_id": "channel_id"}

    project(mock_ack, command, mock_say)

    mock_ack.assert_called_once()
    expected_message = {
        "channel": "channel_id",
        "blocks": [
            {
                "type": "section",
                "block_id": "project_select_block_0",
                "text": {"type": "mrkdwn", "text": "Select a project (Page 1):"},
                "accessory": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select a project (Page 1)"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "project1"}, "value": "project1"},
                        {"text": {"type": "plain_text", "text": "project2"}, "value": "project2"},
                        {"text": {"type": "plain_text", "text": "project3"}, "value": "project3"},
                    ],
                    "action_id": "project_select_action_0",
                },
            }
        ],
        "text": "Available Projects",
    }
    mock_say.assert_called_once_with(**expected_message)

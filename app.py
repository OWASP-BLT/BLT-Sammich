import json
import logging
import re
from datetime import datetime, timedelta

import dateparser
from dotenv import dotenv_values
from github import Github
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.app import App
from slack_sdk.errors import SlackApiError

from contributors import fetch_github_data, format_data
from project import show_project_page

# Configuration
GITHUB_REPOSITORY_OWNER = "OWASP-BLT"
GITHUB_REPOSITORY_NAME = "BLT-Sammich"
PROJECTS_PER_PAGE = 100

# Load environment variables
secrets = dotenv_values(".secrets")
SLACK_APP_TOKEN = secrets["SLACK_APP_TOKEN"]
SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
GITHUB_TOKEN = secrets["GITHUB_TOKEN"]

# Initialize Slack App
app = App(token=SLACK_BOT_TOKEN)

# Commands
@app.command("/contributors")
def contributors(ack, say, command):
    ack()
    since_date = (datetime.now() - timedelta(days=7)).date()
    prs, issues, comments = fetch_github_data(GITHUB_REPOSITORY_OWNER, GITHUB_REPOSITORY_NAME, since_date)
    formatted_data = format_data(prs, issues, comments)
    if not formatted_data:
        formatted_data = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "No data available"}}
        ]
    say(text="Contributors Activity", blocks=formatted_data)

@app.command("/ghissue")
def create_issue(ack, command, say):
    ack()
    title = command["text"].strip()
    github = Github(GITHUB_TOKEN)
    try:
        repo = github.get_repo(f"{GITHUB_REPOSITORY_OWNER}/{GITHUB_REPOSITORY_NAME}")
        issue = repo.create_issue(title=title)
        say(text=f"Issue created successfully: {issue.html_url}")
    except Exception as e:
        logging.error(f"Failed to create issue: {str(e)}")
        say(text="Failed to create issue")

with open("data/projects.json") as f:
    project_data = json.load(f)

with open("data/repos.json") as f:
    repo_data = json.load(f)

@app.command("/project")
def project(ack, command, say):
    ack()
    project_name = command["text"].strip().lower()
    channel_id = command["channel_id"]
    project = project_data.get(project_name)
    if project:
        project_list = "\n".join(project)
        message = f"Hello, here is the information about '{project_name}':\n{project_list}"
        say(text=message)
    else:
        show_project_page(channel_id, say)

@app.action(re.compile(r"project_select_action_.*"))
def handle_dropdown_selection(ack, body, say):
    ack()
    selected_project = body["actions"][0]["selected_option"]["value"]
    project = project_data.get(selected_project)
    if project:
        project_list = "\n".join(project)
        message = f"Hello, here is the information about '{selected_project}':\n{project_list}"
        say(text=message)

@app.command("/repo")
def repo(ack, command, say):
    ack()
    tech_name = command["text"].strip().lower()
    channel_id = command["channel_id"]
    repos = repo_data.get(tech_name)
    if repos:
        repos_list = "\n".join(repos)
        message = f"Hello, you can implement your '{tech_name}' knowledge here:\n{repos_list}"
        say(text=message)
    else:
        fallback_message = "Available technologies:"
        message_preview = {
            "blocks": [
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
                            "text": {"type": "plain_text", "text": tech},
                            "value": tech,
                            "action_id": f"plugin_repo_button_{tech}",
                        }
                        for tech in repo_data.keys()
                    ],
                },
            ]
        }
        say(
            channel=channel_id,
            blocks=message_preview["blocks"],
            text=fallback_message,
        )

@app.action(re.compile(r"plugin_repo_button_.*"))
def handle_button_click(ack, body, say):
    ack()
    clicked_button_value = body["actions"][0]["value"]
    repos = repo_data.get(clicked_button_value)
    if repos:
        repos_list = "\n".join(repos)
        message = f"Hello, you can implement your '{clicked_button_value}' knowledge here:\n{repos_list}"
        say(text=message)

reminder_pattern = re.compile(r"\[(.*?)\]\s+\[(.+?)\]\s+\[(.+?)\]")

@app.command("/setreminder")
def handle_reminder(ack, body, say):
    ack()
    try:
        self_channel = body["channel_id"]
        text = body["text"].strip()
        logging.info(f"Received command text: {text}")

        channel_name, message, when, every = parse_command(text)
        channel_id = get_channel_id(channel_name)
        if not channel_id or not message or not when:
            say(
                text="Invalid command format. Please use [channel_id] [what] [when]."
            )
            logging.error("Invalid command format")
            return

        post_at = convert_to_datetime(when)
        if not post_at:
            say(
                text=f"Invalid time format for 'when': {when}."
            )
            logging.error(f"Invalid time format for 'when': {when}")
            return

        response = schedule_message(channel_id, message, post_at)
        if response.get("ok"):
            say(
                text=(
                    f"Message scheduled successfully for"
                    f" {post_at.strftime('%Y-%m-%d %H:%M:%S UTC')} in channel {channel_id}."
                )
            )
            logging.info(
                f"Message scheduled successfully for"
                f" {post_at.strftime('%Y-%m-%d %H:%M:%S UTC')} in channel {channel_id}."
            )
        else:
            say(
                text=f"Failed to schedule message: {response.get('error')}"
            )
            logging.error(f"Failed to schedule message: {response.get('error')}")
    except Exception as e:
        logging.error(f"Exception in command handling: {str(e)}")
        say(
            text="An error occurred while processing the command."
        )

def parse_command(command_text):
    match = reminder_pattern.match(command_text)
    if match:
        channel_name, message, when = match.groups()
        every = "every" in when
        when = when.lstrip("every ") if every else when
        return channel_name, message, when, every
    return None, None, None, False

def get_channel_id(channel_name):
    try:
        response = app.client.conversations_list()
        channels = response.get("channels", [])
        for channel in channels:
            if channel["name"] == channel_name.lstrip("#"):
                return channel["id"]
    except SlackApiError as e:
        logging.error(f"Error fetching channels: {e.response['error']}")
    return None

def convert_to_datetime(when):
    try:
        date = dateparser.parse(when)
        return date
    except ValueError:
        return None

def schedule_message(channel_id, text, post_at):
    try:
        response = app.client.chat_scheduleMessage(
            channel=channel_id,
            text=text,
            post_at=int(post_at.timestamp())
        )
        return response
    except SlackApiError as e:
        logging.error(f"Error scheduling message: {e.response['error']}")
        return {"ok": False, "error": e.response.get("error")}

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()

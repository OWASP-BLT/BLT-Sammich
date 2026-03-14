"""BLT-Sammich Python Cloudflare Worker

Handles Slack slash commands and interactive components via HTTP webhooks
using the Cloudflare Workers Python runtime (Pyodide).

Slack sends HTTP POST requests to this worker instead of the previous
Socket Mode approach, so no persistent connection is needed.

Environment variables (set via `wrangler secret put`):
    SLACK_SIGNING_SECRET: Slack signing secret for request verification
    SLACK_BOT_TOKEN:      Slack bot OAuth token (xoxb-...)
    GITHUB_TOKEN:         GitHub personal access token

Worker vars (set in wrangler.toml [vars]):
    GITHUB_REPO_OWNER:    GitHub repository owner (default: OWASP-BLT)
    GITHUB_REPO_NAME:     GitHub repository name  (default: BLT-Sammich)

KV Namespace bindings (configured in wrangler.toml [[kv_namespaces]]):
    BLT_DATA: Cloudflare KV namespace pre-populated with
              "projects" -> contents of data/projects.json
              "repos"    -> contents of data/repos.json

Static assets (configured in wrangler.toml [assets]):
    public/index.html is served automatically for GET /

Routes handled by this worker (all accept POST with a verified Slack signature):
    POST /slack/command    -- Slack slash commands
    POST /slack/action     -- Slack interactive component payloads
"""

import hashlib
import hmac
import json
import math
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from js import Headers, Object
from js import Response as JsResponse
from js import fetch as js_fetch
from pyodide.ffi import to_js

PROJECTS_PER_PAGE = 100
GITHUB_API_URL = "https://api.github.com"
PROJECTS_FALLBACK_URL = (
    "https://raw.githubusercontent.com/OWASP-BLT/BLT-Sammich/main/data/projects.json"
)
REPOS_FALLBACK_URL = (
    "https://raw.githubusercontent.com/OWASP-BLT/BLT-Sammich/main/data/repos.json"
)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _json_response(data: dict, status: int = 200) -> JsResponse:
    headers = Headers.new({"Content-Type": "application/json"}.items())
    return JsResponse.new(json.dumps(data), status=status, headers=headers)


def _text_response(text: str, status: int = 200) -> JsResponse:
    headers = Headers.new({"Content-Type": "text/plain"}.items())
    return JsResponse.new(text, status=status, headers=headers)


async def _fetch(url: str, method: str = "GET", headers: dict = None, body: str = None):
    """Thin wrapper around the JS fetch API."""
    init = {"method": method}
    if headers:
        init["headers"] = headers
    if body is not None:
        init["body"] = body
    js_init = to_js(init, dict_converter=Object.fromEntries)
    return await js_fetch(url, js_init)


# ---------------------------------------------------------------------------
# Slack request verification
# ---------------------------------------------------------------------------


def _verify_slack_signature(request_headers, raw_body: str, signing_secret: str) -> bool:
    """Return True when the Slack-Signature header matches the computed HMAC."""
    timestamp = request_headers.get("x-slack-request-timestamp")
    slack_sig = request_headers.get("x-slack-signature")

    if not timestamp or not slack_sig:
        return False

    # Reject replayed requests older than 5 minutes
    try:
        if abs(datetime.now(timezone.utc).timestamp() - float(timestamp)) > 300:
            return False
    except ValueError:
        return False

    sig_basestring = f"v0:{timestamp}:{raw_body}"
    computed = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, slack_sig)


# ---------------------------------------------------------------------------
# Data loading (KV with GitHub raw fallback)
# ---------------------------------------------------------------------------


async def _load_kv_or_url(env, kv_key: str, fallback_url: str) -> dict:
    """Try KV first, fall back to fetching from GitHub raw URL."""
    try:
        raw = await env.BLT_DATA.get(kv_key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass

    try:
        resp = await _fetch(fallback_url)
        text = await resp.text()
        return json.loads(text)
    except Exception:
        return {}


async def _get_projects(env) -> dict:
    return await _load_kv_or_url(env, "projects", PROJECTS_FALLBACK_URL)


async def _get_repos(env) -> dict:
    return await _load_kv_or_url(env, "repos", REPOS_FALLBACK_URL)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def _handle_contributors(env) -> dict:
    """Handle the /contributors slash command."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    auth = f"token {env.GITHUB_TOKEN}"
    hdrs = {"Authorization": auth, "User-Agent": "BLT-Sammich-Worker"}

    try:
        owner, repo = "OWASP-BLT", "Lettuce"
        prs_resp = await _fetch(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=closed&since={since}",
            headers=hdrs,
        )
        issues_resp = await _fetch(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed&since={since}",
            headers=hdrs,
        )
        comments_resp = await _fetch(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/comments?since={since}",
            headers=hdrs,
        )
        prs = list(await prs_resp.json())
        issues = list(await issues_resp.json())
        comments = list(await comments_resp.json())
    except Exception:
        prs, issues, comments = [], [], []

    blocks = _format_contributor_data(prs, issues, comments)
    return {"response_type": "in_channel", "blocks": blocks, "text": "Contributors Activity"}


def _format_contributor_data(prs: list, issues: list, comments: list) -> list:
    """Build Slack Block Kit blocks from GitHub contribution data."""
    user_data: dict = {}

    for pr in prs:
        if isinstance(pr, dict) and pr.get("user"):
            u = pr["user"]["login"]
            user_data.setdefault(u, {"prs": 0, "issues": 0, "comments": 0})
            user_data[u]["prs"] += 1

    for issue in issues:
        if isinstance(issue, dict) and issue.get("user"):
            u = issue["user"]["login"]
            user_data.setdefault(u, {"prs": 0, "issues": 0, "comments": 0})
            user_data[u]["issues"] += 1

    for comment in comments:
        if isinstance(comment, dict) and comment.get("user"):
            u = comment["user"]["login"]
            user_data.setdefault(u, {"prs": 0, "issues": 0, "comments": 0})
            user_data[u]["comments"] += 1

    if not user_data:
        return [{"type": "section", "text": {"type": "mrkdwn", "text": "No data available"}}]

    mu = max(len(u) for u in user_data)
    mp, mi, mc = 10, 15, 9
    for c in user_data.values():
        mp = max(mp, len(str(c["prs"])))
        mi = max(mi, len(str(c["issues"])))
        mc = max(mc, len(str(c["comments"])))

    header = (
        f"{'User':<{mu}}  {'PRs Merged':<{mp}}  {'Issues Resolved':<{mi}}  {'Comments':<{mc}}\n"
    )
    separator = f"{'-'*mu}  {'-'*mp}  {'-'*mi}  {'-'*mc}\n"
    rows = [header, separator]
    for u, c in user_data.items():
        rows.append(
            f"{u:<{mu}}  {c['prs']:<{mp}}  {c['issues']:<{mi}}  {c['comments']:<{mc}}\n"
        )
    table = "".join(rows)
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Contributor Data*\n```\n{table}\n```"},
        }
    ]


async def _handle_ghissue(text: str, env) -> dict:
    """Handle the /ghissue slash command."""
    title = text.strip()
    if not title:
        return {"response_type": "ephemeral", "text": "Please provide an issue title."}

    owner = getattr(env, "GITHUB_REPO_OWNER", "OWASP-BLT")
    repo_name = getattr(env, "GITHUB_REPO_NAME", "BLT-Sammich")

    try:
        resp = await _fetch(
            f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/issues",
            method="POST",
            headers={
                "Authorization": f"token {env.GITHUB_TOKEN}",
                "Content-Type": "application/json",
                "User-Agent": "BLT-Sammich-Worker",
            },
            body=json.dumps({"title": title}),
        )
        data = dict(await resp.json())
        if resp.status == 201:
            return {
                "response_type": "in_channel",
                "text": f"Issue created successfully: {data['html_url']}",
            }
        return {"response_type": "ephemeral", "text": "Failed to create issue."}
    except Exception:
        return {"response_type": "ephemeral", "text": "Failed to create issue."}


async def _handle_project(text: str, env) -> dict:
    """Handle the /project slash command."""
    project_data = await _get_projects(env)
    project_name = text.strip().lower()

    if project_name and project_name in project_data:
        info = project_data[project_name]
        project_list = "\n".join(info)
        return {
            "response_type": "in_channel",
            "text": f"Hello, here is the information about '{project_name}':\n{project_list}",
        }

    projects = list(project_data.keys())
    num_dropdowns = math.ceil(len(projects) / PROJECTS_PER_PAGE)
    blocks = []
    for i in range(num_dropdowns):
        slc = projects[i * PROJECTS_PER_PAGE : (i + 1) * PROJECTS_PER_PAGE]
        options = [{"text": {"type": "plain_text", "text": p[:75]}, "value": p} for p in slc]
        blocks.append(
            {
                "type": "section",
                "block_id": f"project_select_block_{i}",
                "text": {"type": "mrkdwn", "text": f"Select a project (Page {i + 1}):"},
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": f"Select a project (Page {i + 1})",
                    },
                    "options": options,
                    "action_id": f"project_select_action_{i}",
                },
            }
        )
    return {"response_type": "in_channel", "blocks": blocks, "text": "Available Projects"}


async def _handle_repo(text: str, env) -> dict:
    """Handle the /repo slash command."""
    repo_data = await _get_repos(env)
    tech = text.strip().lower()

    if tech and tech in repo_data:
        repos_list = "\n".join(repo_data[tech])
        return {
            "response_type": "in_channel",
            "text": f"Hello, you can implement your '{tech}' knowledge here:\n{repos_list}",
        }

    blocks = [
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
                    "text": {"type": "plain_text", "text": t},
                    "value": t,
                    "action_id": f"plugin_repo_button_{t}",
                }
                for t in repo_data
            ],
        },
    ]
    return {"response_type": "in_channel", "blocks": blocks, "text": "Available Technologies"}


# ---------------------------------------------------------------------------
# Interactive component (action) handler
# ---------------------------------------------------------------------------


async def _handle_action(payload: dict, env) -> dict:
    """Handle Slack interactive component callbacks (buttons, dropdowns)."""
    actions = payload.get("actions", [])
    if not actions:
        return {"text": "No action found."}

    action = actions[0]
    action_id = action.get("action_id", "")

    if re.match(r"project_select_action_", action_id):
        project_data = await _get_projects(env)
        selected = (action.get("selected_option") or {}).get("value", "")
        info = project_data.get(selected, [])
        return {
            "response_type": "in_channel",
            "text": f"Hello, here is the information about '{selected}':\n" + "\n".join(info),
        }

    if re.match(r"plugin_repo_button_", action_id):
        repo_data = await _get_repos(env)
        clicked = action.get("value", "")
        repos = repo_data.get(clicked, [])
        return {
            "response_type": "in_channel",
            "text": f"Hello, you can implement your '{clicked}' knowledge here:\n"
            + "\n".join(repos),
        }

    return {"text": "Unknown action."}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def on_fetch(request, env):
    """Cloudflare Workers entry point – routes incoming HTTP requests.

    GET /              is served automatically from public/index.html via the
                       [assets] binding in wrangler.toml.
    POST /slack/command  Slack slash commands (signature-verified).
    POST /slack/action   Slack interactive component callbacks (signature-verified).
    """
    parsed = urlparse(request.url)
    path = parsed.path
    method = request.method

    if method == "POST":
        raw_body = await request.text()

        # Every Slack request must carry a valid signature
        if not _verify_slack_signature(request.headers, raw_body, env.SLACK_SIGNING_SECRET):
            return _text_response("Unauthorized", status=401)

        if path == "/slack/command":
            params = parse_qs(raw_body)
            command = params.get("command", [""])[0]
            text = params.get("text", [""])[0]

            if command == "/contributors":
                data = await _handle_contributors(env)
            elif command == "/ghissue":
                data = await _handle_ghissue(text, env)
            elif command == "/project":
                data = await _handle_project(text, env)
            elif command == "/repo":
                data = await _handle_repo(text, env)
            else:
                data = {"response_type": "ephemeral", "text": f"Unknown command: {command}"}

            return _json_response(data)

        if path == "/slack/action":
            params = parse_qs(raw_body)
            payload = json.loads(params.get("payload", ["{}"])[0])
            data = await _handle_action(payload, env)
            return _json_response(data)

    return _text_response("Not Found", status=404)

from src import worker


def test_verify_slack_signature_accepts_valid_request():
    secret = "signing-secret"
    timestamp = "1710000000"
    body = "token=value&command=%2Fproject"
    import hashlib
    import hmac

    expected = (
        "v0="
        + hmac.new(
            secret.encode("utf-8"),
            "v0:{0}:{1}".format(timestamp, body).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    assert worker.verify_slack_signature(
        secret, timestamp, body, expected, now_ts=1710000000
    )


def test_verify_slack_signature_rejects_expired_request():
    assert not worker.verify_slack_signature(
        "secret",
        "1710000000",
        "body",
        "v0=invalid",
        now_ts=1710000601,
    )


def test_project_response_without_query_returns_blocks():
    response = worker.project_response("")
    assert response["blocks"]
    assert response["text"] == "Choose a project to inspect."


def test_repo_response_without_query_returns_blocks():
    response = worker.repo_response("")
    assert response["blocks"]
    assert response["text"] == "Choose a technology to inspect."


def test_interaction_response_returns_project_detail():
    response = worker.interaction_response(
        {
            "actions": [
                {
                    "action_id": "project_select_action_0",
                    "selected_option": {"value": "www-project-zap"},
                }
            ]
        }
    )
    assert "www-project-zap" in response["text"]


def test_build_blocks_are_chunked_and_capped():
    project_blocks = worker.build_project_selection_blocks(
        ["project-{0}".format(index) for index in range(201)]
    )
    assert len(project_blocks) == 3

    repo_blocks = worker.build_repo_selection_blocks(
        {"python": ["https://example.com"]}
    )
    assert len(repo_blocks) == 2


def test_summarize_contributors_sorts_by_total_activity():
    rows = worker.summarize_contributors(
        [{"user": {"login": "alice"}}, {"user": {"login": "alice"}}],
        [{"user": {"login": "bob"}}],
        [{"user": {"login": "bob"}}, {"user": {"login": "bob"}}],
    )
    assert rows[0]["user"] == "bob"
    assert rows[0]["total"] == 3


def test_render_team_join_message_uses_team_template():
    message = worker.render_team_join_message(
        {"user": {"id": "U123", "name": "newperson"}},
        "T04T40NHX",
    )
    assert message == "welcome newperson"


class _Env:
    pass


def test_blt_app_url_response_returns_url_when_set():
    env = _Env()
    setattr(env, "SLACK_APP_URL", "https://api.slack.com/apps/A12345/general")
    response = worker.blt_app_url_response(env)
    assert response["text"] == "https://api.slack.com/apps/A12345/general"


def test_blt_app_url_response_returns_error_when_missing():
    env = _Env()
    response = worker.blt_app_url_response(env)
    assert response["text"] == "Missing required environment variable: SLACK_APP_URL"


def test_current_config_message_formats_public_values():
    env = _Env()
    setattr(env, "GITHUB_ACTIVITY_OWNER", "OWASP-BLT")
    setattr(env, "GITHUB_ACTIVITY_REPO", "BLT-Lettuce")
    setattr(env, "GITHUB_ISSUE_OWNER", "OWASP-BLT")
    setattr(env, "GITHUB_ISSUE_REPO", "BLT-Sammich")
    setattr(
        env, "SLACK_REDIRECT_URL", "https://sammich.owaspblt.org/oauth/slack/callback"
    )
    setattr(env, "SLACK_APP_URL", "https://api.slack.com/apps/A12345/general")

    message = worker.current_config_message(env, "T123", "U123")
    assert "team_id: T123" in message
    assert "installer_user_id: U123" in message
    assert "github_activity_repo: OWASP-BLT/BLT-Lettuce" in message
    assert "slack_app_url: https://api.slack.com/apps/A12345/general" in message


def test_build_slack_install_url_uses_required_env_vars():
    env = _Env()
    setattr(env, "SLACK_CLIENT_ID", "123.456")
    setattr(env, "SLACK_REDIRECT_URL", "https://example.com/oauth/slack/callback")
    setattr(env, "SLACK_OAUTH_STATE", "state-token")
    setattr(env, "SLACK_OAUTH_SCOPES", "commands,chat:write")
    setattr(env, "SLACK_OAUTH_USER_SCOPES", "users:read")

    install_url = worker.build_slack_install_url(env)
    assert install_url.startswith("https://slack.com/oauth/v2/authorize?")
    assert "client_id=123.456" in install_url
    assert (
        "redirect_uri=https%3A%2F%2Fexample.com%2Foauth%2Fslack%2Fcallback"
        in install_url
    )
    assert "state=state-token" in install_url
    assert "scope=commands%2Cchat%3Awrite" in install_url
    assert "user_scope=users%3Aread" in install_url


def test_format_advisory_blocks_with_advisories():
    advisories = [
        {
            "ghsa_id": "GHSA-1234-5678-9012",
            "summary": "Remote code execution vulnerability",
            "severity": "critical",
            "html_url": "https://github.com/advisories/GHSA-1234-5678-9012",
            "cve_id": "CVE-2024-12345",
        }
    ]
    response = worker.format_advisory_blocks("OWASP-BLT", "BLT", advisories)
    assert "OWASP-BLT/BLT" in response["text"]
    assert response["blocks"]
    block_text = response["blocks"][1]["text"]["text"]
    assert "GHSA-1234-5678-9012" in block_text
    assert "CVE-2024-12345" in block_text
    assert "CRITICAL" in block_text
    assert "Remote code execution vulnerability" in block_text


def test_format_advisory_blocks_empty():
    response = worker.format_advisory_blocks("OWASP-BLT", "BLT", [])
    assert "No published security advisories" in response["text"]
    assert response["blocks"]


def test_format_advisory_blocks_without_optional_fields():
    advisories = [
        {
            "ghsa_id": "GHSA-0000-0000-0000",
            "summary": "Minimal advisory",
            "severity": "low",
        }
    ]
    response = worker.format_advisory_blocks("owner", "repo", advisories)
    assert response["blocks"]
    block_text = response["blocks"][1]["text"]["text"]
    assert "GHSA-0000-0000-0000" in block_text
    assert "LOW" in block_text


def test_format_github_activity_blocks_with_all_data():
    commits = [
        {
            "sha": "abc1234def",
            "commit": {"message": "Fix security bug\n\nDetails here", "author": {"name": "alice"}},
            "author": {"login": "alice"},
            "html_url": "https://github.com/OWASP-BLT/BLT/commit/abc1234def",
        }
    ]
    issues = [
        {
            "number": 42,
            "title": "Security issue found",
            "html_url": "https://github.com/OWASP-BLT/BLT/issues/42",
            "user": {"login": "bob"},
        }
    ]
    prs = [
        {
            "number": 10,
            "title": "Add vulnerability scanner",
            "html_url": "https://github.com/OWASP-BLT/BLT/pull/10",
            "user": {"login": "charlie"},
        }
    ]
    response = worker.format_github_activity_blocks(
        "OWASP-BLT", "BLT", commits, issues, prs
    )
    assert "OWASP-BLT/BLT" in response["text"]
    assert len(response["blocks"]) == 4
    commits_block = response["blocks"][1]["text"]["text"]
    assert "alice" in commits_block
    assert "Fix security bug" in commits_block
    issues_block = response["blocks"][2]["text"]["text"]
    assert "bob" in issues_block
    assert "Security issue found" in issues_block
    prs_block = response["blocks"][3]["text"]["text"]
    assert "charlie" in prs_block
    assert "Add vulnerability scanner" in prs_block


def test_format_github_activity_blocks_empty():
    response = worker.format_github_activity_blocks("OWASP-BLT", "BLT", [], [], [])
    assert "OWASP-BLT/BLT" in response["text"]
    assert "No recent activity" in response["blocks"][-1]["text"]["text"]


def test_format_github_activity_blocks_renders_passed_issues():
    commits = []
    issues = [
        {"number": 1, "title": "Real issue", "user": {"login": "alice"}, "html_url": ""},
        {"number": 2, "title": "Another issue", "user": {"login": "bob"}, "html_url": ""},
    ]
    prs = []
    response = worker.format_github_activity_blocks("owner", "repo", commits, issues, prs)
    issues_block = response["blocks"][1]["text"]["text"]
    assert "Real issue" in issues_block
    assert "Another issue" in issues_block


def test_help_response_includes_new_commands():
    response = worker.help_response()
    assert "/ghactivity" in response["text"]
    assert "/vuln" in response["text"]

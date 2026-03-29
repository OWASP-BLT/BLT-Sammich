# BLT-Sammich Slack Bot

**BLT-Sammich** is a feature-rich Slack bot built for the OWASP BLT (Bug Logging Tool) community. This bot helps teams interact with GitHub repositories, track contributors, manage projects, and discover OWASP resources directly from Slack.

> **Note:** The core functionality of this bot has been merged into the [main BLT repository](https://github.com/OWASP-BLT/BLT). This repository serves as the standalone implementation and development base for the BLT Slack bot.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Setup](#-setup)
- [Slack Commands](#-slack-commands)
- [Local Development](#-local-development)
- [Slash Commands](#-slash-commands)
- [Comparison with Main BLT](#-comparison-with-main-blt)
- [Development](#-development)
- [Contributing](#-contributing)

## ✨ Features

### Core Commands

#### `/contributors` 
**Status:** ✅ Standalone Feature (Not in main BLT)

Displays contributor activity for the OWASP-BLT/Lettuce repository over the last 7 days.
- Shows PRs merged, issues resolved, and comments made
- Formatted table view with user statistics
- Aggregates GitHub activity data

**Usage:**
```
/contributors
```

#### `/ghissue [title]`
**Status:** ✅ Standalone Feature (Not in main BLT)

Creates a new GitHub issue directly from Slack.
- Creates issues in the configured repository (default: OWASP-BLT/BLT-Sammich)
- Returns a direct link to the created issue
- Requires GitHub token authentication

**Usage:**
```
/ghissue Fix login bug on mobile devices
```

#### `/project [project_name]`
**Status:** ✅ Standalone Feature (Not in main BLT)

Retrieves information about OWASP projects.
- Shows project details from curated projects.json database
- Interactive dropdown for project selection when no name specified
- Supports pagination for large project lists (100 projects per page)

**Usage:**
```
/project zap                    # Direct lookup
/project                        # Browse all projects
```

#### `/repo [technology]`
**Status:** ✅ Standalone Feature (Not in main BLT)

Finds repositories based on technology stack or programming language.
- Matches technologies from repos.json database
- Interactive button selection when no tech specified
- Returns curated list of relevant repositories

**Usage:**
```
/repo python                    # Direct tech search
/repo                          # Browse technologies
```

### Main BLT Repository Commands

The following commands are available in the main BLT repository but **NOT in BLT-Sammich**:

#### `/discover [search_term]` 
**Status:** ⚠️ Main BLT Only

Searches and browses OWASP repositories.
- Searches all OWASP GitHub repositories
- Supports pagination for results
- Interactive repository selection to view issues
- Caches repository data for performance

**Why not in BLT-Sammich?** This feature was developed directly in the main BLT repository as part of the integration.

### Plugins Architecture

BLT-Sammich is built with a modular plugin system designed to run efficiently at the edge:

1. **Contributors Plugin** (`src/sammich/plugins/contributors.py`)
   - Fetches GitHub data via REST API
   - Formats contributor statistics
   - Displays activity in formatted tables

2. **Project Plugin** (`src/sammich/plugins/project.py`)
   - Manages OWASP project database lookups natively on the edge
   - Handles pagination for large datasets
   - Returns interactive Slack UI components

3. **Reminder Plugin** (`src/sammich/plugins/reminder.py`)
   - Parse natural language time expressions
   - Formats scheduled messages for channels
   - *(Note: Currently **disabled**; planned migration from background tasks to Cloudflare Cron Triggers)* 

### Data Files

- **`data/projects.json`**: Database of 800+ OWASP projects with descriptions and links
- **`data/repos.json`**: Technology-to-repository mapping for development resources

## 🏗️ Architecture

### Tech Stack
- **Edge Runtime:** Cloudflare Python Workers (Pyodide) - A zero-dependency, event-driven model that runs Python natively in the V8 engine
- **Database:** Cloudflare D1 (Serverless SQLite)
- **GitHub Integration:** Edge-compatible REST requests
- **Deployment & Testing:** Wrangler (`npx wrangler`) 

### How It Connects to Main BLT

```text
┌─────────────────────────────────────────────────────┐
│                  User in Slack                      │
└─────────────────┬───────────────────────────────────┘
                  │ (Slash Commands via Webhooks)
                  v
         ┌────────────────────┐
         │ Cloudflare Worker  │  <-- Python (Pyodide)
         │   (BLT-Sammich)    │      Zero-Dependency
         └─┬────────────────┬─┘      Event-Driven
           │                │
           v                v
  ┌────────────────┐ ┌─────────────────────┐
  │ Cloudflare D1  │ │     GitHub API      │
  │ (Local SQLite) │ │ OWASP-BLT/Lettuce   │
  └────────────────┘ └─────────────────────┘

**Key Connections:**
- Both bots interact with GitHub APIs independently
- BLT-Sammich focuses on BLT-specific workflows and project discovery
- Main BLT bot provides broader OWASP repository exploration
- No direct communication between the two bot implementations

## 🚀 Setup

For initial setup and local development instructions, see the **[Local Development](#-local-development)** section below.

## 📚 Slack Commands

This section documents each Slack command with purpose, example usage, and expected output.

### /contributors

**Purpose:** Displays contributor activity for the OWASP-BLT/Lettuce repository over the last 7 days. Shows PRs merged, issues resolved, and comments made in a formatted table view.

**Example:**
```
/contributors
```

**Expected Output:** A formatted table showing contributor statistics including GitHub usernames, PRs merged, issues resolved, and comments made. Returns "No data available" if no activity in the period.

---

### /ghissue

**Purpose:** Creates a new GitHub issue directly from Slack. Issues are created in the configured repository (default: OWASP-BLT/BLT-Sammich).

**Example:**
```
/ghissue Fix login bug on mobile devices
```

**Expected Output:** A success message with a direct link to the created issue (e.g., `Issue created successfully: https://github.com/OWASP-BLT/BLT-Sammich/issues/123`). Returns an error message if creation fails.

---

### /project

**Purpose:** Retrieves information about OWASP projects from the curated projects database. Supports direct lookup by name or interactive browsing when no name is specified.

**Example:**
```
/project zap                    # Direct lookup for ZAP project
/project                        # Browse all projects (interactive dropdown)
```

**Expected Output:** For direct lookup, displays project details including description and links. When used without arguments, shows an interactive dropdown to select from 800+ OWASP projects (100 per page).

---

### /repo

**Purpose:** Finds repositories based on technology stack or programming language. Matches from the curated repos.json database of OWASP development resources.

**Example:**
```
/repo python                    # Direct tech search
/repo                           # Browse available technologies (interactive buttons)
```

**Expected Output:** For direct search, returns a list of repositories where you can apply that technology. When used without arguments, displays buttons to select from available technologies (e.g., Python, JavaScript, Go).

---

## 📚 Slash Commands

| Command | Description | Example | Available In |
|---------|-------------|---------|--------------|
| `/contributors` | Show recent contributor activity | `/contributors` | BLT-Sammich only |
| `/ghissue [title]` | Create GitHub issue | `/ghissue Bug in login form` | BLT-Sammich only |
| `/project [name]` | Find OWASP project info | `/project zap` | BLT-Sammich only |
| `/repo [tech]` | Find repos by technology | `/repo python` | BLT-Sammich only |
| `/discover [term]` | Search all OWASP repos | `/discover security` | Main BLT only |
| `/help [term]` | Show help menu | `/help` | BLT-Sammich only |


## 🧑‍💻 Local Development

This section explains how to run the BLT-Sammich Slack bot locally for development and testing using the Cloudflare Workers ecosystem.

### Prerequisites

- **Node.js & npm** - [Download Node.js](https://nodejs.org/en/download/). This is required to run Wrangler.
- **Slack workspace** with admin access to create and configure a Slack app.
- **GitHub account**
with a Personal Access Token (for `/ghissue` and `/contributors` commands)
- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)
- **Wrangler** - CLI for developing, testing, and deploying Cloudflare Workers. Install via: `npm install -g wrangler`

### Steps to run locally
**1.Clone the repository**
```bash
git clone https://github.com/OWASP-BLT/BLT-Sammich.git
cd BLT-Sammich
```

**2. Configure Local Database (D1)**
Before running the bot, you must initialize the local D1 database schema:
```bash
npx wrangler d1 execute blt-sammich --local --file=migrations/0001_initial.sql
```

**3. Configure environment variables**

Create a `.secrets` file in the project root (copy from the sample):
```bash
cp .secrets.sample .secrets
```

Edit `.secrets` with your credentials:
```
SLACK_APP_TOKEN=xapp-your-app-level-token
SLACK_BOT_TOKEN=xoxb-your-bot-user-oauth-token
GITHUB_TOKEN=ghp_your-github-personal-access-token
```

> **Note:** Never commit `.secrets` to version control. It is listed in `.gitignore`.

**4. Start the bot**
```bash
npx wrangler dev
```

You should see:
```text
⎔ Starting local server...
[wrangler:info] Ready on http://127.0.0.1:8787
```

The bot uses **Cloudflare Workers** natively. For local development, `wrangler dev` creates a local server, but to test Slack commands and webhooks, you must expose your local server using a tunnel like **ngrok** or **cloudflared** (see Troubleshooting).

### Troubleshooting

| Problem | Solution |
|---------|----------|
| **`wrangler: command not found`** | Install Wrangler: `npm install -g wrangler` or use `npx wrangler` |
| **`Resource location: local` Error** | Ensure you've run the `d1 execute` command to create the local database first |
| **`KeyError` when reading `.secrets`** | Ensure `.secrets` exists and contains all three variables: `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`, `GITHUB_TOKEN` |
| **Bot not responding in Slack** | Verify the bot is installed in your workspace. Check that the Request URL in Slack points to your local tunnel (if testing webhooks) |
| **`/ghissue` fails with "Failed to create issue"** | Verify your `GITHUB_TOKEN` has `repo` scope and the correct owner/repo is set in `.secrets` |
| **`/contributors` returns "No data available"** | This is normal if there has been no activity in OWASP-BLT/Lettuce in the last 7 days |

For running tests and code formatting, see the [Development](#-development) section.

## 🔄 Comparison with Main BLT

### Features Unique to BLT-Sammich
✅ **In BLT-Sammich Only:**
- `/contributors` - GitHub activity tracking
- `/ghissue` - Issue creation from Slack
- `/project` - OWASP projects database
- `/repo` - Technology-based repository discovery
- Plugin architecture for extensibility
- Curated projects and repos JSON databases

### Features in Main BLT Only
⚠️ **In Main BLT Only:**
- `/discover` - Full OWASP repository search
- Slack integration with Django web app
- OAuth-based Slack workspace integration
- Daily timelog updates
- Welcome messages for new members
- Activity logging and monitoring
- Workspace-specific configurations

### Why Two Implementations?

**BLT-Sammich** serves as:
1. **Standalone Bot** - Can run independently without the full BLT web application
2. **Development Environment** - Faster iteration for Slack-specific features
3. **Specialized Commands** - Focus on BLT project management workflows
4. **Plugin Testbed** - Experimental features before main BLT integration

**Main BLT** provides:
1. **Full Integration** - Deep integration with BLT's bug tracking system
2. **Web Dashboard** - Configure bot settings through web UI
3. **Enterprise Features** - Multi-workspace support, admin controls
4. **Production Ready** - Comprehensive logging and monitoring

## 🛠️ Development

### Project Structure
```text
BLT-Sammich/
├── wrangler.toml         # Cloudflare Worker configuration
├── src/
│   └── worker.py         # Main bot application (Pyodide)
├── data/
│   ├── projects.json     # OWASP projects database
│   └── repos.json          # Technology repository mapping
├── migrations/           # D1 database schema
├── public/               # Static assets
└── tests/                # Unit tests
```

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Run linter
poetry run ruff check .

# Format code
poetry run ruff format .
```

### Adding a New Command

1. Create handler in `app.py`:
```python
@app.command("/mycommand")
def my_command(ack, say, command):
    ack()
    # Your logic here
    say("Response message")
```

2. Register command in Slack App manifest
3. Test in your workspace
4. Add tests in `tests/`

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Run tests**
   ```bash
   poetry run pytest
   ```
5. **Commit with clear message**
   ```bash
   git commit -m "Add amazing feature"
   ```
6. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Contribution Ideas
- 🔧 Integrate the `/setreminder` command from reminder.py plugin
- 📊 Add analytics for command usage
- 🌐 Support for more OWASP data sources
- 🔍 Enhanced search capabilities
- 🧪 Improve test coverage
- 📝 Additional documentation

## 📄 License

This project is part of OWASP BLT and follows the same license terms. See [LICENSE.md](LICENSE.md) for details.

## 🔗 Links

- [Main BLT Repository](https://github.com/OWASP-BLT/BLT)
- [OWASP BLT Website](https://owasp.org/www-project-bug-logging-tool/)
- [Slack Bot Documentation](https://github.com/OWASP-BLT/BLT/blob/main/docs/bot-setup.md)
- [Report Issues](https://github.com/OWASP-BLT/BLT-Sammich/issues)

## 💬 Support

Need help? 
- 📖 Check the [Main BLT Documentation](https://github.com/OWASP-BLT/BLT)
- 🐛 [Report a Bug](https://github.com/OWASP-BLT/BLT-Sammich/issues)
- 💡 [Request a Feature](https://github.com/OWASP-BLT/BLT-Sammich/issues)
- 💬 Join the OWASP BLT Slack workspace

---

Made with ❤️ by the OWASP BLT community


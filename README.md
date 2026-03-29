# Composio Multi-Account Skill

A Claude skill that lets you connect multiple accounts to the same Composio toolkit — for example, linking both a personal and work Gmail, or multiple Google Calendar accounts.

## The problem

The Composio MCP's built-in `COMPOSIO_MANAGE_CONNECTIONS` tool only supports one active connection per toolkit. If you already have Gmail connected with one Google account and want to add a second, there's no way to do it through the standard MCP interface.

## What this skill does

It calls the Composio REST API directly (via the Remote Workbench) with the `allow_multiple: true` parameter, generating an authentication link for each additional account you want to connect. You click the link, sign in with the new account, and it's added alongside your existing connection.

Works for any Composio toolkit — Google apps, Slack, GitHub, etc.

## Installation

### Option A: Install the `.skill` file

1. Download `composio-multi-account.skill` from the [Releases](../../releases) page
2. Open the Claude desktop app
3. Drag the `.skill` file into the chat, or go to **Settings > Skills** and install it from there

### Option B: Clone the repo

1. Clone this repository
2. Copy the `composio-multi-account` folder into your Claude skills directory:
   - macOS: `~/.claude/skills/`
   - Or wherever your Cowork session mounts skills

## Prerequisites

- **Composio MCP** must be connected in your Claude session (the skill uses `COMPOSIO_REMOTE_WORKBENCH` to make API calls)
- At least one account already connected to the toolkit you want to add more accounts to

## Usage

Just ask Claude naturally. These kinds of prompts will trigger the skill:

- "Add my work Gmail account to Composio"
- "Connect a second Google Calendar"
- "I want to link both my personal and work Google accounts"
- "Add another account to Google Drive"

Claude will generate a time-limited authentication link for each toolkit. Click the link, sign in with the account you want to add, and you're done.

## How it works

1. Claude reads your Composio session to find your `user_id` and the `auth_config_id` for each toolkit
2. It POSTs to `POST /api/v3/connected_accounts/link` with `allow_multiple: true`
3. Composio returns a branded authentication URL (valid for ~10 minutes)
4. You click the link and sign in with the new account
5. Claude verifies the connection is active

Each connected account gets a unique `connected_account_id` that can be passed when executing tools to target a specific account.

## File structure

```
composio-multi-account/
├── SKILL.md                        # Skill instructions (read by Claude)
├── scripts/
│   └── add_connections.py          # Helper functions for the Remote Workbench
└── README.md                       # This file
```

## Authors

**Christine B.** — Founder, [Social AI](https://www.socialai.jp)

**Claude** (Anthropic) — Co-author

## License

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — Free to use and modify for non-commercial purposes. Attribution required.

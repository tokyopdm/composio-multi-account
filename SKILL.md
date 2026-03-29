---
name: composio-multi-account
description: "Add additional account connections to Composio toolkits when a user already has one account connected and wants to add more (e.g., connecting a second Gmail or Google Calendar account). Use this skill whenever the user mentions adding another account, connecting a second account, multi-account setup, or switching between accounts in Composio-connected apps. Also trigger when the user says things like 'connect my work email too', 'add my other Google account', or 'I need both accounts linked'. This skill is essential because the standard COMPOSIO_MANAGE_CONNECTIONS tool does not expose the allow_multiple parameter needed for this workflow."
---

# Composio Multi-Account Connection Skill

## Why this skill exists

The standard `COMPOSIO_MANAGE_CONNECTIONS` MCP tool can check or initiate a single connection per toolkit, but it has no way to add a *second* account alongside an existing one. This skill works around that limitation by calling the Composio REST API directly through the `COMPOSIO_REMOTE_WORKBENCH`, using the `allow_multiple: true` parameter that the MCP tool doesn't expose.

## When to use this

- The user wants to connect an additional account to a toolkit that already has an active connection (e.g., a second Gmail, a work Google Calendar alongside a personal one)
- The user wants to generate auth links for multiple new accounts across several toolkits at once
- The user asks about managing or switching between multiple connected accounts for the same service

## How it works under the hood

The Composio backend stores connections per `(user_id, auth_config_id)` pair. By default, initiating a new connection for a toolkit that already has one will fail. Passing `allow_multiple: true` in the POST body tells the backend to create an additional connection rather than rejecting or replacing the existing one.

Each connection gets its own `connected_account_id`. When executing tools later, you pass this ID to target a specific account — for example, `run_composio_tool(..., account="ca_xxxxx")` in the workbench.

## Step-by-step procedure

### Step 1: Retrieve session context

Every Composio MCP session has a `user_id` and a map of configured toolkits to their `auth_config_id` values. You need both to generate connection links.

Run this in `COMPOSIO_REMOTE_WORKBENCH`:

```python
import os, requests

backend_url = os.environ.get('BACKEND_URL', 'https://backend.composio.dev')
access_key = os.environ.get('COMPOSIO_WORKBENCH_ACCESS_KEY')
session_id = os.environ.get('COMPOSIO_TOOLROUTER_SESSION_ID')

resp = requests.get(
    f"{backend_url}/api/v3/tool_router/session/{session_id}",
    headers={'x-session-access-key': access_key, 'Content-Type': 'application/json'}
)
session_data = resp.json()

user_id = session_data['config']['user_id']
auth_configs = session_data['config']['auth_configs']

print(f"User ID: {user_id}")
print("Available toolkits:")
for toolkit, config_id in sorted(auth_configs.items()):
    print(f"  {toolkit}: {config_id}")
```

### Step 2 (optional): Check existing connections

Before adding new accounts, you may want to see what's already connected. Call `COMPOSIO_MANAGE_CONNECTIONS` with the relevant toolkit names — it will show the current active connection and which email/account it belongs to.

### Step 3: Generate connection links

For each toolkit the user wants to add an account to, POST to the `connected_accounts/link` endpoint with `allow_multiple: true`.

```python
import os, requests, json

backend_url = os.environ.get('BACKEND_URL', 'https://backend.composio.dev')
access_key = os.environ.get('COMPOSIO_WORKBENCH_ACCESS_KEY')

url = f"{backend_url}/api/v3/connected_accounts/link"
headers = {'x-session-access-key': access_key, 'Content-Type': 'application/json'}

# Substitute actual values from Step 1
user_id = "..."
toolkits_to_connect = {
    "Gmail": "ac_...",
    "Google Calendar": "ac_...",
}

for name, auth_config_id in toolkits_to_connect.items():
    resp = requests.post(url, json={
        "auth_config_id": auth_config_id,
        "user_id": user_id,
        "allow_multiple": True
    }, headers=headers)

    if resp.status_code == 201:
        data = resp.json()
        print(f"OK  {name}: {data['redirect_url']}")
    else:
        print(f"ERR {name}: {resp.status_code} — {resp.text[:200]}")
```

### Step 4: Present links to the user

Format the `redirect_url` values as clickable markdown links. Important things to tell the user:
- The links expire in approximately **10 minutes**
- They should sign in with the **new** account (not the one already connected)

Example output:

```markdown
Here are your connection links (expire in ~10 minutes). Sign in with the account you want to add:

1. [Connect Gmail](https://connect.composio.dev/link/lk_xxxxx)
2. [Connect Google Calendar](https://connect.composio.dev/link/lk_yyyyy)
```

### Step 5: Verify

After the user confirms they've authenticated, call `COMPOSIO_MANAGE_CONNECTIONS` for the relevant toolkits to confirm the new connections are active.

## Important notes

- **Auth configs are reused.** The `auth_config_id` contains the OAuth credentials configured in the Composio dashboard. All accounts for the same toolkit share the same auth config — only the `connected_account_id` differs.
- **Link expiry.** Connection links expire in ~10 minutes. Generate fresh ones if the user needs more time.
- **Targeting a specific account.** When executing tools in the workbench, use `run_composio_tool(..., account="ca_xxxxx")`. The `COMPOSIO_MULTI_EXECUTE_TOOL` does not directly expose account selection — use the workbench for multi-account tool execution.
- **Session-scoped auth.** The `x-session-access-key` header authenticates against the tool router session, not the Composio project API key. The skill works within any active Composio MCP session without needing the user's API key.
- **Works for any toolkit.** While Google apps are the most common use case, this approach works for any Composio-connected toolkit (Slack, GitHub, etc.).

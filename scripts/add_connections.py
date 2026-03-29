"""
Composio Multi-Account Connection Helpers

Convenience functions for adding additional account connections to Composio
toolkits that already have an active connection. Uses the allow_multiple=True
parameter on the Composio REST API, which the standard COMPOSIO_MANAGE_CONNECTIONS
MCP tool does not expose.

These functions are designed to run inside the COMPOSIO_REMOTE_WORKBENCH, which
provides the required environment variables (COMPOSIO_WORKBENCH_ACCESS_KEY,
COMPOSIO_TOOLROUTER_SESSION_ID, BACKEND_URL).

Quick start (paste into COMPOSIO_REMOTE_WORKBENCH):

    # List what toolkits are available
    list_available_toolkits()

    # Add a second account for one toolkit
    link = add_connection("gmail")
    print(link["redirect_url"])  # Share this with the user

    # Add second accounts for several toolkits at once
    links = add_connections(["gmail", "googlecalendar", "googledrive"])
"""

import os
import requests
import json
from typing import Dict, List, Optional


_BACKEND_URL = os.environ.get("BACKEND_URL", "https://backend.composio.dev")
_ACCESS_KEY = os.environ.get("COMPOSIO_WORKBENCH_ACCESS_KEY")
_SESSION_ID = os.environ.get("COMPOSIO_TOOLROUTER_SESSION_ID")

# Cache session context so we don't re-fetch on every call
_session_cache: Optional[dict] = None


def _get_session_context() -> tuple:
    """
    Fetch user_id and auth_configs from the Composio tool router session.

    Returns:
        (user_id, auth_configs) where auth_configs maps toolkit name -> auth_config_id
    """
    global _session_cache

    if _session_cache is not None:
        return _session_cache["user_id"], _session_cache["auth_configs"]

    url = f"{_BACKEND_URL}/api/v3/tool_router/session/{_SESSION_ID}"
    headers = {"x-session-access-key": _ACCESS_KEY, "Content-Type": "application/json"}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    _session_cache = {
        "user_id": data["config"]["user_id"],
        "auth_configs": data["config"]["auth_configs"],
    }
    return _session_cache["user_id"], _session_cache["auth_configs"]


def list_available_toolkits() -> Dict[str, str]:
    """
    Show all toolkits configured in the current Composio session.

    Returns:
        Dict mapping toolkit name to its auth_config_id.
    """
    _, auth_configs = _get_session_context()
    print("Available toolkits:")
    for name, config_id in sorted(auth_configs.items()):
        print(f"  {name}: {config_id}")
    return auth_configs


def add_connection(toolkit: str) -> dict:
    """
    Generate an allow_multiple connection link for a single toolkit.

    Args:
        toolkit: Toolkit name (e.g., "gmail", "googlecalendar", "slack").
                 Case-insensitive.

    Returns:
        On success: dict with redirect_url, connected_account_id, expires_at, link_token
        On failure: dict with error key describing what went wrong
    """
    user_id, auth_configs = _get_session_context()
    toolkit_lower = toolkit.lower()

    if toolkit_lower not in auth_configs:
        available = ", ".join(sorted(auth_configs.keys()))
        return {"error": f"Toolkit '{toolkit}' not found. Available: {available}"}

    url = f"{_BACKEND_URL}/api/v3/connected_accounts/link"
    headers = {"x-session-access-key": _ACCESS_KEY, "Content-Type": "application/json"}
    payload = {
        "auth_config_id": auth_configs[toolkit_lower],
        "user_id": user_id,
        "allow_multiple": True,
    }

    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 201:
        return resp.json()
    else:
        return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]}


def add_connections(toolkits: List[str]) -> Dict[str, dict]:
    """
    Generate allow_multiple connection links for multiple toolkits at once.

    Args:
        toolkits: List of toolkit names (e.g., ["gmail", "googlecalendar"]).

    Returns:
        Dict mapping each toolkit name to its result (redirect_url etc., or error).
    """
    user_id, auth_configs = _get_session_context()

    url = f"{_BACKEND_URL}/api/v3/connected_accounts/link"
    headers = {"x-session-access-key": _ACCESS_KEY, "Content-Type": "application/json"}

    results = {}
    for toolkit in toolkits:
        toolkit_lower = toolkit.lower()
        if toolkit_lower not in auth_configs:
            results[toolkit] = {"error": f"Toolkit '{toolkit}' not configured in this session"}
            print(f"SKIP {toolkit}: not configured")
            continue

        payload = {
            "auth_config_id": auth_configs[toolkit_lower],
            "user_id": user_id,
            "allow_multiple": True,
        }

        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 201:
            data = resp.json()
            results[toolkit] = data
            print(f"OK   {toolkit}: {data.get('redirect_url')}")
        else:
            results[toolkit] = {"error": f"HTTP {resp.status_code}", "detail": resp.text[:300]}
            print(f"ERR  {toolkit}: {resp.status_code}")

    return results

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
    print(link.get("redirect_url") or link.get("error"))

    # Add second accounts for several toolkits at once
    links = add_connections(["gmail", "googlecalendar", "googledrive"])
"""

import os
from typing import Any, Dict, List, Tuple

import requests

__all__ = ["list_available_toolkits", "add_connection", "add_connections"]

_REQUEST_TIMEOUT = 30

_cache: Dict[str, Any] = {}


def _env_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise OSError(f"Missing required environment variable: {name}")
    return value


def _headers() -> Dict[str, str]:
    return {"x-session-access-key": _env_required("COMPOSIO_WORKBENCH_ACCESS_KEY")}


def _backend_url() -> str:
    return os.environ.get("BACKEND_URL", "https://backend.composio.dev")


def _get_session_context() -> Tuple[str, Dict[str, str]]:
    """
    Fetch user_id and auth_configs from the Composio tool router session.

    Returns:
        (user_id, auth_configs) where auth_configs maps toolkit name -> auth_config_id

    Raises:
        OSError: If required environment variables are missing.
        requests.HTTPError: If the session endpoint returns a non-2xx status.
    """
    if "user_id" in _cache:
        return _cache["user_id"], _cache["auth_configs"]

    session_id = _env_required("COMPOSIO_TOOLROUTER_SESSION_ID")
    resp = requests.get(
        f"{_backend_url()}/api/v3/tool_router/session/{session_id}",
        headers=_headers(),
        timeout=_REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    _cache["user_id"] = data["config"]["user_id"]
    _cache["auth_configs"] = data["config"]["auth_configs"]
    return _cache["user_id"], _cache["auth_configs"]


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


def add_connection(toolkit: str) -> Dict[str, Any]:
    """
    Generate an allow_multiple connection link for a single toolkit.

    Args:
        toolkit: Toolkit name (e.g., "gmail", "googlecalendar", "slack").
                 Case-insensitive.

    Returns:
        On success: dict with redirect_url, connected_account_id, expires_at, link_token
        On failure: dict with error key describing what went wrong

    Raises:
        OSError: If required environment variables are missing.
        requests.HTTPError: If the session endpoint returns a non-2xx status.
    """
    user_id, auth_configs = _get_session_context()
    toolkit_lower = toolkit.lower()

    if toolkit_lower not in auth_configs:
        return {"error": f"Toolkit '{toolkit}' not found in this session"}

    resp = requests.post(
        f"{_backend_url()}/api/v3/connected_accounts/link",
        json={
            "auth_config_id": auth_configs[toolkit_lower],
            "user_id": user_id,
            "allow_multiple": True,
        },
        headers=_headers(),
        timeout=_REQUEST_TIMEOUT,
    )
    if resp.status_code == 201:
        return resp.json()
    return {"error": f"HTTP {resp.status_code}: connection link request failed"}


def add_connections(toolkits: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Generate allow_multiple connection links for multiple toolkits at once.

    Args:
        toolkits: List of toolkit names (e.g., ["gmail", "googlecalendar"]).

    Returns:
        Dict mapping each toolkit name to its result (redirect_url etc., or error).
    """
    results: Dict[str, Dict[str, Any]] = {}
    for toolkit in toolkits:
        result = add_connection(toolkit)
        if "error" in result:
            print(f"SKIP {toolkit}: {result['error']}")
        else:
            print(f"OK   {toolkit}: {result.get('redirect_url')}")
        results[toolkit] = result
    return results

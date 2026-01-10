#!/usr/bin/env python3
"""
Manage watchers on Jira issues.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python watch_issue.py PROJ-123 --watch
    python watch_issue.py PROJ-123 --add "John Smith"
    python watch_issue.py PROJ-123 --list
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# Add shared module to path for cache access
SCRIPT_DIR = Path(__file__).parent
SHARED_DIR = SCRIPT_DIR.parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))

try:
    from jira_cache import JiraCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


def get_auth_header() -> str:
    """Generate Basic Auth header from environment variables."""
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")

    if not email or not token:
        raise EnvironmentError(
            "JIRA_EMAIL and JIRA_API_TOKEN environment variables required"
        )

    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def get_base_url() -> str:
    """Get Jira base URL from environment."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")
    return base_url


def api_request(
    path: str,
    method: str = "GET",
    data: Optional[str] = None
) -> Optional[dict]:
    """Make authenticated API request to Jira."""
    url = urljoin(get_base_url(), path)
    req = Request(url, method=method)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = data.encode() if isinstance(data, str) else json.dumps(data).encode()

    try:
        with urlopen(req, timeout=30) as response:
            content = response.read().decode()
            return json.loads(content) if content else None
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 204:
            return None  # Success with no content
        elif e.code == 404:
            raise ValueError(f"Issue not found: {error_body}")
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError(f"Access denied: {error_body}")
        elif e.code == 400:
            raise ValueError(f"Bad request: {error_body}")
        else:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def get_current_user() -> dict:
    """Get current authenticated user."""
    if CACHE_AVAILABLE:
        try:
            cache = JiraCache()
            return cache.get_current_user()
        except Exception:
            pass

    result = api_request("/rest/api/3/myself")
    return {
        "accountId": result["accountId"],
        "displayName": result.get("displayName", ""),
    }


def find_user_by_name(name: str, project_key: str) -> Optional[dict]:
    """Find a user by display name."""
    if CACHE_AVAILABLE:
        try:
            cache = JiraCache()
            user = cache.get_user_by_name(project_key, name)
            if user:
                return user
        except Exception:
            pass

    # Search via API
    from urllib.parse import quote
    result = api_request(f"/rest/api/3/user/search?query={quote(name)}&maxResults=10")

    name_lower = name.lower()
    for user in result:
        if name_lower in user.get("displayName", "").lower():
            return {
                "accountId": user["accountId"],
                "displayName": user.get("displayName", ""),
            }

    return None


def get_watchers(issue_key: str) -> dict:
    """Get list of watchers for an issue."""
    result = api_request(f"/rest/api/3/issue/{issue_key}/watchers")
    watchers = []
    for w in result.get("watchers", []):
        watchers.append({
            "accountId": w.get("accountId", ""),
            "displayName": w.get("displayName", ""),
        })

    return {
        "issue": issue_key,
        "watchers": watchers,
        "count": result.get("watchCount", len(watchers)),
        "isWatching": result.get("isWatching", False),
    }


def add_watcher(issue_key: str, account_id: str) -> None:
    """Add a user as watcher."""
    # The API expects just the account ID as a quoted string
    api_request(
        f"/rest/api/3/issue/{issue_key}/watchers",
        method="POST",
        data=f'"{account_id}"'
    )


def remove_watcher(issue_key: str, account_id: str) -> None:
    """Remove a user as watcher."""
    from urllib.parse import quote
    path = f"/rest/api/3/issue/{issue_key}/watchers?accountId={quote(account_id)}"

    url = urljoin(get_base_url(), path)
    req = Request(url, method="DELETE")
    req.add_header("Authorization", get_auth_header())

    try:
        with urlopen(req, timeout=30) as response:
            pass  # 204 No Content on success
    except HTTPError as e:
        if e.code == 204:
            return  # Success
        error_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Failed to remove watcher: {e.code} {error_body}")


def format_output(result: dict, output_format: str) -> str:
    """Format the result for output."""
    if "action" in result:
        # Add/remove watcher result
        if output_format == "compact":
            action = "added" if result["action"] == "add" else "removed"
            return f"WATCHED|{result['issue']}|{action}|@{result['user']}"

        elif output_format == "json":
            return json.dumps({
                "issue": result["issue"],
                "action": result["action"],
                "user": result["user"],
            }, separators=(',', ':'))

        else:  # text
            action = "Added" if result["action"] == "add" else "Removed"
            return (
                f"Watcher {action}\n"
                f"Issue: {result['issue']}\n"
                f"User: {result['user']}"
            )

    else:
        # List watchers result
        watchers = result["watchers"]
        count = result["count"]

        if output_format == "compact":
            names = ",".join([f"@{w['displayName'].split()[0].lower()}" for w in watchers])
            return f"WATCHERS|{result['issue']}|{count}|{names}"

        elif output_format == "json":
            return json.dumps({
                "issue": result["issue"],
                "watchers": [w["displayName"] for w in watchers],
                "count": count,
                "isWatching": result["isWatching"],
            }, separators=(',', ':'))

        else:  # text
            lines = [f"Watchers for {result['issue']}:"]
            for w in watchers:
                lines.append(f"  - {w['displayName']}")
            lines.append(f"Total: {count} watcher{'s' if count != 1 else ''}")
            if result["isWatching"]:
                lines.append("(You are watching this issue)")
            return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Manage watchers on Jira issues"
    )
    parser.add_argument(
        "issue_key",
        help="Issue key (e.g., PROJ-123)"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Add yourself as a watcher"
    )
    parser.add_argument(
        "--unwatch", "-u",
        action="store_true",
        help="Remove yourself as a watcher"
    )
    parser.add_argument(
        "--add", "-a",
        metavar="USER",
        help="Add a user as watcher (by name)"
    )
    parser.add_argument(
        "--remove", "-r",
        metavar="USER",
        help="Remove a user as watcher (by name)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List current watchers"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()
    issue_key = args.issue_key.upper()

    # Extract project key for user lookups
    project_key = issue_key.split("-")[0]

    try:
        results = []

        # Watch (add self)
        if args.watch:
            current_user = get_current_user()
            add_watcher(issue_key, current_user["accountId"])
            results.append({
                "issue": issue_key,
                "action": "add",
                "user": current_user["displayName"],
            })

        # Unwatch (remove self)
        if args.unwatch:
            current_user = get_current_user()
            remove_watcher(issue_key, current_user["accountId"])
            results.append({
                "issue": issue_key,
                "action": "remove",
                "user": current_user["displayName"],
            })

        # Add another user
        if args.add:
            user = find_user_by_name(args.add, project_key)
            if not user:
                raise ValueError(f"User '{args.add}' not found")
            add_watcher(issue_key, user["accountId"])
            results.append({
                "issue": issue_key,
                "action": "add",
                "user": user["displayName"],
            })

        # Remove another user
        if args.remove:
            user = find_user_by_name(args.remove, project_key)
            if not user:
                raise ValueError(f"User '{args.remove}' not found")
            remove_watcher(issue_key, user["accountId"])
            results.append({
                "issue": issue_key,
                "action": "remove",
                "user": user["displayName"],
            })

        # List watchers
        if args.list or not results:
            result = get_watchers(issue_key)
            results.append(result)

        # Output results
        for result in results:
            print(format_output(result, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

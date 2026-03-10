#!/usr/bin/env python3
"""
Link Jira issues together.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python link_issues.py PROJ-123 PROJ-456 [--type "Blocks"] [--comment "Note"]
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

# Add shared module to path
SCRIPT_DIR = Path(__file__).parent
SHARED_DIR = SCRIPT_DIR.parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))

from markdown_to_adf import markdown_to_adf


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
    data: Optional[dict] = None
) -> Optional[dict]:
    """Make authenticated API request to Jira."""
    url = urljoin(get_base_url(), path)
    req = Request(url, method=method)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()

    try:
        with urlopen(req, timeout=30) as response:
            content = response.read().decode()
            return json.loads(content) if content else None
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 404:
            raise ValueError(f"Resource not found: {error_body}")
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


def get_link_types() -> list[dict]:
    """Fetch available issue link types."""
    result = api_request("/rest/api/3/issueLinkType")
    link_types = []
    for lt in result.get("issueLinkTypes", []):
        link_types.append({
            "id": lt["id"],
            "name": lt["name"],
            "inward": lt.get("inward", ""),
            "outward": lt.get("outward", ""),
        })
    return link_types


def find_link_type(name: str, link_types: list[dict]) -> Optional[dict]:
    """Find link type by name (case-insensitive, partial match)."""
    name_lower = name.lower()

    # Exact match first
    for lt in link_types:
        if lt["name"].lower() == name_lower:
            return lt

    # Partial match on name, inward, or outward
    for lt in link_types:
        if (name_lower in lt["name"].lower() or
            name_lower in lt["inward"].lower() or
            name_lower in lt["outward"].lower()):
            return lt

    return None


def create_issue_link(
    outward_issue: str,
    inward_issue: str,
    link_type_name: str,
    comment: Optional[str] = None
) -> dict:
    """Create a link between two issues."""
    link_types = get_link_types()
    link_type = find_link_type(link_type_name, link_types)

    if not link_type:
        available = ", ".join([lt["name"] for lt in link_types])
        raise ValueError(
            f"Link type '{link_type_name}' not found. Available: {available}"
        )

    payload: dict = {
        "type": {"name": link_type["name"]},
        "outwardIssue": {"key": outward_issue},
        "inwardIssue": {"key": inward_issue},
    }

    if comment:
        payload["comment"] = markdown_to_adf(comment)

    api_request("/rest/api/3/issueLink", method="POST", data=payload)

    return {
        "outward": outward_issue,
        "inward": inward_issue,
        "type": link_type["name"],
        "outward_desc": link_type["outward"],
        "inward_desc": link_type["inward"],
    }


def format_output(result: dict, output_format: str) -> str:
    """Format the result for output."""
    if output_format == "compact":
        return f"LINKED|{result['outward']}->{result['inward']}|{result['type']}"

    elif output_format == "json":
        return json.dumps({
            "outward": result["outward"],
            "inward": result["inward"],
            "type": result["type"],
        }, separators=(',', ':'))

    else:  # text
        return (
            f"Link Created\n"
            f"From: {result['outward']}\n"
            f"To: {result['inward']}\n"
            f"Type: {result['type']} ({result['outward_desc']} -> {result['inward_desc']})"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Link Jira issues together"
    )
    parser.add_argument(
        "outward_issue",
        nargs="?",
        help="The 'from' issue key (e.g., PROJ-123)"
    )
    parser.add_argument(
        "inward_issue",
        nargs="?",
        help="The 'to' issue key (e.g., PROJ-456)"
    )
    parser.add_argument(
        "--type", "-t",
        default="Relates",
        help="Link type name (default: Relates)"
    )
    parser.add_argument(
        "--comment", "-c",
        help="Comment to add to the outward issue"
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List available link types"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    try:
        if args.list_types:
            link_types = get_link_types()
            print("Available link types:")
            for lt in link_types:
                print(f"  {lt['name']}: {lt['outward']} / {lt['inward']}")
            return

        if not args.outward_issue or not args.inward_issue:
            parser.error("Both outward_issue and inward_issue are required")

        result = create_issue_link(
            args.outward_issue.upper(),
            args.inward_issue.upper(),
            args.type,
            args.comment
        )

        print(format_output(result, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

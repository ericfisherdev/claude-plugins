#!/usr/bin/env python3
"""
Create Jira issues with token-efficient output.

Uses shared cache for project metadata, issue types, users, etc.
to minimize API calls and provide quick lookups.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python create_jira_issue.py --project PROJ --type Bug --summary "Issue title"

Options:
    --project KEY       Project key (required)
    --type TYPE         Issue type name (required, e.g., Bug, Story, Task)
    --summary TEXT      Issue summary/title (required)
    --description TEXT  Issue description
    --priority NAME     Priority name (e.g., High, Medium, Low)
    --assignee NAME     Assignee display name (partial match supported)
    --labels L1,L2      Comma-separated labels
    --components C1,C2  Comma-separated component names
    --parent KEY        Parent issue key (for subtasks)
    --format FORMAT     Output: compact (default), text, json
    --list-types        List available issue types for project
    --list-users        List assignable users for project
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import base64

# Add shared module to path
SCRIPT_DIR = Path(__file__).parent
SHARED_DIR = SCRIPT_DIR.parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))

from jira_cache import JiraCache


def get_auth_header() -> str:
    """Generate Basic Auth header."""
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    if not email or not token:
        raise EnvironmentError(
            "JIRA_EMAIL and JIRA_API_TOKEN environment variables required"
        )
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def create_issue(
    project_key: str,
    issue_type_id: str,
    summary: str,
    description: Optional[str] = None,
    priority_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    labels: Optional[list[str]] = None,
    component_ids: Optional[list[str]] = None,
    parent_key: Optional[str] = None,
) -> dict:
    """Create a new Jira issue."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    # Build issue payload
    fields = {
        "project": {"key": project_key},
        "issuetype": {"id": issue_type_id},
        "summary": summary,
    }

    if description:
        # Convert to Atlassian Document Format
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}]
                }
            ]
        }

    if priority_id:
        fields["priority"] = {"id": priority_id}

    if assignee_id:
        fields["assignee"] = {"accountId": assignee_id}

    if labels:
        fields["labels"] = labels

    if component_ids:
        fields["components"] = [{"id": cid} for cid in component_ids]

    if parent_key:
        fields["parent"] = {"key": parent_key}

    payload = {"fields": fields}

    # Make API request
    url = urljoin(base_url, "/rest/api/3/issue")
    req = Request(url, method="POST")
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(payload).encode()

    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        try:
            error_json = json.loads(error_body)
            errors = error_json.get("errors", {})
            error_messages = error_json.get("errorMessages", [])
            details = "; ".join(error_messages + [f"{k}: {v}" for k, v in errors.items()])
            raise RuntimeError(f"Failed to create issue: {details}")
        except json.JSONDecodeError:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def fetch_created_issue(issue_key: str) -> dict:
    """Fetch the newly created issue details."""
    base_url = os.environ.get("JIRA_BASE_URL")
    url = urljoin(base_url, f"/rest/api/3/issue/{issue_key}?fields=summary,status,issuetype,priority,assignee,reporter,created")

    req = Request(url)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError):
        return {}


def format_output(issue_data: dict, created_response: dict, output_format: str) -> str:
    """Format the created issue output."""
    key = created_response.get("key", "Unknown")
    issue_id = created_response.get("id", "")
    self_url = created_response.get("self", "")

    # Extract fields from fetched issue
    fields = issue_data.get("fields", {})
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "Open")
    issue_type = fields.get("issuetype", {}).get("name", "")
    priority = fields.get("priority", {}).get("name", "") if fields.get("priority") else ""
    assignee = fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned"

    # Build browse URL
    base_url = os.environ.get("JIRA_BASE_URL", "")
    browse_url = f"{base_url}/browse/{key}" if base_url else ""

    if output_format == "compact":
        parts = [f"CREATED|{key}|{summary}|{status}"]
        if issue_type:
            parts[0] += f"|{issue_type}"
        if priority:
            parts[0] += f"|P:{priority}"
        if assignee != "Unassigned":
            parts[0] += f"|@{assignee}"
        if browse_url:
            parts.append(f"URL:{browse_url}")
        return "\n".join(parts)

    elif output_format == "json":
        return json.dumps({
            "key": key,
            "id": issue_id,
            "summary": summary,
            "status": status,
            "type": issue_type,
            "priority": priority,
            "assignee": assignee,
            "url": browse_url
        }, separators=(',', ':'))

    else:  # text
        lines = [
            f"Issue Created: {key}",
            f"Summary: {summary}",
            f"Status: {status}",
            f"Type: {issue_type}",
        ]
        if priority:
            lines.append(f"Priority: {priority}")
        lines.append(f"Assignee: {assignee}")
        if browse_url:
            lines.append(f"URL: {browse_url}")
        return "\n".join(lines)


def list_issue_types(cache: JiraCache, project_key: str) -> None:
    """List available issue types for a project."""
    issue_types = cache.get_issue_types(project_key)
    if not issue_types:
        print(f"No issue types found for project {project_key}", file=sys.stderr)
        sys.exit(1)

    print(f"Issue types for {project_key}:")
    for it in issue_types:
        subtask = " (subtask)" if it.get("subtask") else ""
        print(f"  - {it['name']}{subtask}")


def list_users(cache: JiraCache, project_key: str) -> None:
    """List assignable users for a project."""
    users = cache.get_users(project_key)
    if not users:
        print(f"No assignable users found for project {project_key}", file=sys.stderr)
        sys.exit(1)

    print(f"Assignable users for {project_key}:")
    for u in users:
        email = f" ({u['emailAddress']})" if u.get('emailAddress') else ""
        print(f"  - {u['displayName']}{email}")


def main():
    parser = argparse.ArgumentParser(
        description="Create Jira issues with token-efficient output"
    )
    parser.add_argument(
        "--project", "-p",
        help="Project key (required for creating issues)"
    )
    parser.add_argument(
        "--type", "-t",
        help="Issue type name (e.g., Bug, Story, Task)"
    )
    parser.add_argument(
        "--summary", "-s",
        help="Issue summary/title"
    )
    parser.add_argument(
        "--description", "-d",
        help="Issue description"
    )
    parser.add_argument(
        "--priority",
        help="Priority name (e.g., High, Medium, Low)"
    )
    parser.add_argument(
        "--assignee", "-a",
        help="Assignee display name (partial match)"
    )
    parser.add_argument(
        "--labels", "-l",
        help="Comma-separated labels"
    )
    parser.add_argument(
        "--components", "-c",
        help="Comma-separated component names"
    )
    parser.add_argument(
        "--parent",
        help="Parent issue key (for subtasks)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List available issue types for project"
    )
    parser.add_argument(
        "--list-users",
        action="store_true",
        help="List assignable users for project"
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Force refresh cached metadata"
    )

    args = parser.parse_args()

    try:
        cache = JiraCache()

        # Handle list commands
        if args.list_types:
            if not args.project:
                print("Error: --project required with --list-types", file=sys.stderr)
                sys.exit(1)
            list_issue_types(cache, args.project)
            return

        if args.list_users:
            if not args.project:
                print("Error: --project required with --list-users", file=sys.stderr)
                sys.exit(1)
            list_users(cache, args.project)
            return

        # Validate required arguments for creating
        if not args.project:
            print("Error: --project is required", file=sys.stderr)
            sys.exit(1)
        if not args.type:
            print("Error: --type is required", file=sys.stderr)
            sys.exit(1)
        if not args.summary:
            print("Error: --summary is required", file=sys.stderr)
            sys.exit(1)

        # Resolve issue type
        issue_type = cache.get_issue_type_by_name(args.project, args.type)
        if not issue_type:
            print(f"Error: Issue type '{args.type}' not found in project {args.project}", file=sys.stderr)
            print("Use --list-types to see available types", file=sys.stderr)
            sys.exit(1)

        # Resolve priority
        priority_id = None
        if args.priority:
            priority = cache.get_priority_by_name(args.priority)
            if not priority:
                print(f"Error: Priority '{args.priority}' not found", file=sys.stderr)
                sys.exit(1)
            priority_id = priority["id"]

        # Resolve assignee
        assignee_id = None
        if args.assignee:
            user = cache.get_user_by_name(args.project, args.assignee)
            if not user:
                print(f"Error: User '{args.assignee}' not found in project {args.project}", file=sys.stderr)
                print("Use --list-users to see available users", file=sys.stderr)
                sys.exit(1)
            assignee_id = user["accountId"]

        # Parse labels
        labels = None
        if args.labels:
            labels = [l.strip() for l in args.labels.split(",")]

        # Resolve components
        component_ids = None
        if args.components:
            component_names = [c.strip() for c in args.components.split(",")]
            components = cache.get_components(args.project)
            component_ids = []
            for name in component_names:
                name_lower = name.lower()
                found = None
                for c in components:
                    if c["name"].lower() == name_lower:
                        found = c
                        break
                if not found:
                    print(f"Error: Component '{name}' not found in project {args.project}", file=sys.stderr)
                    sys.exit(1)
                component_ids.append(found["id"])

        # Create the issue
        result = create_issue(
            project_key=args.project,
            issue_type_id=issue_type["id"],
            summary=args.summary,
            description=args.description,
            priority_id=priority_id,
            assignee_id=assignee_id,
            labels=labels,
            component_ids=component_ids,
            parent_key=args.parent,
        )

        # Fetch created issue details
        issue_data = fetch_created_issue(result["key"])

        # Output
        output = format_output(issue_data, result, args.format)
        print(output)

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

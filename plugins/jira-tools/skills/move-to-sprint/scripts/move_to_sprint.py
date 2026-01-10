#!/usr/bin/env python3
"""
Move issues to a sprint or backlog in Jira.

Supports:
- Moving single or multiple issues
- Moving to active sprint, specific sprint, or backlog
- Moving to next future sprint

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python move_to_sprint.py ISSUE [ISSUE...] [options]

Options:
    --sprint-id ID      Move to specific sprint
    --backlog           Move to backlog (remove from sprint)
    --next-sprint       Move to next future sprint
    --list-sprints      List available sprints
    --format FORMAT     Output: compact (default), json, text
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


def api_request(path: str, method: str = "GET", data: Optional[dict] = None) -> Optional[dict]:
    """Make authenticated API request to Jira."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    url = urljoin(base_url, path)
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
        if e.code == 204:
            return None  # Success with no content
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError("Access denied - check 'Schedule Issues' permission")
        elif e.code == 404:
            raise ValueError(f"Resource not found: {error_body}")
        else:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def get_project_from_issue(issue_key: str) -> str:
    """Extract project key from issue key."""
    return issue_key.split("-")[0]


def get_board_for_project(project_key: str) -> Optional[dict]:
    """Get the primary board for a project."""
    result = api_request(f"/rest/agile/1.0/board?projectKeyOrId={project_key}&maxResults=1")
    boards = result.get("values", []) if result else []
    if boards:
        return {
            "id": boards[0]["id"],
            "name": boards[0]["name"],
        }
    return None


def get_sprints(board_id: int, state: Optional[str] = None) -> list[dict]:
    """Get sprints for a board."""
    path = f"/rest/agile/1.0/board/{board_id}/sprint"
    if state:
        path += f"?state={state}"

    result = api_request(path)
    sprints = []
    for s in result.get("values", []) if result else []:
        sprints.append({
            "id": s["id"],
            "name": s["name"],
            "state": s.get("state", ""),
            "startDate": s.get("startDate", "")[:10] if s.get("startDate") else "",
            "endDate": s.get("endDate", "")[:10] if s.get("endDate") else "",
        })
    return sprints


def move_issues_to_sprint(sprint_id: int, issue_keys: list[str]) -> None:
    """Move issues to a sprint."""
    data = {"issues": issue_keys}
    api_request(f"/rest/agile/1.0/sprint/{sprint_id}/issue", method="POST", data=data)


def move_issues_to_backlog(board_id: int, issue_keys: list[str]) -> None:
    """Move issues to backlog (remove from sprint)."""
    data = {"issues": issue_keys}
    api_request(f"/rest/agile/1.0/backlog/issue", method="POST", data=data)


def get_issue_summaries(issue_keys: list[str]) -> dict[str, str]:
    """Get summaries for issues."""
    summaries = {}
    for key in issue_keys:
        try:
            result = api_request(f"/rest/api/3/issue/{key}?fields=summary")
            if result:
                summaries[key] = result.get("fields", {}).get("summary", "")
        except (ValueError, RuntimeError):
            summaries[key] = ""
    return summaries


def format_output(
    issue_keys: list[str],
    target: str,
    summaries: Optional[dict[str, str]],
    output_format: str
) -> str:
    """Format move result for output."""
    if output_format == "json":
        data = {
            "issues": issue_keys,
            "target": target,
        }
        if summaries:
            data["summaries"] = summaries
        return json.dumps(data, separators=(',', ':'))

    elif output_format == "text":
        lines = [f"Moved {len(issue_keys)} issue(s) to {target}:"]
        for key in issue_keys:
            summary = summaries.get(key, "") if summaries else ""
            if summary:
                lines.append(f"  {key}: {summary}")
            else:
                lines.append(f"  {key}")
        return "\n".join(lines)

    else:  # compact
        return f"MOVED|{','.join(issue_keys)}|{target}"


def format_sprint_list(sprints: list[dict], output_format: str) -> str:
    """Format sprint list for output."""
    if output_format == "json":
        return json.dumps(sprints, separators=(',', ':'))

    elif output_format == "text":
        lines = ["Available sprints:"]
        for s in sprints:
            state_icon = {"active": "*", "closed": "-", "future": "+"}
            icon = state_icon.get(s["state"], "?")
            lines.append(f"  [{icon}] {s['id']}: {s['name']} ({s['state']})")
        lines.append("")
        lines.append("Legend: * active, + future, - closed")
        return "\n".join(lines)

    else:  # compact
        lines = []
        for s in sprints:
            state_icon = {"active": "*", "closed": "-", "future": "+"}
            icon = state_icon.get(s["state"], "?")
            lines.append(f"{icon}|{s['id']}|{s['name']}|{s['state']}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Move issues to a sprint or backlog"
    )
    parser.add_argument(
        "issues",
        nargs="*",
        help="Issue keys to move (e.g., PROJ-123 PROJ-124)"
    )
    parser.add_argument(
        "--sprint-id",
        type=int,
        help="Target sprint ID"
    )
    parser.add_argument(
        "--backlog",
        action="store_true",
        help="Move to backlog (remove from sprint)"
    )
    parser.add_argument(
        "--next-sprint",
        action="store_true",
        help="Move to next future sprint"
    )
    parser.add_argument(
        "--list-sprints",
        action="store_true",
        help="List available sprints"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "json", "text"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    try:
        # Need at least one issue for most operations
        if not args.issues and not args.list_sprints:
            parser.error("At least one issue key required")

        # Get project from first issue
        if args.issues:
            project_key = get_project_from_issue(args.issues[0])
        else:
            # For list-sprints without issues, need to get project somehow
            parser.error("At least one issue key required to determine project")

        # Get board
        board = get_board_for_project(project_key)
        if not board:
            print(f"Error: No board found for project {project_key}", file=sys.stderr)
            sys.exit(1)

        # List sprints mode
        if args.list_sprints:
            sprints = get_sprints(board["id"])
            if not sprints:
                print(f"No sprints found for project {project_key}", file=sys.stderr)
                sys.exit(0)
            print(format_sprint_list(sprints, args.format))
            return

        # Validate options
        options_count = sum([
            args.sprint_id is not None,
            args.backlog,
            args.next_sprint
        ])

        if options_count > 1:
            parser.error("Only one of --sprint-id, --backlog, --next-sprint can be specified")

        # Determine target sprint
        target_name = ""
        sprint_id = None

        if args.backlog:
            target_name = "Backlog"
        elif args.sprint_id:
            sprint_id = args.sprint_id
            sprints = get_sprints(board["id"])
            sprint = next((s for s in sprints if s["id"] == sprint_id), None)
            if sprint:
                target_name = sprint["name"]
            else:
                target_name = f"Sprint {sprint_id}"
        elif args.next_sprint:
            sprints = get_sprints(board["id"], "future")
            if not sprints:
                print("Error: No future sprints available", file=sys.stderr)
                sys.exit(1)
            sprint_id = sprints[0]["id"]
            target_name = sprints[0]["name"]
        else:
            # Default: active sprint
            sprints = get_sprints(board["id"], "active")
            if not sprints:
                print("Error: No active sprint. Use --sprint-id or --next-sprint", file=sys.stderr)
                sys.exit(1)
            sprint_id = sprints[0]["id"]
            target_name = sprints[0]["name"]

        # Move issues
        if args.backlog:
            move_issues_to_backlog(board["id"], args.issues)
        else:
            move_issues_to_sprint(sprint_id, args.issues)

        # Get summaries for text output
        summaries = None
        if args.format == "text":
            summaries = get_issue_summaries(args.issues)

        # Output result
        print(format_output(args.issues, target_name, summaries, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch sprint information from Jira with token-efficient output.

Retrieves sprint details including:
- Sprint name, state, dates
- Progress (issues done vs total)
- Story points (if available)
- Issue list (optional)

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python sprint_info.py PROJECT [options]

Options:
    --sprint-id ID      Get specific sprint (default: active sprint)
    --list-sprints      List all sprints for project
    --include-issues    Include issue list in output
    --state STATE       Filter: active, closed, future
    --format FORMAT     Output: compact (default), json, text
    --refresh           Force refresh from API
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, quote
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


def api_request(path: str, method: str = "GET", data: Optional[dict] = None) -> dict:
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
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError("Access denied")
        elif e.code == 404:
            raise ValueError(f"Resource not found: {error_body}")
        else:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def get_board_for_project(project_key: str, cache: Optional["JiraCache"] = None) -> Optional[dict]:
    """Get the primary board for a project."""
    if cache:
        board = cache.get_board_for_project(project_key)
        if board:
            return board

    result = api_request(f"/rest/agile/1.0/board?projectKeyOrId={project_key}&maxResults=1")
    boards = result.get("values", [])
    if boards:
        return {
            "id": boards[0]["id"],
            "name": boards[0]["name"],
            "type": boards[0].get("type", ""),
        }
    return None


def get_sprints(board_id: int, state: Optional[str] = None) -> list[dict]:
    """Get sprints for a board."""
    path = f"/rest/agile/1.0/board/{board_id}/sprint"
    if state:
        path += f"?state={state}"

    result = api_request(path)
    sprints = []
    for s in result.get("values", []):
        sprints.append({
            "id": s["id"],
            "name": s["name"],
            "state": s.get("state", ""),
            "startDate": s.get("startDate", ""),
            "endDate": s.get("endDate", ""),
            "completeDate": s.get("completeDate", ""),
            "goal": s.get("goal", ""),
        })
    return sprints


def get_sprint_issues(sprint_id: int, max_results: int = 100) -> list[dict]:
    """Get issues in a sprint."""
    path = f"/rest/agile/1.0/sprint/{sprint_id}/issue?maxResults={max_results}&fields=summary,status,issuetype,customfield_10016"

    result = api_request(path)
    issues = []
    for issue in result.get("issues", []):
        fields = issue.get("fields", {})
        status = fields.get("status", {})
        issue_type = fields.get("issuetype", {})

        issues.append({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": status.get("name", "Unknown"),
            "statusCategory": status.get("statusCategory", {}).get("key", ""),
            "type": issue_type.get("name", ""),
            "storyPoints": fields.get("customfield_10016"),  # Common story points field
        })
    return issues


def calculate_progress(issues: list[dict]) -> dict:
    """Calculate sprint progress from issues."""
    total = len(issues)
    done = sum(1 for i in issues if i.get("statusCategory") == "done")
    in_progress = sum(1 for i in issues if i.get("statusCategory") == "indeterminate")
    todo = total - done - in_progress

    # Story points (if available)
    total_points = sum(i.get("storyPoints") or 0 for i in issues)
    done_points = sum(i.get("storyPoints") or 0 for i in issues if i.get("statusCategory") == "done")
    remaining_points = total_points - done_points

    return {
        "total": total,
        "done": done,
        "inProgress": in_progress,
        "todo": todo,
        "percentDone": round((done / total * 100) if total > 0 else 0),
        "totalPoints": total_points,
        "donePoints": done_points,
        "remainingPoints": remaining_points,
    }


def format_date(date_str: str) -> str:
    """Format ISO date string to YYYY-MM-DD."""
    if not date_str:
        return "-"
    return date_str[:10]


def format_output(sprint: dict, progress: Optional[dict], issues: Optional[list[dict]], output_format: str) -> str:
    """Format sprint info for output."""
    if output_format == "json":
        data = {"sprint": sprint}
        if progress:
            data["progress"] = progress
        if issues:
            data["issues"] = issues
        return json.dumps(data, separators=(',', ':'))

    elif output_format == "text":
        lines = [
            f"Sprint: {sprint['name']}",
            f"State: {sprint['state']}",
            f"Start: {format_date(sprint['startDate'])}",
            f"End: {format_date(sprint['endDate'])}",
        ]
        if sprint.get("goal"):
            lines.append(f"Goal: {sprint['goal']}")

        if progress:
            lines.append("")
            lines.append(f"Progress: {progress['done']}/{progress['total']} issues done ({progress['percentDone']}%)")
            lines.append(f"  In Progress: {progress['inProgress']}")
            lines.append(f"  To Do: {progress['todo']}")
            if progress['totalPoints'] > 0:
                lines.append(f"Story Points: {progress['donePoints']}/{progress['totalPoints']} ({progress['remainingPoints']} remaining)")

        if issues:
            lines.append("")
            lines.append("Issues:")
            for i in issues:
                points_str = f" ({i['storyPoints']}pts)" if i.get('storyPoints') else ""
                lines.append(f"  {i['key']}: [{i['status']}] {i['summary']}{points_str}")

        return "\n".join(lines)

    else:  # compact
        lines = [
            f"SPRINT|{sprint['name']}|{sprint['state']}|{format_date(sprint['startDate'])}|{format_date(sprint['endDate'])}"
        ]

        if progress:
            points_str = f"|{progress['remainingPoints']}pts remaining" if progress['totalPoints'] > 0 else ""
            lines.append(f"PROGRESS|{progress['done']}/{progress['total']} done|{progress['percentDone']}%{points_str}")

        if issues:
            lines.append("ISSUES:")
            for i in issues:
                lines.append(f"{i['key']}|{i['status']}|{i['summary']}")

        return "\n".join(lines)


def format_sprint_list(sprints: list[dict], output_format: str) -> str:
    """Format sprint list for output."""
    if output_format == "json":
        return json.dumps(sprints, separators=(',', ':'))

    elif output_format == "text":
        lines = ["Sprints:"]
        for s in sprints:
            state_icon = {"active": "*", "closed": "-", "future": "+"}
            icon = state_icon.get(s["state"], "?")
            lines.append(f"  [{icon}] {s['id']}: {s['name']} ({s['state']})")
            lines.append(f"      {format_date(s['startDate'])} - {format_date(s['endDate'])}")
        lines.append("")
        lines.append("Legend: * active, + future, - closed")
        return "\n".join(lines)

    else:  # compact
        lines = []
        for s in sprints:
            state_icon = {"active": "*", "closed": "-", "future": "+"}
            icon = state_icon.get(s["state"], "?")
            lines.append(f"{icon}|{s['id']}|{s['name']}|{s['state']}|{format_date(s['startDate'])}|{format_date(s['endDate'])}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch sprint information from Jira"
    )
    parser.add_argument(
        "project",
        help="Jira project key (e.g., PROJ)"
    )
    parser.add_argument(
        "--sprint-id",
        type=int,
        help="Get specific sprint by ID (default: active sprint)"
    )
    parser.add_argument(
        "--list-sprints",
        action="store_true",
        help="List all sprints for project"
    )
    parser.add_argument(
        "--include-issues",
        action="store_true",
        help="Include issue list in output"
    )
    parser.add_argument(
        "--state",
        choices=["active", "closed", "future"],
        help="Filter sprints by state"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "json", "text"],
        default="compact",
        help="Output format (default: compact)"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh from API"
    )

    args = parser.parse_args()

    try:
        # Initialize cache if available
        cache = JiraCache() if CACHE_AVAILABLE and not args.refresh else None

        # Get board for project
        board = get_board_for_project(args.project, cache)
        if not board:
            print(f"Error: No board found for project {args.project}", file=sys.stderr)
            sys.exit(1)

        # List sprints mode
        if args.list_sprints:
            sprints = get_sprints(board["id"], args.state)
            if not sprints:
                print(f"No sprints found for project {args.project}", file=sys.stderr)
                sys.exit(0)
            print(format_sprint_list(sprints, args.format))
            return

        # Get specific sprint or active sprint
        if args.sprint_id:
            sprints = get_sprints(board["id"])
            sprint = next((s for s in sprints if s["id"] == args.sprint_id), None)
            if not sprint:
                print(f"Error: Sprint {args.sprint_id} not found", file=sys.stderr)
                sys.exit(1)
        else:
            # Default to active sprint
            sprints = get_sprints(board["id"], "active")
            if not sprints:
                print(f"No active sprint for project {args.project}", file=sys.stderr)
                sys.exit(1)
            sprint = sprints[0]

        # Get issues and calculate progress
        issues = get_sprint_issues(sprint["id"])
        progress = calculate_progress(issues)

        # Output
        output_issues = issues if args.include_issues else None
        print(format_output(sprint, progress, output_issues, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

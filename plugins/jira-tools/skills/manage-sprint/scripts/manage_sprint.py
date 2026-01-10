#!/usr/bin/env python3
"""
Create, start, complete, and update sprints in Jira.

Supports:
- Creating new sprints
- Starting sprints (future -> active)
- Completing sprints (active -> closed)
- Updating sprint details (name, dates, goal)

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python manage_sprint.py PROJECT [options]

Actions:
    --create NAME       Create new sprint
    --start             Start a sprint (future -> active)
    --complete          Complete a sprint (active -> closed)
    --update            Update sprint details

Options:
    --sprint-id ID      Target specific sprint
    --next              Use next future sprint (for --start)
    --start-date DATE   Start date (YYYY-MM-DD)
    --end-date DATE     End date (YYYY-MM-DD)
    --duration DAYS     Duration in days (default: 14)
    --goal TEXT         Sprint goal
    --name NAME         New name (for --update)
    --format FORMAT     Output: compact (default), json, text
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
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
            return None
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError("Access denied - check 'Manage Sprints' permission")
        elif e.code == 404:
            raise ValueError(f"Resource not found: {error_body}")
        else:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def get_board_for_project(project_key: str) -> Optional[dict]:
    """Get the primary board for a project."""
    result = api_request(f"/rest/agile/1.0/board?projectKeyOrId={project_key}&maxResults=1")
    boards = result.get("values", []) if result else []
    if boards:
        return {"id": boards[0]["id"], "name": boards[0]["name"]}
    return None


def get_sprints(board_id: int, state: Optional[str] = None) -> list[dict]:
    """Get sprints for a board."""
    path = f"/rest/agile/1.0/board/{board_id}/sprint?maxResults=50"
    if state:
        path += f"&state={state}"

    result = api_request(path)
    sprints = []
    for s in result.get("values", []) if result else []:
        sprints.append({
            "id": s["id"],
            "name": s["name"],
            "state": s.get("state", ""),
            "startDate": s.get("startDate", ""),
            "endDate": s.get("endDate", ""),
            "goal": s.get("goal", ""),
        })
    return sprints


def create_sprint(
    board_id: int,
    name: str,
    start_date: str,
    end_date: str,
    goal: Optional[str] = None
) -> dict:
    """Create a new sprint."""
    data = {
        "name": name,
        "originBoardId": board_id,
        "startDate": f"{start_date}T09:00:00.000Z",
        "endDate": f"{end_date}T17:00:00.000Z",
    }
    if goal:
        data["goal"] = goal

    result = api_request("/rest/agile/1.0/sprint", method="POST", data=data)
    return result


def update_sprint(sprint_id: int, updates: dict) -> dict:
    """Update sprint details including state."""
    # Format dates if provided
    if "startDate" in updates and updates["startDate"]:
        if "T" not in updates["startDate"]:
            updates["startDate"] = f"{updates['startDate']}T09:00:00.000Z"
    if "endDate" in updates and updates["endDate"]:
        if "T" not in updates["endDate"]:
            updates["endDate"] = f"{updates['endDate']}T17:00:00.000Z"

    result = api_request(f"/rest/agile/1.0/sprint/{sprint_id}", method="POST", data=updates)
    return result


def start_sprint(sprint_id: int) -> dict:
    """Start a sprint (future -> active)."""
    return update_sprint(sprint_id, {"state": "active"})


def complete_sprint(sprint_id: int) -> dict:
    """Complete a sprint (active -> closed)."""
    return update_sprint(sprint_id, {"state": "closed"})


def format_date(date_str: str) -> str:
    """Format ISO date string to YYYY-MM-DD."""
    if not date_str:
        return "-"
    return date_str[:10]


def format_output(action: str, sprint: dict, output_format: str) -> str:
    """Format result for output."""
    if output_format == "json":
        return json.dumps({"action": action, "sprint": sprint}, separators=(',', ':'))

    elif output_format == "text":
        action_text = {
            "created": "Sprint Created",
            "started": "Sprint Started",
            "completed": "Sprint Completed",
            "updated": "Sprint Updated",
        }
        lines = [
            f"{action_text.get(action, action)}",
            f"  ID: {sprint.get('id', '-')}",
            f"  Name: {sprint.get('name', '-')}",
            f"  State: {sprint.get('state', '-')}",
            f"  Start: {format_date(sprint.get('startDate', ''))}",
            f"  End: {format_date(sprint.get('endDate', ''))}",
        ]
        if sprint.get('goal'):
            lines.append(f"  Goal: {sprint['goal']}")
        return "\n".join(lines)

    else:  # compact
        return f"{action.upper()}|{sprint.get('id', '-')}|{sprint.get('name', '-')}|{sprint.get('state', '-')}|{format_date(sprint.get('startDate', ''))}|{format_date(sprint.get('endDate', ''))}"


def main():
    parser = argparse.ArgumentParser(
        description="Create, start, complete, and update sprints"
    )
    parser.add_argument(
        "project",
        help="Jira project key (e.g., PROJ)"
    )

    # Actions (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--create",
        metavar="NAME",
        help="Create new sprint with given name"
    )
    action_group.add_argument(
        "--start",
        action="store_true",
        help="Start a sprint (future -> active)"
    )
    action_group.add_argument(
        "--complete",
        action="store_true",
        help="Complete a sprint (active -> closed)"
    )
    action_group.add_argument(
        "--update",
        action="store_true",
        help="Update sprint details"
    )
    action_group.add_argument(
        "--list",
        action="store_true",
        help="List all sprints"
    )

    # Sprint selection
    parser.add_argument(
        "--sprint-id",
        type=int,
        help="Target specific sprint by ID"
    )
    parser.add_argument(
        "--next",
        action="store_true",
        help="Use next future sprint (for --start)"
    )

    # Create/update options
    parser.add_argument(
        "--start-date",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=14,
        help="Duration in days (default: 14)"
    )
    parser.add_argument(
        "--goal",
        help="Sprint goal"
    )
    parser.add_argument(
        "--name",
        help="New sprint name (for --update)"
    )

    # Output
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "json", "text"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    try:
        # Get board
        board = get_board_for_project(args.project)
        if not board:
            print(f"Error: No board found for project {args.project}", file=sys.stderr)
            sys.exit(1)

        # List sprints
        if args.list:
            sprints = get_sprints(board["id"])
            for s in sprints:
                state_icon = {"active": "*", "closed": "-", "future": "+"}
                icon = state_icon.get(s["state"], "?")
                print(f"{icon}|{s['id']}|{s['name']}|{s['state']}|{format_date(s['startDate'])}|{format_date(s['endDate'])}")
            return

        # Create sprint
        if args.create:
            # Calculate dates
            if args.start_date:
                start_date = args.start_date
            else:
                start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            if args.end_date:
                end_date = args.end_date
            else:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_date = (start_dt + timedelta(days=args.duration)).strftime("%Y-%m-%d")

            result = create_sprint(board["id"], args.create, start_date, end_date, args.goal)
            print(format_output("created", result, args.format))
            return

        # Start sprint
        if args.start:
            if args.sprint_id:
                sprint_id = args.sprint_id
                sprints = get_sprints(board["id"])
                sprint = next((s for s in sprints if s["id"] == sprint_id), None)
            elif args.next:
                sprints = get_sprints(board["id"], "future")
                if not sprints:
                    print("Error: No future sprints to start", file=sys.stderr)
                    sys.exit(1)
                sprint = sprints[0]
                sprint_id = sprint["id"]
            else:
                sprints = get_sprints(board["id"], "future")
                if not sprints:
                    print("Error: No future sprints to start", file=sys.stderr)
                    sys.exit(1)
                sprint = sprints[0]
                sprint_id = sprint["id"]

            if not sprint:
                print(f"Error: Sprint {sprint_id} not found", file=sys.stderr)
                sys.exit(1)

            if sprint["state"] != "future":
                print(f"Error: Sprint is already {sprint['state']}, cannot start", file=sys.stderr)
                sys.exit(1)

            result = start_sprint(sprint_id)
            if result:
                print(format_output("started", result, args.format))
            else:
                sprint["state"] = "active"
                print(format_output("started", sprint, args.format))
            return

        # Complete sprint
        if args.complete:
            if args.sprint_id:
                sprint_id = args.sprint_id
                sprints = get_sprints(board["id"])
                sprint = next((s for s in sprints if s["id"] == sprint_id), None)
            else:
                sprints = get_sprints(board["id"], "active")
                if not sprints:
                    print("Error: No active sprint to complete", file=sys.stderr)
                    sys.exit(1)
                sprint = sprints[0]
                sprint_id = sprint["id"]

            if not sprint:
                print(f"Error: Sprint {sprint_id} not found", file=sys.stderr)
                sys.exit(1)

            if sprint["state"] != "active":
                print(f"Error: Sprint is {sprint['state']}, not active", file=sys.stderr)
                sys.exit(1)

            result = complete_sprint(sprint_id)
            if result:
                print(format_output("completed", result, args.format))
            else:
                sprint["state"] = "closed"
                print(format_output("completed", sprint, args.format))
            return

        # Update sprint
        if args.update:
            if not args.sprint_id:
                print("Error: --sprint-id required for --update", file=sys.stderr)
                sys.exit(1)

            updates = {}
            if args.name:
                updates["name"] = args.name
            if args.start_date:
                updates["startDate"] = args.start_date
            if args.end_date:
                updates["endDate"] = args.end_date
            if args.goal:
                updates["goal"] = args.goal

            if not updates:
                print("Error: No updates specified (--name, --start-date, --end-date, --goal)", file=sys.stderr)
                sys.exit(1)

            result = update_sprint(args.sprint_id, updates)
            if result:
                print(format_output("updated", result, args.format))
            else:
                # Fetch updated sprint
                sprints = get_sprints(board["id"])
                sprint = next((s for s in sprints if s["id"] == args.sprint_id), {"id": args.sprint_id})
                print(format_output("updated", sprint, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

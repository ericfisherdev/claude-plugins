#!/usr/bin/env python3
"""
Generate sprint reports with progress metrics and velocity data.

Provides:
- Progress summary (issues and story points)
- Issue breakdown by status and type
- Velocity comparison with past sprints

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python sprint_report.py PROJECT [options]

Options:
    --sprint-id ID      Report for specific sprint (default: active)
    --detailed          Include issue-by-issue breakdown
    --velocity          Include velocity comparison
    --format FORMAT     Output: compact (default), json, text
"""

import argparse
import json
import os
import sys
from collections import defaultdict
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


def api_request(path: str) -> dict:
    """Make authenticated API request to Jira."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    url = urljoin(base_url, path)
    req = Request(url)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

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


def get_board_for_project(project_key: str) -> Optional[dict]:
    """Get the primary board for a project."""
    result = api_request(f"/rest/agile/1.0/board?projectKeyOrId={project_key}&maxResults=1")
    boards = result.get("values", [])
    if boards:
        return {"id": boards[0]["id"], "name": boards[0]["name"]}
    return None


def get_sprints(board_id: int, state: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Get sprints for a board."""
    path = f"/rest/agile/1.0/board/{board_id}/sprint?maxResults={limit}"
    if state:
        path += f"&state={state}"

    result = api_request(path)
    sprints = []
    for s in result.get("values", []):
        sprints.append({
            "id": s["id"],
            "name": s["name"],
            "state": s.get("state", ""),
            "startDate": s.get("startDate", ""),
            "endDate": s.get("endDate", ""),
            "goal": s.get("goal", ""),
        })
    return sprints


def get_sprint_issues(sprint_id: int) -> list[dict]:
    """Get all issues in a sprint."""
    path = f"/rest/agile/1.0/sprint/{sprint_id}/issue?maxResults=200&fields=summary,status,issuetype,customfield_10016,assignee"

    result = api_request(path)
    issues = []
    for issue in result.get("issues", []):
        fields = issue.get("fields", {})
        status = fields.get("status", {})
        issue_type = fields.get("issuetype", {})
        assignee = fields.get("assignee", {})

        issues.append({
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": status.get("name", "Unknown"),
            "statusCategory": status.get("statusCategory", {}).get("key", ""),
            "type": issue_type.get("name", ""),
            "storyPoints": fields.get("customfield_10016"),
            "assignee": assignee.get("displayName", "") if assignee else "",
        })
    return issues


def calculate_metrics(issues: list[dict]) -> dict:
    """Calculate sprint metrics from issues."""
    total = len(issues)
    done = sum(1 for i in issues if i.get("statusCategory") == "done")
    in_progress = sum(1 for i in issues if i.get("statusCategory") == "indeterminate")
    todo = total - done - in_progress

    # Story points
    total_points = sum(i.get("storyPoints") or 0 for i in issues)
    done_points = sum(i.get("storyPoints") or 0 for i in issues if i.get("statusCategory") == "done")

    # By type
    by_type = defaultdict(int)
    for i in issues:
        by_type[i.get("type", "Unknown")] += 1

    # By status
    by_status = defaultdict(int)
    for i in issues:
        by_status[i.get("status", "Unknown")] += 1

    return {
        "total": total,
        "done": done,
        "inProgress": in_progress,
        "todo": todo,
        "percentDone": round((done / total * 100) if total > 0 else 0),
        "totalPoints": total_points,
        "donePoints": done_points,
        "remainingPoints": total_points - done_points,
        "byType": dict(by_type),
        "byStatus": dict(by_status),
    }


def calculate_velocity(board_id: int, current_sprint_points: int) -> dict:
    """Calculate velocity metrics from past sprints."""
    closed_sprints = get_sprints(board_id, "closed", limit=5)

    past_velocities = []
    for sprint in closed_sprints[:3]:  # Last 3 closed sprints
        issues = get_sprint_issues(sprint["id"])
        done_points = sum(
            i.get("storyPoints") or 0
            for i in issues
            if i.get("statusCategory") == "done"
        )
        past_velocities.append({
            "name": sprint["name"],
            "points": done_points,
        })

    avg_velocity = round(sum(v["points"] for v in past_velocities) / len(past_velocities)) if past_velocities else 0

    # Trend calculation
    trend = "stable"
    if len(past_velocities) >= 2:
        recent = past_velocities[0]["points"]
        older = past_velocities[-1]["points"]
        if recent > older * 1.1:
            trend = "up"
        elif recent < older * 0.9:
            trend = "down"

    return {
        "current": current_sprint_points,
        "average": avg_velocity,
        "trend": trend,
        "history": past_velocities,
    }


def format_date(date_str: str) -> str:
    """Format ISO date string to YYYY-MM-DD."""
    if not date_str:
        return "-"
    return date_str[:10]


def format_compact(sprint: dict, metrics: dict, velocity: Optional[dict], detailed: bool, issues: list[dict]) -> str:
    """Format report in compact format."""
    lines = [
        f"SPRINT|{sprint['name']}|{sprint['state']}|{format_date(sprint['startDate'])}|{format_date(sprint['endDate'])}|{metrics['percentDone']}%",
        f"ISSUES|{metrics['done']}/{metrics['total']} done|{metrics['inProgress']} in-progress|{metrics['todo']} todo",
    ]

    if metrics['totalPoints'] > 0:
        lines.append(f"POINTS|{metrics['donePoints']}/{metrics['totalPoints']}|{metrics['remainingPoints']} remaining")

    if velocity:
        trend_symbol = {"up": "^", "down": "v", "stable": "-"}
        lines.append(f"VELOCITY|{velocity['current']}|avg:{velocity['average']}|trend:{trend_symbol.get(velocity['trend'], '?')}")

    if detailed:
        lines.append("BY_STATUS|" + "|".join(f"{k}:{v}" for k, v in metrics['byStatus'].items()))
        lines.append("BY_TYPE|" + "|".join(f"{k}:{v}" for k, v in metrics['byType'].items()))

        # List issues not done
        not_done = [i for i in issues if i.get("statusCategory") != "done"]
        if not_done:
            lines.append("REMAINING:")
            for i in not_done[:10]:  # Limit to 10
                assignee = f"@{i['assignee']}" if i.get('assignee') else "unassigned"
                points = f"({i['storyPoints']}pts)" if i.get('storyPoints') else ""
                lines.append(f"  {i['key']}|{i['status']}|{assignee}|{i['summary'][:50]}{points}")

    return "\n".join(lines)


def format_text(sprint: dict, metrics: dict, velocity: Optional[dict], detailed: bool, issues: list[dict]) -> str:
    """Format report in text format."""
    lines = [
        f"Sprint Report: {sprint['name']}",
        "=" * (16 + len(sprint['name'])),
        f"Status: {sprint['state']}",
        f"Period: {format_date(sprint['startDate'])} to {format_date(sprint['endDate'])}",
    ]

    if sprint.get('goal'):
        lines.append(f"Goal: {sprint['goal']}")

    lines.extend([
        "",
        "Progress",
        "--------",
        f"Issues: {metrics['done']}/{metrics['total']} done ({metrics['percentDone']}%)",
        f"  - In Progress: {metrics['inProgress']}",
        f"  - To Do: {metrics['todo']}",
    ])

    if metrics['totalPoints'] > 0:
        lines.extend([
            "",
            f"Story Points: {metrics['donePoints']}/{metrics['totalPoints']} completed",
            f"  - Remaining: {metrics['remainingPoints']} points",
        ])

    if velocity:
        trend_text = {"up": "Improving", "down": "Declining", "stable": "Stable"}
        lines.extend([
            "",
            "Velocity",
            "--------",
            f"Current Sprint: {velocity['current']} points",
            f"Average (last 3): {velocity['average']} points",
            f"Trend: {trend_text.get(velocity['trend'], 'Unknown')}",
        ])

    if detailed:
        lines.extend([
            "",
            "By Status",
            "---------",
        ])
        for status, count in sorted(metrics['byStatus'].items()):
            lines.append(f"  {status}: {count}")

        lines.extend([
            "",
            "By Type",
            "-------",
        ])
        for issue_type, count in sorted(metrics['byType'].items()):
            lines.append(f"  {issue_type}: {count}")

        not_done = [i for i in issues if i.get("statusCategory") != "done"]
        if not_done:
            lines.extend([
                "",
                "Remaining Issues",
                "----------------",
            ])
            for i in not_done[:10]:
                assignee = i.get('assignee') or "unassigned"
                points = f" ({i['storyPoints']}pts)" if i.get('storyPoints') else ""
                lines.append(f"  {i['key']}: [{i['status']}] {i['summary'][:40]}... - {assignee}{points}")

    return "\n".join(lines)


def format_json(sprint: dict, metrics: dict, velocity: Optional[dict], detailed: bool, issues: list[dict]) -> str:
    """Format report in JSON format."""
    data = {
        "sprint": sprint,
        "metrics": metrics,
    }

    if velocity:
        data["velocity"] = velocity

    if detailed:
        data["issues"] = issues

    return json.dumps(data, separators=(',', ':'))


def main():
    parser = argparse.ArgumentParser(
        description="Generate sprint reports with progress metrics"
    )
    parser.add_argument(
        "project",
        help="Jira project key (e.g., PROJ)"
    )
    parser.add_argument(
        "--sprint-id",
        type=int,
        help="Report for specific sprint (default: active)"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Include issue-by-issue breakdown"
    )
    parser.add_argument(
        "--velocity",
        action="store_true",
        help="Include velocity comparison"
    )
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

        # Get sprint
        if args.sprint_id:
            sprints = get_sprints(board["id"])
            sprint = next((s for s in sprints if s["id"] == args.sprint_id), None)
            if not sprint:
                print(f"Error: Sprint {args.sprint_id} not found", file=sys.stderr)
                sys.exit(1)
        else:
            sprints = get_sprints(board["id"], "active")
            if not sprints:
                print(f"No active sprint for project {args.project}", file=sys.stderr)
                sys.exit(1)
            sprint = sprints[0]

        # Get issues and calculate metrics
        issues = get_sprint_issues(sprint["id"])
        metrics = calculate_metrics(issues)

        # Calculate velocity if requested
        velocity = None
        if args.velocity:
            velocity = calculate_velocity(board["id"], metrics['totalPoints'])

        # Format output
        if args.format == "json":
            output = format_json(sprint, metrics, velocity, args.detailed, issues)
        elif args.format == "text":
            output = format_text(sprint, metrics, velocity, args.detailed, issues)
        else:
            output = format_compact(sprint, metrics, velocity, args.detailed, issues)

        print(output)

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

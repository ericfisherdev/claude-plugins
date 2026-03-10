#!/usr/bin/env python3
"""
Update Jira issues with token-efficient output.

Uses shared cache for project metadata, users, priorities, etc.
Supports field updates, status transitions, and adding comments.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python update_jira_issue.py PROJ-123 [options]

Options:
    --summary TEXT        Update issue summary/title
    --description TEXT    Update issue description
    --status STATUS       Transition to new status
    --priority NAME       Update priority
    --assignee NAME       Update assignee (partial match)
    --labels L1,L2        Set labels (replaces existing)
    --add-labels L1,L2    Add labels to existing
    --remove-labels L1,L2 Remove labels from existing
    --components C1,C2    Set components (replaces existing)
    --comment TEXT        Add a comment to the issue
    --format FORMAT       Output: compact (default), text, json
    --list-transitions    List available status transitions
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
from markdown_to_adf import markdown_to_adf


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


def api_request(path: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    """Make authenticated API request to Jira."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    url = urljoin(base_url, path)
    req = Request(url, method=method)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()

    try:
        with urlopen(req, timeout=30) as response:
            content = response.read().decode()
            return json.loads(content) if content else {}
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        try:
            error_json = json.loads(error_body)
            errors = error_json.get("errors", {})
            error_messages = error_json.get("errorMessages", [])
            details = "; ".join(error_messages + [f"{k}: {v}" for k, v in errors.items()])
            raise RuntimeError(f"Jira API error: {details}")
        except json.JSONDecodeError:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def get_issue(issue_key: str) -> dict:
    """Fetch issue details."""
    return api_request(
        f"/rest/api/3/issue/{issue_key}?fields=summary,status,issuetype,priority,assignee,labels,components,project"
    )


def get_transitions(issue_key: str) -> list[dict]:
    """Get available transitions for an issue."""
    result = api_request(f"/rest/api/3/issue/{issue_key}/transitions")
    transitions = []
    for t in result.get("transitions", []):
        transitions.append({
            "id": t["id"],
            "name": t["name"],
            "to_status": t.get("to", {}).get("name", ""),
        })
    return transitions


def update_issue_fields(issue_key: str, fields: dict) -> None:
    """Update issue fields."""
    if not fields:
        return
    api_request(f"/rest/api/3/issue/{issue_key}", method="PUT", data={"fields": fields})


def transition_issue(issue_key: str, transition_id: str) -> None:
    """Transition issue to new status."""
    api_request(
        f"/rest/api/3/issue/{issue_key}/transitions",
        method="POST",
        data={"transition": {"id": transition_id}}
    )


def add_comment(issue_key: str, comment_text: str) -> dict:
    """Add a comment to an issue."""
    body = {"body": markdown_to_adf(comment_text)}
    return api_request(f"/rest/api/3/issue/{issue_key}/comment", method="POST", data=body)


def format_output(issue_key: str, issue_data: dict, changes: list[str], output_format: str) -> str:
    """Format the updated issue output."""
    fields = issue_data.get("fields", {})
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "")
    issue_type = fields.get("issuetype", {}).get("name", "")
    priority = fields.get("priority", {}).get("name", "") if fields.get("priority") else ""
    assignee = fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned"
    labels = fields.get("labels", [])

    base_url = os.environ.get("JIRA_BASE_URL", "")
    browse_url = f"{base_url}/browse/{issue_key}" if base_url else ""

    if output_format == "compact":
        parts = [f"UPDATED|{issue_key}|{summary}|{status}"]
        if issue_type:
            parts[0] += f"|{issue_type}"
        if priority:
            parts[0] += f"|P:{priority}"
        if assignee != "Unassigned":
            parts[0] += f"|@{assignee}"
        if changes:
            parts.append(f"Changes:{','.join(changes)}")
        if browse_url:
            parts.append(f"URL:{browse_url}")
        return "\n".join(parts)

    elif output_format == "json":
        data = {
            "key": issue_key,
            "summary": summary,
            "status": status,
            "changes": changes,
            "url": browse_url
        }
        if issue_type:
            data["type"] = issue_type
        if priority:
            data["priority"] = priority
        if assignee != "Unassigned":
            data["assignee"] = assignee
        if labels:
            data["labels"] = labels
        return json.dumps(data, separators=(',', ':'))

    else:  # text
        lines = [
            f"Issue Updated: {issue_key}",
            f"Summary: {summary}",
            f"Status: {status}",
        ]
        if issue_type:
            lines.append(f"Type: {issue_type}")
        if priority:
            lines.append(f"Priority: {priority}")
        lines.append(f"Assignee: {assignee}")
        if labels:
            lines.append(f"Labels: {', '.join(labels)}")
        if changes:
            lines.append(f"Changes: {', '.join(changes)}")
        if browse_url:
            lines.append(f"URL: {browse_url}")
        return "\n".join(lines)


def list_transitions_output(issue_key: str, transitions: list[dict]) -> None:
    """List available transitions for an issue."""
    if not transitions:
        print(f"No transitions available for {issue_key}", file=sys.stderr)
        sys.exit(1)

    print(f"Available transitions for {issue_key}:")
    for t in transitions:
        print(f"  - {t['name']} -> {t['to_status']}")


def main():
    parser = argparse.ArgumentParser(
        description="Update Jira issues with token-efficient output"
    )
    parser.add_argument(
        "issue_key",
        help="Jira issue key (e.g., PROJ-123)"
    )
    parser.add_argument(
        "--summary", "-s",
        help="Update issue summary/title"
    )
    parser.add_argument(
        "--description", "-d",
        help="Update issue description"
    )
    parser.add_argument(
        "--status",
        help="Transition to new status"
    )
    parser.add_argument(
        "--priority",
        help="Update priority (e.g., High, Medium, Low)"
    )
    parser.add_argument(
        "--assignee", "-a",
        help="Update assignee (display name, partial match)"
    )
    parser.add_argument(
        "--unassign",
        action="store_true",
        help="Remove assignee from issue"
    )
    parser.add_argument(
        "--labels", "-l",
        help="Set labels (comma-separated, replaces existing)"
    )
    parser.add_argument(
        "--add-labels",
        help="Add labels (comma-separated)"
    )
    parser.add_argument(
        "--remove-labels",
        help="Remove labels (comma-separated)"
    )
    parser.add_argument(
        "--components", "-c",
        help="Set components (comma-separated, replaces existing)"
    )
    parser.add_argument(
        "--comment",
        help="Add a comment to the issue"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )
    parser.add_argument(
        "--list-transitions",
        action="store_true",
        help="List available status transitions"
    )

    args = parser.parse_args()

    try:
        cache = JiraCache()

        # Handle list transitions command
        if args.list_transitions:
            transitions = get_transitions(args.issue_key)
            list_transitions_output(args.issue_key, transitions)
            return

        # Get current issue to determine project
        current_issue = get_issue(args.issue_key)
        project_key = current_issue.get("fields", {}).get("project", {}).get("key", "")
        current_labels = current_issue.get("fields", {}).get("labels", [])

        fields_to_update = {}
        changes = []

        # Summary
        if args.summary:
            fields_to_update["summary"] = args.summary
            changes.append("summary")

        # Description
        if args.description:
            fields_to_update["description"] = markdown_to_adf(args.description)
            changes.append("description")

        # Priority
        if args.priority:
            priority = cache.get_priority_by_name(args.priority)
            if not priority:
                print(f"Error: Priority '{args.priority}' not found", file=sys.stderr)
                sys.exit(1)
            fields_to_update["priority"] = {"id": priority["id"]}
            changes.append("priority")

        # Assignee
        if args.unassign:
            fields_to_update["assignee"] = None
            changes.append("unassigned")
        elif args.assignee:
            if not project_key:
                print("Error: Could not determine project key", file=sys.stderr)
                sys.exit(1)
            user = cache.get_user_by_name(project_key, args.assignee)
            if not user:
                print(f"Error: User '{args.assignee}' not found in project {project_key}", file=sys.stderr)
                sys.exit(1)
            fields_to_update["assignee"] = {"accountId": user["accountId"]}
            changes.append("assignee")

        # Labels - set (replace)
        if args.labels is not None:
            if args.labels == "":
                fields_to_update["labels"] = []
            else:
                fields_to_update["labels"] = [l.strip() for l in args.labels.split(",")]
            changes.append("labels")

        # Labels - add
        if args.add_labels:
            new_labels = [l.strip() for l in args.add_labels.split(",")]
            combined = list(set(current_labels + new_labels))
            fields_to_update["labels"] = combined
            changes.append("labels+")

        # Labels - remove
        if args.remove_labels:
            remove_set = {l.strip().lower() for l in args.remove_labels.split(",")}
            remaining = [l for l in current_labels if l.lower() not in remove_set]
            fields_to_update["labels"] = remaining
            changes.append("labels-")

        # Components
        if args.components is not None:
            if not project_key:
                print("Error: Could not determine project key", file=sys.stderr)
                sys.exit(1)
            if args.components == "":
                fields_to_update["components"] = []
            else:
                component_names = [c.strip() for c in args.components.split(",")]
                components = cache.get_components(project_key)
                component_ids = []
                for name in component_names:
                    name_lower = name.lower()
                    found = None
                    for c in components:
                        if c["name"].lower() == name_lower:
                            found = c
                            break
                    if not found:
                        print(f"Error: Component '{name}' not found", file=sys.stderr)
                        sys.exit(1)
                    component_ids.append({"id": found["id"]})
                fields_to_update["components"] = component_ids
            changes.append("components")

        # Apply field updates
        if fields_to_update:
            update_issue_fields(args.issue_key, fields_to_update)

        # Status transition
        if args.status:
            transitions = get_transitions(args.issue_key)
            target_status = args.status.lower()
            transition = None
            for t in transitions:
                if t["name"].lower() == target_status or t["to_status"].lower() == target_status:
                    transition = t
                    break
            if not transition:
                print(f"Error: Cannot transition to '{args.status}'", file=sys.stderr)
                print("Available transitions:", file=sys.stderr)
                for t in transitions:
                    print(f"  - {t['name']} -> {t['to_status']}", file=sys.stderr)
                sys.exit(1)
            transition_issue(args.issue_key, transition["id"])
            changes.append(f"status->{transition['to_status']}")

        # Add comment
        if args.comment:
            add_comment(args.issue_key, args.comment)
            changes.append("comment")

        # Check if any changes were made
        if not changes:
            print("Error: No updates specified. Use --help for options.", file=sys.stderr)
            sys.exit(1)

        # Fetch updated issue and output
        updated_issue = get_issue(args.issue_key)
        output = format_output(args.issue_key, updated_issue, changes, args.format)
        print(output)

        # Update cache with new issue data
        updated_fields = updated_issue.get("fields", {})
        cache_data = {
            "id": updated_issue.get("id", ""),
            "key": args.issue_key,
            "summary": updated_fields.get("summary", ""),
            "status": updated_fields.get("status", {}).get("name", ""),
            "labels": updated_fields.get("labels", []),
        }
        # Try to update existing cached issue, or add new if not present
        if cache.get_cached_issue(args.issue_key):
            cache.update_cached_issue_fields(args.issue_key, cache_data)
        else:
            cache.set_cached_issue(args.issue_key, cache_data)

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

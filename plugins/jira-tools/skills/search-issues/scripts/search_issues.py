#!/usr/bin/env python3
"""
Search Jira issues using JQL or simple filters.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python search_issues.py --jql "project = PROJ AND status = Open"
    python search_issues.py --project PROJ --status "In Progress"
"""

import argparse
import base64
import json
import os
import sys
from typing import Optional
from urllib.parse import urljoin, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


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


def api_request(path: str, method: str = "GET", data: Optional[dict] = None) -> dict:
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
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 400:
            raise ValueError(f"Invalid JQL query: {error_body}")
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError(f"Access denied: {error_body}")
        else:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def build_jql(
    jql: Optional[str] = None,
    project: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    issue_type: Optional[str] = None,
    priority: Optional[str] = None,
    labels: Optional[str] = None,
    created: Optional[str] = None,
    updated: Optional[str] = None,
) -> str:
    """Build JQL query from parameters."""
    if jql:
        return jql

    clauses = []

    if project:
        clauses.append(f'project = "{project}"')

    if status:
        clauses.append(f'status = "{status}"')

    if assignee:
        if assignee.lower() == "me":
            clauses.append("assignee = currentUser()")
        else:
            clauses.append(f'assignee ~ "{assignee}"')

    if issue_type:
        clauses.append(f'type = "{issue_type}"')

    if priority:
        clauses.append(f'priority = "{priority}"')

    if labels:
        label_list = [l.strip() for l in labels.split(",")]
        if len(label_list) == 1:
            clauses.append(f'labels = "{label_list[0]}"')
        else:
            labels_str = ", ".join([f'"{l}"' for l in label_list])
            clauses.append(f"labels in ({labels_str})")

    if created:
        if created.startswith("-"):
            clauses.append(f"created >= {created}")
        else:
            clauses.append(f'created >= "{created}"')

    if updated:
        if updated.startswith("-"):
            clauses.append(f"updated >= {updated}")
        else:
            clauses.append(f'updated >= "{updated}"')

    return " AND ".join(clauses) if clauses else "ORDER BY created DESC"


def search_issues(
    jql: str,
    fields: list[str],
    max_results: int = 20,
    order_by: Optional[str] = None,
) -> dict:
    """Search for issues using JQL via the new /search/jql endpoint."""
    # Add ORDER BY if not present and order_by is specified
    if order_by and "ORDER BY" not in jql.upper():
        jql = f"{jql} ORDER BY {order_by}"
    elif "ORDER BY" not in jql.upper():
        jql = f"{jql} ORDER BY updated DESC"

    # Build POST request body for new /search/jql endpoint
    request_body = {
        "jql": jql,
        "fields": fields,
        "maxResults": max_results,
    }

    result = api_request("/rest/api/3/search/jql", method="POST", data=request_body)

    return {
        "total": result.get("total", 0),
        "issues": result.get("issues", []),
        "jql": jql,
    }


def extract_text_from_adf(adf_doc: Optional[dict]) -> str:
    """Extract plain text from Atlassian Document Format."""
    if not adf_doc or not isinstance(adf_doc, dict):
        return ""

    def extract_content(node: dict) -> str:
        text_parts = []
        if node.get("type") == "text":
            text_parts.append(node.get("text", ""))
        for child in node.get("content", []):
            text_parts.append(extract_content(child))
        return "".join(text_parts)

    return extract_content(adf_doc)


def format_issue(issue: dict, compact: bool = True) -> dict:
    """Extract and format issue fields."""
    fields = issue.get("fields", {})

    key = issue.get("key", "")
    summary = fields.get("summary", "No summary")
    status = fields.get("status", {}).get("name", "Unknown")
    issue_type = fields.get("issuetype", {}).get("name", "Unknown")

    priority = fields.get("priority")
    priority_name = priority.get("name", "None") if priority else "None"

    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

    labels = fields.get("labels", [])
    created = fields.get("created", "")[:10] if fields.get("created") else ""
    updated = fields.get("updated", "")[:10] if fields.get("updated") else ""

    return {
        "key": key,
        "summary": summary,
        "status": status,
        "type": issue_type,
        "priority": priority_name,
        "assignee": assignee_name,
        "labels": labels,
        "created": created,
        "updated": updated,
    }


def format_output(result: dict, output_format: str) -> str:
    """Format search results for output."""
    issues = [format_issue(i) for i in result["issues"]]
    total = result["total"]
    shown = len(issues)

    if output_format == "compact":
        lines = []
        for issue in issues:
            parts = [
                issue["key"],
                issue["summary"][:50],
                issue["status"],
                issue["type"],
            ]
            if issue["priority"] != "None":
                parts.append(f"P:{issue['priority']}")
            if issue["assignee"] != "Unassigned":
                # Get short name
                name_parts = issue["assignee"].split()
                short_name = name_parts[0].lower() if name_parts else issue["assignee"]
                parts.append(f"@{short_name}")
            lines.append("|".join(parts))

        if shown < total:
            lines.append(f"Found: {shown}/{total} issues (more available)")
        else:
            lines.append(f"Found: {total} issues")

        return "\n".join(lines)

    elif output_format == "table":
        # Simple table format
        lines = [
            "Key       | Summary                        | Status       | Type   | Priority | Assignee",
            "----------|--------------------------------|--------------|--------|----------|----------"
        ]
        for issue in issues:
            key = issue["key"][:10].ljust(10)
            summary = issue["summary"][:30].ljust(30)
            status = issue["status"][:12].ljust(12)
            itype = issue["type"][:6].ljust(6)
            priority = issue["priority"][:8].ljust(8)
            assignee = issue["assignee"].split()[0][:10] if issue["assignee"] != "Unassigned" else "-"
            lines.append(f"{key}| {summary}| {status}| {itype}| {priority}| {assignee}")

        lines.append(f"\nFound: {shown}/{total} issues")
        return "\n".join(lines)

    elif output_format == "json":
        return json.dumps({
            "total": total,
            "shown": shown,
            "issues": issues,
        }, separators=(',', ':'))

    else:  # text
        lines = []
        for issue in issues:
            lines.extend([
                f"Issue: {issue['key']}",
                f"Summary: {issue['summary']}",
                f"Status: {issue['status']}",
                f"Type: {issue['type']}",
                f"Priority: {issue['priority']}",
                f"Assignee: {issue['assignee']}",
                f"Created: {issue['created']}",
                f"Updated: {issue['updated']}",
            ])
            if issue["labels"]:
                lines.append(f"Labels: {', '.join(issue['labels'])}")
            lines.append("---")

        lines.append(f"Found: {shown}/{total} issues")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search Jira issues using JQL or filters"
    )

    # JQL query
    parser.add_argument(
        "--jql", "-q",
        help="Raw JQL query string"
    )

    # Simple filters
    parser.add_argument(
        "--project", "-p",
        help="Filter by project key"
    )
    parser.add_argument(
        "--status", "-s",
        help="Filter by status name"
    )
    parser.add_argument(
        "--assignee", "-a",
        help="Filter by assignee (name or 'me')"
    )
    parser.add_argument(
        "--type", "-t",
        dest="issue_type",
        help="Filter by issue type (Bug, Story, etc.)"
    )
    parser.add_argument(
        "--priority",
        help="Filter by priority"
    )
    parser.add_argument(
        "--labels", "-l",
        help="Filter by labels (comma-separated)"
    )
    parser.add_argument(
        "--created",
        help="Created date filter (e.g., '-7d', '2024-01-01')"
    )
    parser.add_argument(
        "--updated",
        help="Updated date filter"
    )

    # Output options
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=20,
        help="Maximum results (default: 20)"
    )
    parser.add_argument(
        "--fields",
        default="summary,status,issuetype,priority,assignee,labels,created,updated",
        help="Fields to retrieve (comma-separated)"
    )
    parser.add_argument(
        "--order",
        help="Sort order (e.g., 'created DESC', 'priority ASC')"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json", "table"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    try:
        # Build JQL from args
        jql = build_jql(
            jql=args.jql,
            project=args.project,
            status=args.status,
            assignee=args.assignee,
            issue_type=args.issue_type,
            priority=args.priority,
            labels=args.labels,
            created=args.created,
            updated=args.updated,
        )

        if not jql or jql == "ORDER BY created DESC":
            parser.error("At least one search criteria required (--jql, --project, --status, etc.)")

        # Parse fields
        fields = [f.strip() for f in args.fields.split(",")]

        # Search
        result = search_issues(
            jql,
            fields,
            max_results=args.max_results,
            order_by=args.order,
        )

        print(format_output(result, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

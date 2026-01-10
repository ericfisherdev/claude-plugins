#!/usr/bin/env python3
"""
Fetch Jira issues with token-efficient output and sprint-aware caching.

Retrieves a summary of issues with only essential fields:
- Issue ID
- Issue key (e.g., EFT-1)
- Labels
- Status
- Summary
- Sprint info (for categorization)

Issues are cached in three categories with different TTLs:
- active_sprint: 1 hour (issues change frequently during active sprints)
- backlog: 12 hours (backlog items change less frequently)
- past_sprints: 24 hours (closed sprint issues rarely change)

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python fetch_backlog.py PROJECT [options]

Scope:
    --scope SCOPE           Filter by: backlog, active-sprint, past-sprints, all (default: all)

Filters:
    --label LABEL           Include only issues with this label (can repeat)
    --exclude-label LABEL   Exclude issues with this label (can repeat)
    --status STATUS         Include only issues with this status (can repeat)
    --exclude-status STATUS Exclude issues with this status (can repeat)
    --jql JQL              Additional JQL clause to append

Options:
    --max-results COUNT     Max issues to retrieve (default: 50)
    --format FORMAT         Output: compact (default), json, text
    --no-cache              Don't cache results
    --refresh               Force refresh (ignore cached results)
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

# Add shared module to path for cache access
SCRIPT_DIR = Path(__file__).parent
SHARED_DIR = SCRIPT_DIR.parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))

try:
    from jira_cache import (
        JiraCache,
        ISSUE_CATEGORY_ACTIVE_SPRINT,
        ISSUE_CATEGORY_BACKLOG,
        ISSUE_CATEGORY_PAST_SPRINTS,
        SPRINT_STATE_ACTIVE,
        SPRINT_STATE_CLOSED,
    )
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    ISSUE_CATEGORY_ACTIVE_SPRINT = "active_sprint"
    ISSUE_CATEGORY_BACKLOG = "backlog"
    ISSUE_CATEGORY_PAST_SPRINTS = "past_sprints"
    SPRINT_STATE_ACTIVE = "active"
    SPRINT_STATE_CLOSED = "closed"

# Scope to JQL mapping
SCOPE_JQL = {
    "backlog": "Sprint is EMPTY",
    "active-sprint": "Sprint in openSprints()",
    "past-sprints": "Sprint in closedSprints()",
}

# Scope to cache category mapping
SCOPE_TO_CATEGORY = {
    "backlog": ISSUE_CATEGORY_BACKLOG,
    "active-sprint": ISSUE_CATEGORY_ACTIVE_SPRINT,
    "past-sprints": ISSUE_CATEGORY_PAST_SPRINTS,
}


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


def build_jql(
    project: str,
    scope: Optional[str] = None,
    labels: Optional[list[str]] = None,
    exclude_labels: Optional[list[str]] = None,
    statuses: Optional[list[str]] = None,
    exclude_statuses: Optional[list[str]] = None,
    additional_jql: Optional[str] = None
) -> str:
    """Build JQL query from filters."""
    clauses = [f'project = "{project}"']

    # Scope filter (sprint-based)
    if scope and scope in SCOPE_JQL:
        clauses.append(SCOPE_JQL[scope])

    # Label filters
    if labels:
        for label in labels:
            clauses.append(f'labels = "{label}"')

    if exclude_labels:
        for label in exclude_labels:
            clauses.append(f'labels != "{label}"')

    # Status filters
    if statuses:
        if len(statuses) == 1:
            clauses.append(f'status = "{statuses[0]}"')
        else:
            quoted = ', '.join(f'"{s}"' for s in statuses)
            clauses.append(f'status IN ({quoted})')

    if exclude_statuses:
        for status in exclude_statuses:
            clauses.append(f'status != "{status}"')

    # Additional JQL
    if additional_jql:
        clauses.append(f'({additional_jql})')

    # Order by created date descending (most recent first)
    jql = ' AND '.join(clauses) + ' ORDER BY created DESC'
    return jql


def search_issues(jql: str, max_results: int = 50) -> list[dict]:
    """Search issues using JQL via the new /search/jql endpoint."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    # Request fields including sprint for categorization
    fields = ["summary", "status", "labels"]

    api_path = "/rest/api/3/search/jql"
    url = urljoin(base_url, api_path)

    # Build POST request body
    request_body = {
        "jql": jql,
        "maxResults": max_results,
        "fields": fields,
    }

    req = Request(url, method="POST")
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(request_body).encode()

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("issues", [])
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 400:
            raise ValueError(f"Invalid JQL query: {error_body}")
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError("Access denied to search issues")
        else:
            raise RuntimeError(f"Jira API error: {e.code} - {e.reason}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def extract_issue_summary(issue: dict, scope: Optional[str] = None) -> dict:
    """Extract minimal issue data for caching and output.

    Args:
        issue: Raw issue data from Jira API
        scope: The scope used to fetch ('backlog', 'active-sprint', 'past-sprints')
               Used to set sprint info for cache categorization
    """
    fields = issue.get("fields", {})
    status_obj = fields.get("status", {})

    data = {
        "id": issue.get("id", ""),
        "key": issue.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": status_obj.get("name", "Unknown"),
        "labels": fields.get("labels", []),
    }

    # Set sprint info based on scope for proper cache categorization
    if scope == "active-sprint":
        data["sprint"] = {"state": SPRINT_STATE_ACTIVE}
    elif scope == "past-sprints":
        data["sprint"] = {"state": SPRINT_STATE_CLOSED}
    # For backlog or unspecified, no sprint info means it will be categorized as backlog

    return data


def format_output(issues: list[dict], output_format: str = "compact") -> str:
    """Format issues for output."""
    if output_format == "compact":
        # Ultra-compact: one line per issue
        # Format: KEY|status|labels|summary
        lines = []
        for issue in issues:
            labels_str = ",".join(issue["labels"]) if issue["labels"] else "-"
            line = f"{issue['key']}|{issue['status']}|{labels_str}|{issue['summary']}"
            lines.append(line)
        return "\n".join(lines)

    elif output_format == "json":
        # Compact JSON array
        return json.dumps(issues, separators=(',', ':'))

    else:  # text
        lines = []
        for issue in issues:
            labels_str = ", ".join(issue["labels"]) if issue["labels"] else "none"
            lines.append(f"{issue['key']}: {issue['summary']}")
            lines.append(f"  Status: {issue['status']} | Labels: {labels_str}")
            lines.append("")
        return "\n".join(lines).rstrip()


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Jira issues with token-efficient output and sprint-aware caching"
    )
    parser.add_argument(
        "project",
        help="Jira project key (e.g., EFT)"
    )

    # Scope options (sprint-based filtering)
    parser.add_argument(
        "--scope",
        choices=["all", "backlog", "active-sprint", "past-sprints"],
        default="all",
        help="Filter by sprint scope (default: all)"
    )

    # Filter options
    parser.add_argument(
        "--label", "-l",
        action="append",
        dest="labels",
        help="Include only issues with this label (can repeat)"
    )
    parser.add_argument(
        "--exclude-label", "-L",
        action="append",
        dest="exclude_labels",
        help="Exclude issues with this label (can repeat)"
    )
    parser.add_argument(
        "--status", "-s",
        action="append",
        dest="statuses",
        help="Include only issues with this status (can repeat)"
    )
    parser.add_argument(
        "--exclude-status", "-S",
        action="append",
        dest="exclude_statuses",
        help="Exclude issues with this status (can repeat)"
    )
    parser.add_argument(
        "--jql", "-q",
        help="Additional JQL clause to append"
    )

    # Output options
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=50,
        help="Max issues to retrieve (default: 50)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "json", "text"],
        default="compact",
        help="Output format (default: compact)"
    )

    # Cache options
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't cache results"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh (ignore cached results)"
    )

    # Discovery options
    parser.add_argument(
        "--list-statuses",
        action="store_true",
        help="List available statuses for the project"
    )
    parser.add_argument(
        "--list-labels",
        action="store_true",
        help="List available labels"
    )
    parser.add_argument(
        "--list-sprints",
        action="store_true",
        help="List sprints for the project"
    )

    args = parser.parse_args()

    try:
        # Handle discovery commands
        if args.list_statuses or args.list_labels or args.list_sprints:
            if not CACHE_AVAILABLE:
                print("Error: Cache module not available", file=sys.stderr)
                sys.exit(1)

            cache = JiraCache()
            if args.list_statuses:
                statuses = cache.get_statuses(args.project)
                print("Available statuses:")
                for s in statuses:
                    print(f"  {s['name']} ({s['category']})")
            if args.list_labels:
                labels = cache.get_labels()
                print("Available labels:")
                for label in labels[:50]:  # Limit output
                    print(f"  {label}")
                if len(labels) > 50:
                    print(f"  ... and {len(labels) - 50} more")
            if args.list_sprints:
                sprints = cache.get_sprints(args.project, force_refresh=True)
                if not sprints:
                    print(f"No sprints found for project {args.project}")
                else:
                    print(f"Sprints for {args.project}:")
                    for s in sprints:
                        state_icon = {"active": "*", "closed": "-", "future": "+"}
                        icon = state_icon.get(s["state"], "?")
                        print(f"  [{icon}] {s['id']}: {s['name']} ({s['state']})")
                    print("\nLegend: * active, + future, - closed")
            return

        # Determine scope for JQL and caching
        scope = args.scope if args.scope != "all" else None

        # Build JQL
        jql = build_jql(
            project=args.project,
            scope=scope,
            labels=args.labels,
            exclude_labels=args.exclude_labels,
            statuses=args.statuses,
            exclude_statuses=args.exclude_statuses,
            additional_jql=args.jql
        )

        # Fetch issues
        raw_issues = search_issues(jql, args.max_results)

        # Extract minimal data with scope for proper categorization
        issues = [extract_issue_summary(issue, scope) for issue in raw_issues]

        # Cache results with appropriate category
        if CACHE_AVAILABLE and not args.no_cache:
            cache = JiraCache()
            # If specific scope, use that category; otherwise auto-categorize
            category = SCOPE_TO_CATEGORY.get(scope) if scope else None
            cache.set_cached_issues(issues, category=category)

        # Format and output
        output = format_output(issues, args.format)
        print(output)

        # Print summary to stderr
        scope_label = f" ({scope})" if scope else ""
        print(f"\n# {len(issues)} issues found{scope_label}", file=sys.stderr)

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

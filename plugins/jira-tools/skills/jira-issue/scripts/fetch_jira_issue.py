#!/usr/bin/env python3
"""
Fetch Jira issue information with token-efficient output.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python fetch_jira_issue.py ISSUE-123 [options]

Presets (recommended):
    --preset minimal    Key, summary, status only (~20 tokens)
    --preset standard   Core fields, truncated desc, 3 comments (~200 tokens)
    --preset full       All fields, 10 comments with truncation (~500 tokens)

Options:
    --fields FIELD1,FIELD2    Comma-separated fields to retrieve
    --max-desc LENGTH         Truncate description to LENGTH chars (default: 500)
    --max-comments COUNT      Limit comments (default: 0)
    --max-comment-len LENGTH  Truncate each comment (default: 200)
    --format FORMAT           Output: compact (default), text, json, markdown
"""

# Preset configurations for common use cases
PRESETS = {
    "minimal": {
        "fields": "summary,status",
        "max_desc": 0,
        "max_comments": 0,
        "format": "compact"
    },
    "standard": {
        "fields": "summary,status,issuetype,priority,assignee,description",
        "max_desc": 500,
        "max_comments": 3,
        "max_comment_len": 200,
        "format": "compact"
    },
    "full": {
        "fields": "summary,status,issuetype,priority,assignee,reporter,description,labels,components,created,updated",
        "max_desc": 1500,
        "max_comments": 10,
        "max_comment_len": 400,
        "format": "text"
    }
}

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

# Add shared module to path for cache access
SCRIPT_DIR = Path(__file__).parent
SHARED_DIR = SCRIPT_DIR.parent.parent.parent / "shared"
sys.path.insert(0, str(SHARED_DIR))

# Import cache for issue caching
try:
    from jira_cache import JiraCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


def cache_issue(issue: dict) -> None:
    """Cache issue summary data for cross-skill reference."""
    if not CACHE_AVAILABLE:
        return
    try:
        fields = issue.get("fields", {})
        cache_data = {
            "id": issue.get("id", ""),
            "key": issue.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "") if fields.get("status") else "",
            "labels": fields.get("labels", []),
        }
        cache = JiraCache()
        cache.set_cached_issue(issue.get("key", ""), cache_data)
    except Exception:
        pass  # Silently fail caching to not interrupt main functionality


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


def truncate_text(text: Optional[str], max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if truncated."""
    if text is None:
        return ""
    if max_length <= 0 or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def fetch_issue(
    issue_key: str,
    fields: Optional[list[str]] = None,
    expand: Optional[list[str]] = None
) -> dict:
    """Fetch issue from Jira REST API."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    # Build API URL
    api_path = f"/rest/api/3/issue/{issue_key}"
    params = []

    if fields:
        params.append(f"fields={','.join(fields)}")
    if expand:
        params.append(f"expand={','.join(expand)}")

    url = urljoin(base_url, api_path)
    if params:
        url += "?" + "&".join(params)

    # Make request
    req = Request(url)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Issue {issue_key} not found")
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError(f"Access denied to issue {issue_key}")
        else:
            raise RuntimeError(f"Jira API error: {e.code} - {e.reason}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def fetch_comments(issue_key: str, max_results: int = 50) -> list[dict]:
    """Fetch comments for an issue."""
    base_url = os.environ.get("JIRA_BASE_URL")
    if not base_url:
        raise EnvironmentError("JIRA_BASE_URL environment variable required")

    api_path = f"/rest/api/3/issue/{issue_key}/comment"
    url = urljoin(base_url, api_path)
    url += f"?maxResults={max_results}&orderBy=-created"

    req = Request(url)
    req.add_header("Authorization", get_auth_header())
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("comments", [])
    except HTTPError:
        return []


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


def format_issue_data(
    issue: dict,
    comments: list[dict],
    max_desc: int = 0,
    max_comment_len: int = 0,
    output_format: str = "text"
) -> str:
    """Format issue data for output."""
    fields = issue.get("fields", {})

    # Extract core fields
    key = issue.get("key", "Unknown")
    summary = fields.get("summary", "No summary")
    status = fields.get("status", {}).get("name", "Unknown")
    issue_type = fields.get("issuetype", {}).get("name", "Unknown")
    priority = fields.get("priority", {}).get("name", "None") if fields.get("priority") else "None"

    # Extract assignee/reporter
    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

    reporter = fields.get("reporter")
    reporter_name = reporter.get("displayName", "Unknown") if reporter else "Unknown"

    # Extract description
    description_adf = fields.get("description")
    description = extract_text_from_adf(description_adf)
    if max_desc > 0:
        description = truncate_text(description, max_desc)

    # Extract labels and components
    labels = fields.get("labels", [])
    components = [c.get("name", "") for c in fields.get("components", [])]

    # Extract dates
    created = fields.get("created", "")[:10] if fields.get("created") else ""
    updated = fields.get("updated", "")[:10] if fields.get("updated") else ""

    # Process comments
    processed_comments = []
    for comment in comments:
        author = comment.get("author", {}).get("displayName", "Unknown")
        created_at = comment.get("created", "")[:10] if comment.get("created") else ""
        body_adf = comment.get("body")
        body = extract_text_from_adf(body_adf)
        if max_comment_len > 0:
            body = truncate_text(body, max_comment_len)
        processed_comments.append({
            "author": author,
            "created": created_at,
            "body": body
        })

    if output_format == "compact":
        # Ultra-compact format: minimal tokens
        parts = [f"{key}|{summary}|{status}"]
        if issue_type and issue_type != "Unknown":
            parts[0] += f"|{issue_type}"
        if priority and priority != "None":
            parts[0] += f"|P:{priority}"
        if assignee_name != "Unassigned":
            parts[0] += f"|@{assignee_name}"
        if description:
            parts.append(f"Desc:{description}")
        if processed_comments:
            for c in processed_comments:
                parts.append(f"[{c['author']}]{c['body']}")
        return "\n".join(parts)

    elif output_format == "json":
        # Compact JSON - no indentation
        data = {"key": key, "summary": summary, "status": status}
        if issue_type and issue_type != "Unknown":
            data["type"] = issue_type
        if priority and priority != "None":
            data["priority"] = priority
        if assignee_name != "Unassigned":
            data["assignee"] = assignee_name
        if reporter_name != "Unknown":
            data["reporter"] = reporter_name
        if description:
            data["description"] = description
        if labels:
            data["labels"] = labels
        if components:
            data["components"] = components
        if created:
            data["created"] = created
        if updated:
            data["updated"] = updated
        if processed_comments:
            data["comments"] = processed_comments
        return json.dumps(data, separators=(',', ':'))

    elif output_format == "markdown":
        lines = [
            f"# {key}: {summary}",
            "",
            f"**Status:** {status} | **Type:** {issue_type} | **Priority:** {priority}",
            f"**Assignee:** {assignee_name} | **Reporter:** {reporter_name}",
            f"**Created:** {created} | **Updated:** {updated}",
        ]

        if labels:
            lines.append(f"**Labels:** {', '.join(labels)}")
        if components:
            lines.append(f"**Components:** {', '.join(components)}")

        if description:
            lines.extend(["", "## Description", "", description])

        if processed_comments:
            lines.extend(["", "## Comments", ""])
            for c in processed_comments:
                lines.append(f"### {c['author']} ({c['created']})")
                lines.append(c['body'])
                lines.append("")

        return "\n".join(lines)

    else:  # text format
        lines = [
            f"Issue: {key}",
            f"Summary: {summary}",
            f"Status: {status}",
            f"Type: {issue_type}",
            f"Priority: {priority}",
            f"Assignee: {assignee_name}",
            f"Reporter: {reporter_name}",
            f"Created: {created}",
            f"Updated: {updated}",
        ]

        if labels:
            lines.append(f"Labels: {', '.join(labels)}")
        if components:
            lines.append(f"Components: {', '.join(components)}")

        if description:
            lines.extend(["", "Description:", description])

        if processed_comments:
            lines.extend(["", "Comments:"])
            for c in processed_comments:
                lines.append(f"  [{c['created']}] {c['author']}:")
                lines.append(f"    {c['body']}")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Jira issue information with token-efficient output"
    )
    parser.add_argument(
        "issue_key",
        help="Jira issue key (e.g., PROJ-123)"
    )
    parser.add_argument(
        "--preset",
        choices=["minimal", "standard", "full"],
        help="Use preset configuration (minimal ~20 tokens, standard ~200, full ~500)"
    )
    parser.add_argument(
        "--fields",
        help="Comma-separated fields (default: summary,status,issuetype,priority,assignee)"
    )
    parser.add_argument(
        "--max-desc",
        type=int,
        help="Max description length in chars (default: 500, 0=exclude)"
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        help="Max comments to retrieve (default: 0)"
    )
    parser.add_argument(
        "--max-comment-len",
        type=int,
        help="Max length per comment (default: 200)"
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Exclude comments entirely"
    )
    parser.add_argument(
        "--format",
        choices=["compact", "text", "json", "markdown"],
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    # Apply preset defaults, then override with explicit args
    config = {
        "fields": "summary,status,issuetype,priority,assignee",
        "max_desc": 500,
        "max_comments": 0,
        "max_comment_len": 200,
        "format": "compact"
    }

    if args.preset:
        config.update(PRESETS[args.preset])

    # Override with explicit arguments
    if args.fields:
        config["fields"] = args.fields
    if args.max_desc is not None:
        config["max_desc"] = args.max_desc
    if args.max_comments is not None:
        config["max_comments"] = args.max_comments
    if args.max_comment_len is not None:
        config["max_comment_len"] = args.max_comment_len
    if args.format:
        config["format"] = args.format
    if args.no_comments:
        config["max_comments"] = 0

    try:
        # Parse fields
        fields = [f.strip() for f in config["fields"].split(",")]

        # Fetch issue
        issue = fetch_issue(args.issue_key, fields=fields)

        # Cache issue for cross-skill reference
        cache_issue(issue)

        # Fetch comments
        comments = []
        if config["max_comments"] > 0:
            comments = fetch_comments(args.issue_key, config["max_comments"])

        # Format and output
        output = format_issue_data(
            issue,
            comments,
            max_desc=config["max_desc"],
            max_comment_len=config["max_comment_len"],
            output_format=config["format"]
        )

        print(output)

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

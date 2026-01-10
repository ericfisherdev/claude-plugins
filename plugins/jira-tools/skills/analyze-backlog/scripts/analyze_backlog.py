#!/usr/bin/env python3
"""
Helper script for the analyze-backlog skill.

Provides utilities for:
1. Finding unanalyzed backlog issues (missing claude-analyzed label)
2. Getting full issue details including description
3. Updating issue description with analysis and adding label

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    # Find issues to analyze
    python analyze_backlog.py find PROJECT [--max-results 3]

    # Get issue with full description for analysis
    python analyze_backlog.py get ISSUE-KEY

    # Update issue with analysis (appends to description, adds label)
    python analyze_backlog.py update ISSUE-KEY --analysis-file analysis.md
    python analyze_backlog.py update ISSUE-KEY --analysis "Analysis text..."
"""

import argparse
import json
import os
import sys
from datetime import datetime
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


# Label used to mark analyzed issues
# Note: Jira auto-creates labels when added - no need to pre-create
ANALYZED_LABEL = "claude-analyzed"


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


def text_to_adf(text: str) -> dict:
    """Convert plain text to Atlassian Document Format.

    Handles:
    - Headings (lines starting with ## or ###)
    - Horizontal rules (---)
    - Code blocks (```...```)
    - Regular paragraphs
    """
    lines = text.split('\n')
    content = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip empty lines (they'll create paragraph breaks naturally)
        if not line.strip():
            i += 1
            continue

        # Handle code blocks
        if line.strip().startswith('```'):
            code_lang = line.strip()[3:] or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```

            code_block = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": '\n'.join(code_lines)}]
            }
            if code_lang:
                code_block["attrs"] = {"language": code_lang}
            content.append(code_block)
            continue

        # Handle horizontal rules
        if line.strip() == '---':
            content.append({"type": "rule"})
            i += 1
            continue

        # Handle headings
        if line.startswith('### '):
            content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": line[4:]}]
            })
            i += 1
            continue

        if line.startswith('## '):
            content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": line[3:]}]
            })
            i += 1
            continue

        if line.startswith('# '):
            content.append({
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": line[2:]}]
            })
            i += 1
            continue

        # Handle bullet points
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            list_items = []
            while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                item_text = lines[i].strip()[2:]
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": item_text}]
                    }]
                })
                i += 1
            content.append({
                "type": "bulletList",
                "content": list_items
            })
            continue

        # Handle numbered lists
        if line.strip() and line.strip()[0].isdigit() and '. ' in line:
            list_items = []
            while i < len(lines) and lines[i].strip() and lines[i].strip()[0].isdigit() and '. ' in lines[i]:
                item_text = lines[i].strip().split('. ', 1)[1] if '. ' in lines[i] else lines[i].strip()
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": item_text}]
                    }]
                })
                i += 1
            content.append({
                "type": "orderedList",
                "content": list_items
            })
            continue

        # Regular paragraph - collect consecutive non-empty lines
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') and not lines[i].strip().startswith('```') and lines[i].strip() != '---' and not (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
            para_lines.append(lines[i])
            i += 1

        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": ' '.join(para_lines)}]
        })

    return {
        "type": "doc",
        "version": 1,
        "content": content if content else [{"type": "paragraph", "content": [{"type": "text", "text": ""}]}]
    }


def find_unanalyzed_issues(project: str, max_results: int = 3) -> list[dict]:
    """Find backlog issues without the claude-analyzed label.

    NOTE: This function queries Jira directly (no cache) to ensure we get
    the current state of labels. This prevents race conditions where another
    person may have already analyzed an issue.
    """
    jql = f'project = "{project}" AND Sprint is EMPTY AND labels != "{ANALYZED_LABEL}" ORDER BY created DESC'

    fields = "summary,status,labels,description"
    api_path = f"/rest/api/3/search?jql={quote(jql)}&maxResults={max_results}&fields={fields}"

    result = api_request(api_path)
    issues = []

    for issue in result.get("issues", []):
        fields_data = issue.get("fields", {})
        issues.append({
            "key": issue.get("key", ""),
            "id": issue.get("id", ""),
            "summary": fields_data.get("summary", ""),
            "status": fields_data.get("status", {}).get("name", ""),
            "labels": fields_data.get("labels", []),
            "has_description": bool(fields_data.get("description")),
        })

    return issues


def get_issue_full(issue_key: str) -> dict:
    """Get issue with full details including description."""
    fields = "summary,status,issuetype,priority,assignee,reporter,description,labels,components,created,updated"
    result = api_request(f"/rest/api/3/issue/{issue_key}?fields={fields}")

    fields_data = result.get("fields", {})
    description_adf = fields_data.get("description")
    description_text = extract_text_from_adf(description_adf)

    return {
        "key": result.get("key", ""),
        "id": result.get("id", ""),
        "summary": fields_data.get("summary", ""),
        "status": fields_data.get("status", {}).get("name", ""),
        "type": fields_data.get("issuetype", {}).get("name", ""),
        "priority": fields_data.get("priority", {}).get("name", "") if fields_data.get("priority") else "",
        "assignee": fields_data.get("assignee", {}).get("displayName", "") if fields_data.get("assignee") else "",
        "reporter": fields_data.get("reporter", {}).get("displayName", "") if fields_data.get("reporter") else "",
        "labels": fields_data.get("labels", []),
        "components": [c.get("name", "") for c in fields_data.get("components", [])],
        "created": fields_data.get("created", "")[:10] if fields_data.get("created") else "",
        "updated": fields_data.get("updated", "")[:10] if fields_data.get("updated") else "",
        "description": description_text,
        "description_adf": description_adf,
    }


def update_with_analysis(issue_key: str, analysis_text: str) -> dict:
    """Update issue: append analysis to description and add label.

    Args:
        issue_key: Jira issue key
        analysis_text: The analysis text to append (will be formatted with header)

    Returns:
        Updated issue data
    """
    # Get current issue to preserve original description
    current = get_issue_full(issue_key)
    current_labels = current.get("labels", [])
    current_desc = current.get("description", "")

    # Build new description with analysis appended
    today = datetime.now().strftime("%Y-%m-%d")

    if current_desc.strip():
        new_description = f"""{current_desc}

---

## Claude Analysis

{analysis_text}

---
*Analysis generated by Claude on {today}*"""
    else:
        new_description = f"""## Claude Analysis

{analysis_text}

---
*Analysis generated by Claude on {today}*"""

    # Convert to ADF
    new_desc_adf = text_to_adf(new_description)

    # Prepare labels update
    new_labels = list(set(current_labels + [ANALYZED_LABEL]))

    # Update issue
    update_data = {
        "fields": {
            "description": new_desc_adf,
            "labels": new_labels,
        }
    }

    api_request(f"/rest/api/3/issue/{issue_key}", method="PUT", data=update_data)

    # Fetch and return updated issue
    updated = get_issue_full(issue_key)

    # Update cache if available
    if CACHE_AVAILABLE:
        try:
            cache = JiraCache()
            cache_data = {
                "id": updated.get("id", ""),
                "key": issue_key,
                "summary": updated.get("summary", ""),
                "status": updated.get("status", ""),
                "labels": updated.get("labels", []),
            }
            if cache.get_cached_issue(issue_key):
                cache.update_cached_issue_fields(issue_key, cache_data)
            else:
                cache.set_cached_issue(issue_key, cache_data)
        except Exception:
            pass  # Don't fail on cache errors

    return updated


def format_find_output(issues: list[dict], output_format: str) -> str:
    """Format the find results."""
    if output_format == "json":
        return json.dumps(issues, separators=(',', ':'))

    if not issues:
        return "No unanalyzed backlog issues found."

    if output_format == "compact":
        lines = []
        for issue in issues:
            labels_str = ",".join(issue["labels"]) if issue["labels"] else "-"
            line = f"{issue['key']}|{issue['status']}|{labels_str}|{issue['summary']}"
            lines.append(line)
        return "\n".join(lines)

    # text format
    lines = [f"Found {len(issues)} unanalyzed backlog issue(s):", ""]
    for issue in issues:
        labels_str = ", ".join(issue["labels"]) if issue["labels"] else "none"
        lines.append(f"{issue['key']}: {issue['summary']}")
        lines.append(f"  Status: {issue['status']} | Labels: {labels_str}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_get_output(issue: dict, output_format: str) -> str:
    """Format the get results."""
    if output_format == "json":
        return json.dumps(issue, separators=(',', ':'))

    if output_format == "compact":
        parts = [f"{issue['key']}|{issue['summary']}|{issue['status']}"]
        if issue.get("type"):
            parts[0] += f"|{issue['type']}"
        if issue.get("priority"):
            parts[0] += f"|P:{issue['priority']}"
        if issue.get("description"):
            parts.append(f"Desc:{issue['description']}")
        return "\n".join(parts)

    # text format
    lines = [
        f"Issue: {issue['key']}",
        f"Summary: {issue['summary']}",
        f"Status: {issue['status']}",
        f"Type: {issue.get('type', 'Unknown')}",
        f"Priority: {issue.get('priority', 'None')}",
        f"Assignee: {issue.get('assignee', 'Unassigned')}",
        f"Reporter: {issue.get('reporter', 'Unknown')}",
        f"Created: {issue.get('created', '')}",
        f"Updated: {issue.get('updated', '')}",
    ]

    if issue.get("labels"):
        lines.append(f"Labels: {', '.join(issue['labels'])}")
    if issue.get("components"):
        lines.append(f"Components: {', '.join(issue['components'])}")

    if issue.get("description"):
        lines.extend(["", "Description:", issue["description"]])

    return "\n".join(lines)


def format_update_output(issue: dict, output_format: str) -> str:
    """Format the update results."""
    base_url = os.environ.get("JIRA_BASE_URL", "")
    browse_url = f"{base_url}/browse/{issue['key']}" if base_url else ""

    if output_format == "json":
        result = {
            "key": issue["key"],
            "summary": issue["summary"],
            "status": issue["status"],
            "labels": issue.get("labels", []),
            "analyzed": True,
            "url": browse_url,
        }
        return json.dumps(result, separators=(',', ':'))

    if output_format == "compact":
        parts = [f"UPDATED|{issue['key']}|{issue['summary']}|{issue['status']}"]
        parts.append(f"Labels:{','.join(issue.get('labels', []))}")
        if browse_url:
            parts.append(f"URL:{browse_url}")
        return "\n".join(parts)

    # text format
    lines = [
        f"Issue Updated: {issue['key']}",
        f"Summary: {issue['summary']}",
        f"Status: {issue['status']}",
        f"Labels: {', '.join(issue.get('labels', []))}",
        f"Analysis: Added",
        f"URL: {browse_url}",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Helper script for analyze-backlog skill"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Find command
    find_parser = subparsers.add_parser(
        "find",
        help="Find unanalyzed backlog issues"
    )
    find_parser.add_argument(
        "project",
        help="Jira project key"
    )
    find_parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=3,
        help="Max issues to return (default: 3)"
    )
    find_parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="text",
        help="Output format"
    )

    # Get command
    get_parser = subparsers.add_parser(
        "get",
        help="Get full issue details including description"
    )
    get_parser.add_argument(
        "issue_key",
        help="Jira issue key"
    )
    get_parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="text",
        help="Output format"
    )

    # Update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update issue with analysis"
    )
    update_parser.add_argument(
        "issue_key",
        help="Jira issue key"
    )
    update_parser.add_argument(
        "--analysis",
        help="Analysis text to append to description"
    )
    update_parser.add_argument(
        "--analysis-file",
        help="File containing analysis text"
    )
    update_parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="text",
        help="Output format"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "find":
            issues = find_unanalyzed_issues(args.project, args.max_results)
            output = format_find_output(issues, args.format)
            print(output)
            print(f"\n# {len(issues)} issue(s) to analyze", file=sys.stderr)

        elif args.command == "get":
            issue = get_issue_full(args.issue_key)
            output = format_get_output(issue, args.format)
            print(output)

        elif args.command == "update":
            if args.analysis_file:
                with open(args.analysis_file, 'r') as f:
                    analysis_text = f.read()
            elif args.analysis:
                analysis_text = args.analysis
            else:
                print("Error: Either --analysis or --analysis-file required", file=sys.stderr)
                sys.exit(1)

            updated = update_with_analysis(args.issue_key, analysis_text)
            output = format_update_output(updated, args.format)
            print(output)

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

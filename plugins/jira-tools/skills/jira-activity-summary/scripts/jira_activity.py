#!/usr/bin/env python3
"""
Summarize Jira activity for the current user in a given project and time period.

Usage:
    python jira_activity.py --project MBC --period yesterday
    python jira_activity.py --project MBC --period today
    python jira_activity.py --project MBC --period this_week
    python jira_activity.py --project MBC --period last_week
    python jira_activity.py --project MBC --period this_month
    python jira_activity.py --project MBC --period yesterday --max-issues 200

Environment Variables:
    JIRA_BASE_URL   - e.g., https://yoursite.atlassian.net
    JIRA_EMAIL      - Your Jira account email
    JIRA_API_TOKEN  - API token from Atlassian account settings
"""

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Auth / HTTP helpers
# ---------------------------------------------------------------------------

def _auth_header():
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    if not email or not token:
        print("Error: JIRA_EMAIL and JIRA_API_TOKEN environment variables are required.", file=sys.stderr)
        sys.exit(1)
    encoded = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {encoded}"


def _request(base_url, path, *, method="GET", body=None):
    url = base_url.rstrip("/") + path
    req = Request(url, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Jira API {e.code} on {path}: {detail}") from e
    except URLError as e:
        raise ConnectionError(f"Cannot reach Jira at {base_url}: {e.reason}") from e


# ---------------------------------------------------------------------------
# Date range helpers
# ---------------------------------------------------------------------------

def get_date_range(period: str):
    today = datetime.now()
    if period == "today":
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == "yesterday":
        d = today - timedelta(days=1)
        start = d.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = d.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_week":
        monday = today - timedelta(days=today.weekday())
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == "last_week":
        this_monday = today - timedelta(days=today.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "this_month":
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today
    else:
        raise ValueError(f"Unknown period '{period}'")
    return start, end


def format_date_header(period: str, start: datetime, end: datetime) -> str:
    if period in ("today", "yesterday"):
        return start.strftime("%m/%d/%Y")
    elif period in ("this_week", "last_week"):
        day = start.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"Week of {start.strftime('%b')} {day}{suffix}"
    elif period == "this_month":
        return start.strftime("%B %Y")
    return start.strftime("%m/%d/%Y")


# ---------------------------------------------------------------------------
# Jira datetime parsing
# ---------------------------------------------------------------------------

def parse_jira_dt(dt_str: str) -> datetime:
    """Parse a Jira timestamp like '2024-01-15T10:30:00.000+0000' to naive datetime.

    Timestamps are stored as UTC in Jira. We strip the timezone and compare
    naively against local start/end, which is close enough for daily summaries.
    """
    if not dt_str:
        return datetime.min
    # Remove milliseconds, normalize offset ('+0000' → '+00:00')
    s = re.sub(r'\.\d+', '', dt_str)
    s = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', s)
    s = s.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(s).replace(tzinfo=None)
    except ValueError:
        return datetime.min


# ---------------------------------------------------------------------------
# Atlassian Document Format (ADF) text extraction
# ---------------------------------------------------------------------------

def extract_text(body, my_account_id: str = None) -> tuple[str, bool]:
    """Return (plain_text, was_mentioned_in_body).

    body may be an ADF dict, a plain string, or None.
    was_mentioned_in_body is True if an ADF @mention with my_account_id is found.
    """
    if body is None:
        return "", False
    if isinstance(body, str):
        return body, False
    if isinstance(body, dict):
        parts: list[str] = []
        mentioned = [False]
        _walk_adf(body, parts, mentioned, my_account_id)
        return " ".join(parts).strip(), mentioned[0]
    return str(body), False


def _walk_adf(node: dict, parts: list, mentioned: list, my_account_id: str):
    ntype = node.get("type", "")
    if ntype == "text":
        text = node.get("text", "")
        if text.strip():
            parts.append(text)
    elif ntype == "mention":
        attrs = node.get("attrs", {})
        if my_account_id and attrs.get("id") == my_account_id:
            mentioned[0] = True
        label = attrs.get("text", attrs.get("displayName", ""))
        if label:
            parts.append(label)
    elif ntype in ("hardBreak", "rule"):
        parts.append(" ")
    for child in node.get("content", []):
        _walk_adf(child, parts, mentioned, my_account_id)


def truncate(text: str, max_len: int = 200) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= max_len else flat[:max_len - 3] + "..."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def paginate(base_url: str, jql: str, fields: list[str]) -> list[dict]:
    """Fetch all issues matching a JQL query, following nextPageToken pagination."""
    issues = []
    next_token = None
    while True:
        body = {"jql": jql, "maxResults": 100, "fields": fields}
        if next_token:
            body["nextPageToken"] = next_token
        result = _request(base_url, "/rest/api/3/search/jql", method="POST", body=body)
        batch = result.get("issues", [])
        issues.extend(batch)
        if result.get("isLast", True) or not batch:
            break
        next_token = result.get("nextPageToken")
    return issues


def main():
    parser = argparse.ArgumentParser(description="Summarize your Jira activity")
    parser.add_argument("--project", "-p", required=True, help="Project key (e.g., MBC)")
    parser.add_argument(
        "--period", "-t", required=True,
        choices=["today", "yesterday", "this_week", "last_week", "this_month"],
    )
    args = parser.parse_args()

    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    if not base_url:
        print("Error: JIRA_BASE_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)

    start, end = get_date_range(args.period)
    project = args.project.upper()

    # Date bounds for JQL — always use both start and end to keep result sets small
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")

    # Current user
    me = _request(base_url, "/rest/api/3/myself")
    my_id: str = me["accountId"]

    # Ticket changes: my assigned tickets updated in the period
    ticket_jql  = f'project = "{project}" AND assignee = currentUser() AND updated >= "{start_str}" AND updated <= "{end_str}" ORDER BY updated DESC'
    # Comments: active sprint issues only, updated in the period
    comment_jql = f'project = "{project}" AND sprint in openSprints() AND updated >= "{start_str}" AND updated <= "{end_str}" ORDER BY updated DESC'

    ticket_issues  = paginate(base_url, ticket_jql,  ["summary", "assignee"])
    comment_issues = paginate(base_url, comment_jql, ["summary", "assignee"])

    ticket_keys  = {i["key"] for i in ticket_issues}
    comment_keys = {i["key"] for i in comment_issues}

    # All unique issues, ticket issues first so their assignee data is preferred on overlap
    all_issues_map: dict[str, dict] = {i["key"]: i for i in comment_issues}
    all_issues_map.update({i["key"]: i for i in ticket_issues})
    issues = list(all_issues_map.values())

    # Collected results
    status_changes: list[dict] = []
    my_comments:    list[dict] = []
    their_comments: list[dict] = []
    seen_comment_ids: set[str] = set()

    for issue in issues:
        key    = issue["key"]
        fields = issue.get("fields", {})
        summary      = fields.get("summary", "")
        assignee     = fields.get("assignee") or {}
        assignee_id  = assignee.get("accountId", "")
        assignee_name = assignee.get("displayName", "Unassigned")
        is_my_ticket = assignee_id == my_id

        # ---- Status changes (only for tickets assigned to me) ----
        if key in ticket_keys and is_my_ticket:
            changelog = _request(base_url, f"/rest/api/3/issue/{key}/changelog?maxResults=100")
            transitions = []
            for history in changelog.get("values", []):
                created_dt = parse_jira_dt(history.get("created", ""))
                if not (start <= created_dt <= end):
                    continue
                for item in history.get("items", []):
                    if item.get("field") == "status":
                        transitions.append({
                            "from": item.get("fromString", ""),
                            "to":   item.get("toString", ""),
                            "ts":   created_dt,
                        })
            if transitions:
                transitions.sort(key=lambda x: x["ts"])
                # Build a chain: [first_from, t1_to, t2_to, ...]
                chain = [transitions[0]["from"]] + [t["to"] for t in transitions]
                # Remove consecutive duplicates
                deduped = [chain[0]]
                for s in chain[1:]:
                    if s != deduped[-1]:
                        deduped.append(s)
                status_changes.append({"key": key, "summary": summary, "chain": deduped})

        # ---- Comments (active sprint issues only) ----
        if key not in comment_keys:
            continue
        comments_data = _request(
            base_url,
            f"/rest/api/3/issue/{key}/comment?maxResults=100&orderBy=created"
        )
        for comment in comments_data.get("comments", []):
            cid = comment.get("id")
            if cid in seen_comment_ids:
                continue

            author       = comment.get("author", {})
            author_id    = author.get("accountId", "")
            author_name  = author.get("displayName", "Unknown")
            created_dt   = parse_jira_dt(comment.get("created", ""))

            if not (start <= created_dt <= end):
                continue

            text, is_mentioned = extract_text(comment.get("body"), my_id)
            text = truncate(text)

            if author_id == my_id:
                # I wrote this comment
                seen_comment_ids.add(cid)
                my_comments.append({
                    "key":          key,
                    "summary":      summary,
                    "assignee_name": assignee_name,
                    "is_my_ticket": is_my_ticket,
                    "text":         text,
                })
            elif is_my_ticket or is_mentioned:
                # Someone else commented on my ticket, or @mentioned me
                seen_comment_ids.add(cid)
                their_comments.append({
                    "key":          key,
                    "summary":      summary,
                    "author_name":  author_name,
                    "is_my_ticket": is_my_ticket,
                    "is_mention":   is_mentioned,
                    "text":         text,
                })

    # ---- Format output ----
    date_header = format_date_header(args.period, start, end)
    lines = [f"# Jira Activity for {date_header}", ""]

    lines.append("## Ticket changes")
    if status_changes:
        for sc in status_changes:
            lines.append(f"{sc['key']} moved from {' to '.join(sc['chain'])}")
    else:
        lines.append("No status changes on your assigned tickets.")
    lines.append("")

    lines.append("## Comments")
    if my_comments or their_comments:
        # Group my comments by text — collapse identical comments across multiple tickets
        from collections import defaultdict
        grouped: dict[str, list[dict]] = defaultdict(list)
        for c in my_comments:
            grouped[c["text"]].append(c)

        for text, group in grouped.items():
            if len(group) == 1:
                c = group[0]
                if c["is_my_ticket"]:
                    label = "(your ticket)"
                elif c["assignee_name"] == "Unassigned":
                    label = "(unassigned)"
                else:
                    label = f"(assigned to {c['assignee_name']})"
                lines.append(f"### Left a comment on {c['key']} {label}:")
            else:
                keys = ", ".join(c["key"] for c in group)
                lines.append(f"### Left the same comment on {len(group)} tickets ({keys}):")
            lines.append(f'- "{text}"')
            lines.append("")

        for c in their_comments:
            if c["is_my_ticket"] and c["is_mention"]:
                lines.append(
                    f"### {c['author_name']} commented on your ticket {c['key']} and mentioned you:"
                )
            elif c["is_my_ticket"]:
                lines.append(f"### {c['author_name']} commented on your ticket {c['key']}:")
            else:
                lines.append(f"### {c['author_name']} mentioned you in a comment on {c['key']}:")
            lines.append(f'- "{c["text"]}"')
            lines.append("")
    else:
        lines.append("No comments found.")

    print("\n".join(lines))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Log work (time tracking) on Jira issues.

Environment Variables:
    JIRA_BASE_URL: Jira instance URL (e.g., https://yoursite.atlassian.net)
    JIRA_EMAIL: User email for authentication
    JIRA_API_TOKEN: API token for authentication

Usage:
    python log_work.py PROJ-123 --time "2h" [--comment "Description"]
"""

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin
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


def api_request(
    path: str,
    method: str = "GET",
    data: Optional[dict] = None
) -> Optional[dict]:
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
            content = response.read().decode()
            return json.loads(content) if content else None
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 404:
            raise ValueError(f"Issue not found: {error_body}")
        elif e.code == 401:
            raise PermissionError("Authentication failed - check credentials")
        elif e.code == 403:
            raise PermissionError(f"Access denied: {error_body}")
        elif e.code == 400:
            raise ValueError(f"Bad request: {error_body}")
        else:
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
    except URLError as e:
        raise ConnectionError(f"Failed to connect to Jira: {e.reason}")


def parse_time_to_seconds(time_str: str) -> int:
    """Parse Jira time format to seconds.

    Supports: 1w, 1d, 1h, 1m (or combinations like "1h 30m")
    Assumes: 1w = 5d, 1d = 8h
    """
    time_str = time_str.strip().lower()
    total_seconds = 0

    # Pattern to match time components
    pattern = r'(\d+(?:\.\d+)?)\s*(w|d|h|m)'
    matches = re.findall(pattern, time_str)

    if not matches:
        raise ValueError(
            f"Invalid time format: '{time_str}'. Use format like '2h', '1h 30m', '1d'"
        )

    multipliers = {
        'w': 5 * 8 * 60 * 60,  # 1 week = 5 days
        'd': 8 * 60 * 60,      # 1 day = 8 hours
        'h': 60 * 60,          # 1 hour
        'm': 60,               # 1 minute
    }

    for value, unit in matches:
        total_seconds += int(float(value) * multipliers[unit])

    return total_seconds


def format_seconds_to_time(seconds: int) -> str:
    """Format seconds back to readable time string."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours and minutes:
        return f"{hours}h {minutes}m"
    elif hours:
        return f"{hours}h"
    elif minutes:
        return f"{minutes}m"
    else:
        return "0m"


def add_worklog(
    issue_key: str,
    time_spent_seconds: int,
    comment: Optional[str] = None,
    started: Optional[str] = None,
    adjust_estimate: str = "auto",
    new_estimate: Optional[str] = None,
    reduce_by: Optional[str] = None,
) -> dict:
    """Add a worklog to an issue."""
    # Prepare started date
    if started:
        started_dt = started
    else:
        started_dt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000")

    payload: dict = {
        "timeSpentSeconds": time_spent_seconds,
        "started": started_dt,
    }

    if comment:
        payload["comment"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment}]
                }
            ]
        }

    # Build query params for estimate adjustment
    params = []
    if adjust_estimate != "auto":
        params.append(f"adjustEstimate={adjust_estimate}")
        if adjust_estimate == "new" and new_estimate:
            params.append(f"newEstimate={new_estimate}")
        elif adjust_estimate == "manual" and reduce_by:
            params.append(f"reduceBy={reduce_by}")

    path = f"/rest/api/3/issue/{issue_key}/worklog"
    if params:
        path += "?" + "&".join(params)

    result = api_request(path, method="POST", data=payload)

    return {
        "issue": issue_key,
        "id": result.get("id", ""),
        "timeSpent": result.get("timeSpent", format_seconds_to_time(time_spent_seconds)),
        "timeSpentSeconds": time_spent_seconds,
        "started": started_dt[:10],
        "author": result.get("author", {}).get("displayName", ""),
        "comment": comment or "",
    }


def format_output(result: dict, output_format: str) -> str:
    """Format the result for output."""
    if output_format == "compact":
        parts = [
            "LOGGED",
            result["issue"],
            result["timeSpent"],
        ]
        if result["author"]:
            parts.append(f"@{result['author']}")
        parts.append(result["started"])
        return "|".join(parts)

    elif output_format == "json":
        return json.dumps({
            "issue": result["issue"],
            "timeSpent": result["timeSpent"],
            "timeSpentSeconds": result["timeSpentSeconds"],
            "started": result["started"],
        }, separators=(',', ':'))

    else:  # text
        lines = [
            "Work Logged",
            f"Issue: {result['issue']}",
            f"Time: {result['timeSpent']} ({result['timeSpentSeconds']} seconds)",
        ]
        if result["author"]:
            lines.append(f"Author: {result['author']}")
        lines.append(f"Started: {result['started']}")
        if result["comment"]:
            lines.append(f"Comment: {result['comment']}")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Log work on a Jira issue"
    )
    parser.add_argument(
        "issue_key",
        help="Issue key (e.g., PROJ-123)"
    )
    parser.add_argument(
        "--time", "-t",
        required=True,
        help="Time spent (e.g., '2h', '1h 30m', '90m')"
    )
    parser.add_argument(
        "--comment", "-c",
        help="Description of work done"
    )
    parser.add_argument(
        "--started", "-s",
        help="Start date/time in ISO format (default: now)"
    )
    parser.add_argument(
        "--adjust-estimate",
        choices=["auto", "leave", "new", "manual"],
        default="auto",
        help="How to adjust remaining estimate (default: auto)"
    )
    parser.add_argument(
        "--new-estimate",
        help="New remaining estimate (use with --adjust-estimate new)"
    )
    parser.add_argument(
        "--reduce-by",
        help="Reduce remaining by this amount (use with --adjust-estimate manual)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    try:
        # Parse time
        time_seconds = parse_time_to_seconds(args.time)

        result = add_worklog(
            args.issue_key.upper(),
            time_seconds,
            comment=args.comment,
            started=args.started,
            adjust_estimate=args.adjust_estimate,
            new_estimate=args.new_estimate,
            reduce_by=args.reduce_by,
        )

        print(format_output(result, args.format))

    except (EnvironmentError, ValueError, PermissionError, ConnectionError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

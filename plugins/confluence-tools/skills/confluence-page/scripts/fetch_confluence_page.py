#!/usr/bin/env python3
"""
Fetch Confluence page with token-efficient output.

Usage:
    python fetch_confluence_page.py PAGE_ID [options]
    python fetch_confluence_page.py --space SPACE --title TITLE [options]

Examples:
    python fetch_confluence_page.py 123456
    python fetch_confluence_page.py 123456 --preset minimal
    python fetch_confluence_page.py --space DEV --title "API Docs"
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


# Preset configurations
PRESETS = {
    "minimal": {
        "body_length": 0,
        "include_labels": False,
        "include_ancestors": False,
    },
    "standard": {
        "body_length": 500,
        "include_labels": False,
        "include_ancestors": False,
    },
    "full": {
        "body_length": -1,  # Full content
        "include_labels": True,
        "include_ancestors": True,
    },
}


def truncate_body(body: str, max_length: int) -> str:
    """Truncate body content to max_length."""
    if max_length == 0:
        return ""
    if max_length < 0 or len(body) <= max_length:
        return body
    return body[:max_length] + "..."


def strip_html_basic(html: str) -> str:
    """Basic HTML stripping for display (not for parsing)."""
    import re
    # Remove common tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def format_compact(page: dict, base_url: str) -> str:
    """Format page as compact output."""
    lines = []

    # Main line: PAGE|id|title|space|status
    main = f"PAGE|{page['id']}|{page['title']}|{page.get('spaceKey', '')}|{page.get('status', 'current')}"
    lines.append(main)

    # Body if present
    if page.get("body"):
        body_text = strip_html_basic(page["body"])
        lines.append(f"Body: {body_text}")

    # Labels if present
    if page.get("labels"):
        lines.append(f"Labels: {','.join(page['labels'])}")

    # Ancestors if present
    if page.get("ancestors"):
        ancestor_titles = [a["title"] for a in page["ancestors"]]
        lines.append(f"Path: {' > '.join(ancestor_titles)}")

    # URL
    space_key = page.get("spaceKey", "")
    url = f"{base_url}/wiki/spaces/{space_key}/pages/{page['id']}"
    lines.append(f"URL:{url}")

    return "\n".join(lines)


def format_text(page: dict, base_url: str) -> str:
    """Format page as readable text."""
    lines = []
    lines.append(f"Page: {page['title']}")
    lines.append(f"ID: {page['id']}")

    if page.get("spaceKey"):
        lines.append(f"Space: {page['spaceKey']}")

    lines.append(f"Status: {page.get('status', 'current')}")
    lines.append(f"Version: {page.get('version', 1)}")

    if page.get("ancestors"):
        ancestor_titles = [a["title"] for a in page["ancestors"]]
        lines.append(f"Path: {' > '.join(ancestor_titles)}")

    if page.get("labels"):
        lines.append(f"Labels: {', '.join(page['labels'])}")

    if page.get("body"):
        body_text = strip_html_basic(page["body"])
        lines.append(f"Body: {body_text}")

    space_key = page.get("spaceKey", "")
    url = f"{base_url}/wiki/spaces/{space_key}/pages/{page['id']}"
    lines.append(f"URL: {url}")

    return "\n".join(lines)


def format_json(page: dict, base_url: str) -> str:
    """Format page as JSON."""
    space_key = page.get("spaceKey", "")
    output = {
        "id": page["id"],
        "title": page["title"],
        "space": space_key,
        "status": page.get("status", "current"),
        "version": page.get("version", 1),
        "url": f"{base_url}/wiki/spaces/{space_key}/pages/{page['id']}",
    }

    if page.get("body"):
        output["body"] = strip_html_basic(page["body"])

    if page.get("labels"):
        output["labels"] = page["labels"]

    if page.get("ancestors"):
        output["ancestors"] = [{"id": a["id"], "title": a["title"]} for a in page["ancestors"]]

    return json.dumps(output)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Confluence page with token-efficient output"
    )
    parser.add_argument(
        "page_id",
        nargs="?",
        help="Page ID to fetch"
    )
    parser.add_argument(
        "--space", "-s",
        help="Space key (required with --title)"
    )
    parser.add_argument(
        "--title", "-t",
        help="Page title to search for"
    )
    parser.add_argument(
        "--preset", "-p",
        choices=["minimal", "standard", "full"],
        default="standard",
        help="Output preset (default: standard)"
    )
    parser.add_argument(
        "--body-length",
        type=int,
        help="Max body characters (0=none, -1=full). Overrides preset."
    )
    parser.add_argument(
        "--include-labels",
        action="store_true",
        help="Include page labels"
    )
    parser.add_argument(
        "--include-ancestors",
        action="store_true",
        help="Include parent page chain"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache, fetch fresh"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.page_id and not (args.space and args.title):
        parser.error("Either PAGE_ID or --space and --title are required")

    if args.title and not args.space:
        parser.error("--space is required when using --title")

    # Check environment
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
    if not base_url:
        print("ERROR: CONFLUENCE_BASE_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    # Initialize cache
    cache = ConfluenceCache()

    # Get preset configuration
    preset_config = PRESETS[args.preset].copy()

    # Override with explicit arguments
    if args.body_length is not None:
        preset_config["body_length"] = args.body_length
    if args.include_labels:
        preset_config["include_labels"] = True
    if args.include_ancestors:
        preset_config["include_ancestors"] = True

    try:
        # Fetch page
        if args.page_id:
            page = cache.get_page(args.page_id, force_refresh=args.no_cache)
        else:
            page = cache.get_page_by_title(args.space, args.title)

        if not page:
            if args.page_id:
                print(f"ERROR: Page {args.page_id} not found", file=sys.stderr)
            else:
                print(f"ERROR: Page '{args.title}' not found in space {args.space}", file=sys.stderr)
            sys.exit(1)

        # Get space key for the page
        if page.get("spaceId") and not page.get("spaceKey"):
            # Try to look up space key
            spaces = cache.get_spaces()
            for s in spaces:
                if s["id"] == page["spaceId"]:
                    page["spaceKey"] = s["key"]
                    break
        if args.space:
            page["spaceKey"] = args.space

        # Process body
        if preset_config["body_length"] != 0 and page.get("body"):
            page["body"] = truncate_body(page["body"], preset_config["body_length"])
        elif preset_config["body_length"] == 0:
            page["body"] = ""

        # Get labels if requested
        if preset_config["include_labels"]:
            page["labels"] = cache.get_labels(page["id"])

        # Get ancestors if requested
        if preset_config["include_ancestors"]:
            page["ancestors"] = cache.get_page_ancestors(page["id"])

        # Format output
        if args.format == "compact":
            output = format_compact(page, base_url)
        elif args.format == "text":
            output = format_text(page, base_url)
        else:
            output = format_json(page, base_url)

        print(output)

    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

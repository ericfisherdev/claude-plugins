#!/usr/bin/env python3
"""
Create a Confluence page with token-efficient output.

Usage:
    python create_confluence_page.py --space SPACE --title TITLE [options]

Examples:
    python create_confluence_page.py --space DEV --title "New Page"
    python create_confluence_page.py --space DEV --title "Docs" --body "<p>Content</p>"
    python create_confluence_page.py --space DEV --title "Child" --parent 123456
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


def format_compact(page: dict, base_url: str) -> str:
    """Format created page as compact output."""
    url = f"{base_url}/wiki/spaces/{page['space']}/pages/{page['id']}"
    return f"CREATED|{page['id']}|{page['title']}|{page['space']}\nURL:{url}"


def format_text(page: dict, base_url: str) -> str:
    """Format created page as readable text."""
    url = f"{base_url}/wiki/spaces/{page['space']}/pages/{page['id']}"
    lines = [
        f"Page Created: {page['title']}",
        f"ID: {page['id']}",
        f"Space: {page['space']}",
    ]
    if page.get("parentId"):
        lines.append(f"Parent ID: {page['parentId']}")
    lines.append(f"URL: {url}")
    return "\n".join(lines)


def format_json(page: dict, base_url: str) -> str:
    """Format created page as JSON."""
    url = f"{base_url}/wiki/spaces/{page['space']}/pages/{page['id']}"
    output = {
        "id": page["id"],
        "title": page["title"],
        "space": page["space"],
        "url": url,
    }
    if page.get("parentId"):
        output["parentId"] = page["parentId"]
    return json.dumps(output)


def main():
    parser = argparse.ArgumentParser(
        description="Create a Confluence page"
    )
    parser.add_argument(
        "--space", "-s",
        required=True,
        help="Space key"
    )
    parser.add_argument(
        "--title", "-t",
        required=True,
        help="Page title"
    )
    parser.add_argument(
        "--body", "-b",
        default="",
        help="Page body in storage format (HTML)"
    )
    parser.add_argument(
        "--body-file",
        help="Read body content from file (use '-' for stdin)"
    )
    parser.add_argument(
        "--parent", "-p",
        help="Parent page ID"
    )
    parser.add_argument(
        "--parent-title",
        help="Parent page title (alternative to --parent)"
    )
    parser.add_argument(
        "--labels", "-l",
        help="Comma-separated labels to add"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    # Check environment
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
    if not base_url:
        print("ERROR: CONFLUENCE_BASE_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    # Initialize cache
    cache = ConfluenceCache()

    try:
        # Get space ID
        space = cache.get_space_by_key(args.space)
        if not space:
            # Try to refresh spaces
            cache.refresh_spaces()
            space = cache.get_space_by_key(args.space)
            if not space:
                print(f"ERROR: Space '{args.space}' not found", file=sys.stderr)
                sys.exit(1)

        space_id = space["id"]

        # Get body content
        body = args.body
        if args.body_file:
            if args.body_file == "-":
                body = sys.stdin.read()
            else:
                with open(args.body_file, "r") as f:
                    body = f.read()

        # Resolve parent
        parent_id = args.parent
        if args.parent_title and not parent_id:
            parent_page = cache.get_page_by_title(args.space, args.parent_title)
            if parent_page:
                parent_id = parent_page["id"]
            else:
                print(f"ERROR: Parent page '{args.parent_title}' not found in space {args.space}", file=sys.stderr)
                sys.exit(1)

        # Build request payload (using v2 API)
        payload = {
            "spaceId": space_id,
            "title": args.title,
            "body": {
                "representation": "storage",
                "value": body or "<p></p>"  # Empty paragraph if no body
            }
        }

        if parent_id:
            payload["parentId"] = parent_id

        # Create page
        result = cache._api_request("/pages", method="POST", data=payload)

        page_data = {
            "id": result["id"],
            "title": result["title"],
            "space": args.space,
            "parentId": parent_id,
        }

        # Add labels if specified
        if args.labels:
            label_list = [l.strip() for l in args.labels.split(",") if l.strip()]
            if label_list:
                label_payload = [{"name": label} for label in label_list]
                try:
                    cache._api_request(
                        f"/pages/{result['id']}/labels",
                        method="POST",
                        data=label_payload
                    )
                except RuntimeError as e:
                    print(f"Warning: Failed to add labels: {e}", file=sys.stderr)

        # Invalidate related caches
        cache.invalidate_page(result["id"])

        # Format output
        if args.format == "compact":
            output = format_compact(page_data, base_url)
        elif args.format == "text":
            output = format_text(page_data, base_url)
        else:
            output = format_json(page_data, base_url)

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

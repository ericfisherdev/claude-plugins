#!/usr/bin/env python3
"""
Create a Confluence folder (or folder-like page) with token-efficient output.

Usage:
    python create_confluence_folder.py --space SPACE --title TITLE [options]

Examples:
    python create_confluence_folder.py --space DEV --title "Documentation"
    python create_confluence_folder.py --space DEV --title "API Docs" --parent 123456
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


def format_compact(folder: dict, base_url: str) -> str:
    """Format created folder as compact output."""
    url = f"{base_url}/wiki/spaces/{folder['space']}/pages/{folder['id']}"
    return f"FOLDER|{folder['id']}|{folder['title']}|{folder['space']}\nURL:{url}"


def format_text(folder: dict, base_url: str) -> str:
    """Format created folder as readable text."""
    url = f"{base_url}/wiki/spaces/{folder['space']}/pages/{folder['id']}"
    lines = [
        f"Folder Created: {folder['title']}",
        f"ID: {folder['id']}",
        f"Space: {folder['space']}",
        f"Type: {folder['type']}",
    ]
    if folder.get("parentId"):
        lines.append(f"Parent ID: {folder['parentId']}")
    lines.append(f"URL: {url}")
    return "\n".join(lines)


def format_json(folder: dict, base_url: str) -> str:
    """Format created folder as JSON."""
    url = f"{base_url}/wiki/spaces/{folder['space']}/pages/{folder['id']}"
    output = {
        "id": folder["id"],
        "title": folder["title"],
        "space": folder["space"],
        "type": folder["type"],
        "url": url,
    }
    if folder.get("parentId"):
        output["parentId"] = folder["parentId"]
    return json.dumps(output)


def create_folder_page(
    cache: ConfluenceCache,
    space_id: str,
    title: str,
    parent_id: str | None,
    description: str | None
) -> dict:
    """Create a page that acts as a folder container."""
    # Create minimal body content
    if description:
        body = f"<p>{description}</p>"
    else:
        body = "<p></p>"  # Empty paragraph - minimal content

    payload = {
        "spaceId": space_id,
        "title": title,
        "body": {
            "representation": "storage",
            "value": body
        }
    }

    if parent_id:
        payload["parentId"] = parent_id

    result = cache._api_request("/pages", method="POST", data=payload)
    return result


def try_create_folder(
    cache: ConfluenceCache,
    space_id: str,
    title: str,
    parent_id: str | None
) -> dict | None:
    """Try to create a true folder (Confluence Cloud feature)."""
    # Confluence v2 API supports folders in some instances
    # This is a newer feature and may not be available everywhere
    try:
        payload = {
            "spaceId": space_id,
            "title": title,
            "type": "folder"
        }

        if parent_id:
            payload["parentId"] = parent_id

        result = cache._api_request("/folders", method="POST", data=payload)
        return result
    except RuntimeError:
        # Folder API not available, fall back to page
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create a Confluence folder"
    )
    parser.add_argument(
        "--space", "-s",
        required=True,
        help="Space key"
    )
    parser.add_argument(
        "--title", "-t",
        required=True,
        help="Folder title"
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
        "--description", "-d",
        help="Brief description for folder page"
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
            cache.refresh_spaces()
            space = cache.get_space_by_key(args.space)
            if not space:
                print(f"ERROR: Space '{args.space}' not found", file=sys.stderr)
                sys.exit(1)

        space_id = space["id"]

        # Resolve parent
        parent_id = args.parent
        if args.parent_title and not parent_id:
            parent_page = cache.get_page_by_title(args.space, args.parent_title)
            if parent_page:
                parent_id = parent_page["id"]
            else:
                print(f"ERROR: Parent page '{args.parent_title}' not found in space {args.space}", file=sys.stderr)
                sys.exit(1)

        # Try to create true folder first, fall back to page
        result = try_create_folder(cache, space_id, args.title, parent_id)
        folder_type = "folder"

        if not result:
            # Fall back to creating a page as folder
            result = create_folder_page(cache, space_id, args.title, parent_id, args.description)
            folder_type = "page (container)"

        folder_data = {
            "id": result["id"],
            "title": result.get("title", args.title),
            "space": args.space,
            "parentId": parent_id,
            "type": folder_type,
        }

        # Invalidate cache
        cache.invalidate_page(result["id"])

        # Format output
        if args.format == "compact":
            output = format_compact(folder_data, base_url)
        elif args.format == "text":
            output = format_text(folder_data, base_url)
        else:
            output = format_json(folder_data, base_url)

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

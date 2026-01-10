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


def try_create_folder(
    cache: ConfluenceCache,
    space_id: str,
    title: str,
    parent_id: str | None
) -> dict:
    """Create a true folder (Confluence Cloud feature).

    Raises RuntimeError if folder creation fails.
    """
    payload = {
        "spaceId": space_id,
        "title": title,
    }

    if parent_id:
        payload["parentId"] = parent_id

    result = cache._api_request("/folders", method="POST", data=payload)
    return result


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
        help="Parent page/folder title (alternative to --parent)"
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

        # Create true folder (no fallback to pages)
        result = try_create_folder(cache, space_id, args.title, parent_id)

        folder_data = {
            "id": result["id"],
            "title": result.get("title", args.title),
            "space": args.space,
            "parentId": parent_id,
            "type": "folder",
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
        error_str = str(e)
        if "404" in error_str or "not found" in error_str.lower():
            print("ERROR: Folder creation failed. The Confluence folders API may not be available.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Suggestions:", file=sys.stderr)
            print("  1. Create the folder manually in Confluence UI", file=sys.stderr)
            print("  2. Check if folders are enabled for this space", file=sys.stderr)
            print("  3. Verify parent ID exists and is a valid folder", file=sys.stderr)
        elif "already exists" in error_str.lower() or "duplicate" in error_str.lower():
            print(f"ERROR: A folder with title '{args.title}' already exists in this location", file=sys.stderr)
        else:
            print(f"ERROR: Failed to create folder: {e}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

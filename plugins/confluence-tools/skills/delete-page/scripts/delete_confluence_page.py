#!/usr/bin/env python3
"""
Delete a Confluence page or folder with token-efficient output.

Usage:
    python delete_confluence_page.py --id PAGE_ID [options]

Examples:
    python delete_confluence_page.py --id 123456
    python delete_confluence_page.py --id 123456 --type folder
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


def format_compact(result: dict) -> str:
    """Format deletion result as compact output."""
    return f"DELETED|{result['id']}|{result['type']}|{result['title']}"


def format_text(result: dict) -> str:
    """Format deletion result as readable text."""
    lines = [
        f"Deleted: {result['title']}",
        f"ID: {result['id']}",
        f"Type: {result['type']}",
    ]
    return "\n".join(lines)


def format_json(result: dict) -> str:
    """Format deletion result as JSON."""
    return json.dumps(result)


def get_page_info(cache: ConfluenceCache, page_id: str) -> dict | None:
    """Get page info before deletion."""
    try:
        result = cache._api_request(f"/pages/{page_id}")
        return {
            "id": result["id"],
            "title": result["title"],
            "type": "page"
        }
    except RuntimeError:
        return None


def get_folder_info(cache: ConfluenceCache, folder_id: str) -> dict | None:
    """Get folder info before deletion."""
    try:
        result = cache._api_request(f"/folders/{folder_id}")
        return {
            "id": result["id"],
            "title": result["title"],
            "type": "folder"
        }
    except RuntimeError:
        return None


def delete_page(cache: ConfluenceCache, page_id: str) -> bool:
    """Delete a page."""
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    import base64
    import os

    base_url = os.environ.get("CONFLUENCE_BASE_URL", "").rstrip('/')
    url = f"{base_url}/wiki/api/v2/pages/{page_id}"

    email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_API_TOKEN")
    credentials = f"{email}:{token}"
    auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"

    req = Request(url, method="DELETE")
    req.add_header("Authorization", auth_header)

    try:
        with urlopen(req, timeout=30) as response:
            # 204 No Content is success for DELETE
            return response.status in (200, 204)
    except HTTPError as e:
        if e.code == 204:
            return True
        raise RuntimeError(f"Failed to delete page: {e.code} {e.reason}")


def delete_folder(cache: ConfluenceCache, folder_id: str) -> bool:
    """Delete a folder."""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    import base64
    import os

    base_url = os.environ.get("CONFLUENCE_BASE_URL", "").rstrip('/')
    url = f"{base_url}/wiki/api/v2/folders/{folder_id}"

    email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_API_TOKEN")
    credentials = f"{email}:{token}"
    auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"

    req = Request(url, method="DELETE")
    req.add_header("Authorization", auth_header)

    try:
        with urlopen(req, timeout=30) as response:
            # 204 No Content is success for DELETE
            return response.status in (200, 204)
    except HTTPError as e:
        if e.code == 204:
            return True
        raise RuntimeError(f"Failed to delete folder: {e.code} {e.reason}")


def main():
    parser = argparse.ArgumentParser(
        description="Delete a Confluence page or folder"
    )
    parser.add_argument(
        "--id", "-i",
        required=True,
        help="Page or folder ID to delete"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["page", "folder", "auto"],
        default="auto",
        help="Content type (default: auto-detect)"
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
        content_id = args.id
        content_type = args.type
        info = None

        # Auto-detect type if needed
        if content_type == "auto":
            # Try page first (more common)
            info = get_page_info(cache, content_id)
            if info:
                content_type = "page"
            else:
                info = get_folder_info(cache, content_id)
                if info:
                    content_type = "folder"
                else:
                    print(f"ERROR: Content with ID '{content_id}' not found as page or folder", file=sys.stderr)
                    sys.exit(1)
        else:
            # Get info for the specified type
            if content_type == "page":
                info = get_page_info(cache, content_id)
            else:
                info = get_folder_info(cache, content_id)

            if not info:
                print(f"ERROR: {content_type.capitalize()} with ID '{content_id}' not found", file=sys.stderr)
                sys.exit(1)

        # Perform deletion
        if content_type == "page":
            delete_page(cache, content_id)
        else:
            delete_folder(cache, content_id)

        # Invalidate cache
        cache.invalidate_page(content_id)

        # Prepare result
        result = {
            "id": content_id,
            "title": info["title"],
            "type": content_type,
            "deleted": True
        }

        # Format output
        if args.format == "compact":
            output = format_compact(result)
        elif args.format == "text":
            output = format_text(result)
        else:
            output = format_json(result)

        print(output)

    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        error_str = str(e)
        if "has children" in error_str.lower() or "not empty" in error_str.lower():
            print(f"ERROR: Cannot delete - content has children. Delete children first.", file=sys.stderr)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

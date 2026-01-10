#!/usr/bin/env python3
"""
List Confluence pages with token-efficient output.

Usage:
    python list_confluence_pages.py --space SPACE [options]
    python list_confluence_pages.py --parent PAGE_ID [options]

Examples:
    python list_confluence_pages.py --space DEV
    python list_confluence_pages.py --space DEV --depth 2 --format tree
    python list_confluence_pages.py --parent 123456
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


# Preset configurations
PRESETS = {
    "minimal": ["id", "title", "type"],
    "standard": ["id", "title", "type", "status", "createdAt"],
    "full": ["id", "title", "type", "status", "createdAt", "childCount"],
}


def get_folder_children(cache: ConfluenceCache, folder_id: str) -> list[dict]:
    """Get children of a folder (pages and subfolders) using CQL search."""
    from urllib.parse import quote

    try:
        # Use v1 CQL search to find children of the folder
        cql = f'parent={folder_id}'
        encoded_cql = quote(cql)
        result = cache._api_request(
            f"/content/search?cql={encoded_cql}&limit=100",
            api_version="v1"
        )

        children = []
        for item in result.get("results", []):
            children.append({
                "id": item["id"],
                "title": item["title"],
                "type": item.get("type", "page"),
                "status": item.get("status", "current"),
                "createdAt": item.get("createdAt", ""),
            })
        return children
    except RuntimeError:
        return []


def detect_content_type(cache: ConfluenceCache, content_id: str) -> str | None:
    """Detect if content ID is a page or folder."""
    # Try page first
    try:
        cache._api_request(f"/pages/{content_id}")
        return "page"
    except RuntimeError:
        pass

    # Try folder
    try:
        cache._api_request(f"/folders/{content_id}")
        return "folder"
    except RuntimeError:
        pass

    return None


def fetch_content_recursive(
    cache: ConfluenceCache,
    space_key: str,
    parent_id: str | None,
    parent_type: str | None,
    depth: int,
    current_depth: int,
    force_refresh: bool
) -> list[dict]:
    """Recursively fetch pages and folders up to specified depth."""
    if current_depth > depth:
        return []

    items = []

    if parent_id:
        # Determine parent type if not provided
        if not parent_type:
            parent_type = detect_content_type(cache, parent_id)

        if parent_type == "folder":
            items = get_folder_children(cache, parent_id)
        else:
            # Parent is a page, get page children
            pages = cache.get_page_children(parent_id, force_refresh=force_refresh)
            items = [{"type": "page", **p} for p in pages]
    else:
        # Root level - get pages in space
        pages = cache.get_pages_in_space(space_key, parent_id=None, force_refresh=force_refresh)
        items = [{"type": "page", **p} for p in pages]

    result = []
    for item in items:
        item_data = item.copy()
        if current_depth < depth:
            children = fetch_content_recursive(
                cache, space_key, item["id"], item.get("type"),
                depth, current_depth + 1, force_refresh
            )
            item_data["children"] = children
        result.append(item_data)

    return result


def format_compact(pages: list[dict], space_key: str, fields: list[str]) -> str:
    """Format pages and folders as compact output."""
    lines = []

    # Count total items
    def count_items(item_list: list) -> int:
        total = len(item_list)
        for p in item_list:
            total += count_items(p.get("children", []))
        return total

    total = count_items(pages)
    lines.append(f"ITEMS|{space_key}|{total}")

    def add_items(item_list: list, indent: int = 0):
        for p in item_list:
            item_type = p.get("type", "page").upper()
            parts = [item_type]
            for field in fields:
                if field == "childCount":
                    parts.append(str(len(p.get("children", []))))
                elif field == "type":
                    continue  # Already included as the first part
                else:
                    parts.append(str(p.get(field, "")))
            prefix = "  " * indent if indent > 0 else ""
            lines.append(prefix + "|".join(parts))
            if p.get("children"):
                add_items(p["children"], indent + 1)

    add_items(pages)
    return "\n".join(lines)


def format_tree(pages: list[dict], space_key: str) -> str:
    """Format pages as tree structure with type indicators."""
    lines = []

    def count_items(item_list: list) -> int:
        total = len(item_list)
        for p in item_list:
            total += count_items(p.get("children", []))
        return total

    total = count_items(pages)
    lines.append(f"Space: {space_key} ({total} items)")

    def add_tree(item_list: list, prefix: str = "", is_last_list: bool = True):
        for i, p in enumerate(item_list):
            is_last = i == len(item_list) - 1
            connector = "└── " if is_last else "├── "
            # Add type indicator: [F] for folder, [P] for page
            item_type = p.get("type", "page")
            type_indicator = "[F]" if item_type == "folder" else "[P]"
            lines.append(f"{prefix}{connector}{type_indicator} {p['title']} ({p['id']})")

            if p.get("children"):
                extension = "    " if is_last else "│   "
                add_tree(p["children"], prefix + extension, is_last)

    add_tree(pages)
    return "\n".join(lines)


def format_json(pages: list[dict], space_key: str) -> str:
    """Format pages as JSON."""
    def count_pages(page_list: list) -> int:
        total = len(page_list)
        for p in page_list:
            total += count_pages(p.get("children", []))
        return total

    output = {
        "space": space_key,
        "count": count_pages(pages),
        "pages": pages
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="List Confluence pages"
    )
    parser.add_argument(
        "--space", "-s",
        help="Space key to list pages from"
    )
    parser.add_argument(
        "--parent", "-p",
        help="Parent page ID to list children of"
    )
    parser.add_argument(
        "--depth", "-d",
        type=int,
        default=1,
        help="Recursion depth (default: 1, max: 5)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Maximum pages per level (default: 50)"
    )
    parser.add_argument(
        "--preset",
        choices=["minimal", "standard", "full"],
        default="standard",
        help="Output preset (default: standard)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "tree", "json"],
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
    if not args.space and not args.parent:
        parser.error("Either --space or --parent is required")

    # Limit depth
    depth = min(args.depth, 5)

    # Check environment
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
    if not base_url:
        print("ERROR: CONFLUENCE_BASE_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    # Initialize cache
    cache = ConfluenceCache()

    try:
        # Determine space key
        space_key = args.space
        if args.parent and not space_key:
            # Try to get space from parent page
            page = cache.get_page(args.parent)
            if page and page.get("spaceId"):
                spaces = cache.get_spaces()
                for s in spaces:
                    if s["id"] == page["spaceId"]:
                        space_key = s["key"]
                        break
            if not space_key:
                space_key = "UNKNOWN"

        # Verify space exists if specified
        if args.space:
            space = cache.get_space_by_key(args.space)
            if not space:
                cache.refresh_spaces()
                space = cache.get_space_by_key(args.space)
                if not space:
                    print(f"ERROR: Space '{args.space}' not found", file=sys.stderr)
                    sys.exit(1)

        # Fetch pages and folders
        items = fetch_content_recursive(
            cache,
            space_key,
            args.parent,
            parent_type=None,  # Auto-detect
            depth=depth,
            current_depth=1,
            force_refresh=args.no_cache
        )

        if not items:
            if args.parent:
                print(f"No children found under {args.parent}", file=sys.stderr)
            else:
                print(f"No content found in space {args.space}", file=sys.stderr)
            sys.exit(0)

        # Rename for compatibility with existing formatting functions
        pages = items

        # Get fields from preset
        fields = PRESETS[args.preset]

        # Format output
        if args.format == "compact":
            output = format_compact(pages, space_key, fields)
        elif args.format == "tree":
            output = format_tree(pages, space_key)
        else:
            output = format_json(pages, space_key)

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

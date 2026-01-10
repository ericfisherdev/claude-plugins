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
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


# Preset configurations
PRESETS = {
    "minimal": ["id", "title"],
    "standard": ["id", "title", "status", "createdAt"],
    "full": ["id", "title", "status", "createdAt", "childCount"],
}


def fetch_pages_recursive(
    cache: ConfluenceCache,
    space_key: str,
    parent_id: str | None,
    depth: int,
    current_depth: int,
    force_refresh: bool
) -> list[dict]:
    """Recursively fetch pages up to specified depth."""
    if current_depth > depth:
        return []

    if parent_id:
        pages = cache.get_page_children(parent_id, force_refresh=force_refresh)
    else:
        pages = cache.get_pages_in_space(space_key, parent_id=None, force_refresh=force_refresh)

    result = []
    for page in pages:
        page_data = page.copy()
        if current_depth < depth:
            children = fetch_pages_recursive(
                cache, space_key, page["id"],
                depth, current_depth + 1, force_refresh
            )
            page_data["children"] = children
        result.append(page_data)

    return result


def format_compact(pages: list[dict], space_key: str, fields: list[str]) -> str:
    """Format pages as compact output."""
    lines = []

    # Count total pages
    def count_pages(page_list: list) -> int:
        total = len(page_list)
        for p in page_list:
            total += count_pages(p.get("children", []))
        return total

    total = count_pages(pages)
    lines.append(f"PAGES|{space_key}|{total}")

    def add_pages(page_list: list, indent: int = 0):
        for p in page_list:
            parts = ["PAGE"]
            for field in fields:
                if field == "childCount":
                    parts.append(str(len(p.get("children", []))))
                else:
                    parts.append(str(p.get(field, "")))
            prefix = "  " * indent if indent > 0 else ""
            lines.append(prefix + "|".join(parts))
            if p.get("children"):
                add_pages(p["children"], indent + 1)

    add_pages(pages)
    return "\n".join(lines)


def format_tree(pages: list[dict], space_key: str) -> str:
    """Format pages as tree structure."""
    lines = []

    def count_pages(page_list: list) -> int:
        total = len(page_list)
        for p in page_list:
            total += count_pages(p.get("children", []))
        return total

    total = count_pages(pages)
    lines.append(f"Space: {space_key} ({total} pages)")

    def add_tree(page_list: list, prefix: str = "", is_last_list: bool = True):
        for i, p in enumerate(page_list):
            is_last = i == len(page_list) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{p['title']} ({p['id']})")

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

        # Fetch pages
        pages = fetch_pages_recursive(
            cache,
            space_key,
            args.parent,
            depth,
            current_depth=1,
            force_refresh=args.no_cache
        )

        if not pages:
            if args.parent:
                print(f"No child pages found under page {args.parent}", file=sys.stderr)
            else:
                print(f"No pages found in space {args.space}", file=sys.stderr)
            sys.exit(0)

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

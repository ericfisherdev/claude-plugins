#!/usr/bin/env python3
"""
Update a Confluence page with token-efficient output.

Usage:
    python update_confluence_page.py PAGE_ID [options]

Examples:
    python update_confluence_page.py 123456 --title "New Title"
    python update_confluence_page.py 123456 --body "<p>New content</p>"
    python update_confluence_page.py 123456 --append "<p>More content</p>"
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache
from markdown_converter import markdown_to_confluence


def format_compact(page: dict, changes: list[str], base_url: str) -> str:
    """Format updated page as compact output."""
    url = f"{base_url}/wiki/spaces/{page.get('space', '')}/pages/{page['id']}"
    main = f"UPDATED|{page['id']}|{page['title']}|v{page['version']}"
    change_str = f"Changes:{','.join(changes)}"
    return f"{main}\n{change_str}\nURL:{url}"


def format_text(page: dict, changes: list[str], base_url: str) -> str:
    """Format updated page as readable text."""
    url = f"{base_url}/wiki/spaces/{page.get('space', '')}/pages/{page['id']}"
    lines = [
        f"Page Updated: {page['title']}",
        f"ID: {page['id']}",
        f"Version: {page['version']}",
        f"Changes: {', '.join(changes)}",
        f"URL: {url}",
    ]
    return "\n".join(lines)


def format_json(page: dict, changes: list[str], base_url: str) -> str:
    """Format updated page as JSON."""
    url = f"{base_url}/wiki/spaces/{page.get('space', '')}/pages/{page['id']}"
    output = {
        "id": page["id"],
        "title": page["title"],
        "version": page["version"],
        "changes": changes,
        "url": url,
    }
    return json.dumps(output)


def main():
    parser = argparse.ArgumentParser(
        description="Update a Confluence page"
    )
    parser.add_argument(
        "page_id",
        help="Page ID to update"
    )
    parser.add_argument(
        "--title", "-t",
        help="New page title"
    )
    parser.add_argument(
        "--body", "-b",
        help="New page body (replaces existing)"
    )
    parser.add_argument(
        "--body-file",
        help="Read body from file (use '-' for stdin)"
    )
    parser.add_argument(
        "--markdown", "-m",
        action="store_true",
        help="Treat body/append/prepend content as markdown and convert to Confluence format"
    )
    parser.add_argument(
        "--append", "-a",
        help="Append content to existing body"
    )
    parser.add_argument(
        "--prepend",
        help="Prepend content to existing body"
    )
    parser.add_argument(
        "--labels", "-l",
        help="Set labels (replaces existing)"
    )
    parser.add_argument(
        "--add-labels",
        help="Add labels to existing"
    )
    parser.add_argument(
        "--remove-labels",
        help="Remove specific labels"
    )
    parser.add_argument(
        "--minor-edit",
        action="store_true",
        help="Mark as minor edit (no notifications)"
    )
    parser.add_argument(
        "--version-message",
        help="Version comment/message"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    # Check for at least one update option
    has_update = any([
        args.title,
        args.body,
        args.body_file,
        args.append,
        args.prepend,
        args.labels,
        args.add_labels,
        args.remove_labels,
    ])
    if not has_update:
        parser.error("At least one update option required (--title, --body, --append, etc.)")

    # Check environment
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
    if not base_url:
        print("ERROR: CONFLUENCE_BASE_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    # Initialize cache
    cache = ConfluenceCache()

    try:
        # Fetch current page
        page = cache.get_page(args.page_id, force_refresh=True)
        if not page:
            print(f"ERROR: Page {args.page_id} not found", file=sys.stderr)
            sys.exit(1)

        changes = []
        current_version = page.get("version", 1)
        new_version = current_version + 1

        # Get current body
        current_body = page.get("body", "")

        # Determine new body
        new_body = None
        if args.body_file:
            if args.body_file == "-":
                new_body = sys.stdin.read()
            else:
                with open(args.body_file, "r") as f:
                    new_body = f.read()
            # Convert markdown if requested
            if args.markdown:
                new_body = markdown_to_confluence(new_body)
            changes.append("body")
        elif args.body:
            new_body = args.body
            # Convert markdown if requested
            if args.markdown:
                new_body = markdown_to_confluence(new_body)
            changes.append("body")
        elif args.append:
            append_content = args.append
            if args.markdown:
                append_content = markdown_to_confluence(append_content)
            new_body = current_body + append_content
            changes.append("append")
        elif args.prepend:
            prepend_content = args.prepend
            if args.markdown:
                prepend_content = markdown_to_confluence(prepend_content)
            new_body = prepend_content + current_body
            changes.append("prepend")

        # Determine new title
        new_title = args.title if args.title else page["title"]
        if args.title:
            changes.append("title")

        # Build update payload
        payload = {
            "id": args.page_id,
            "title": new_title,
            "version": {
                "number": new_version,
            }
        }

        if new_body is not None:
            payload["body"] = {
                "representation": "storage",
                "value": new_body
            }

        if args.version_message:
            payload["version"]["message"] = args.version_message

        # Update page
        result = cache._api_request(
            f"/pages/{args.page_id}",
            method="PUT",
            data=payload
        )

        # Handle labels
        if args.labels is not None or args.add_labels or args.remove_labels:
            current_labels = set(cache.get_labels(args.page_id))

            if args.labels is not None:
                # Replace all labels
                new_labels = set(l.strip() for l in args.labels.split(",") if l.strip())
                to_remove = current_labels - new_labels
                to_add = new_labels - current_labels
            else:
                to_remove = set()
                to_add = set()

                if args.add_labels:
                    to_add = set(l.strip() for l in args.add_labels.split(",") if l.strip())
                    to_add = to_add - current_labels

                if args.remove_labels:
                    to_remove = set(l.strip() for l in args.remove_labels.split(",") if l.strip())
                    to_remove = to_remove & current_labels

            # Remove labels
            for label in to_remove:
                try:
                    cache._api_request(
                        f"/pages/{args.page_id}/labels/{label}",
                        method="DELETE"
                    )
                except RuntimeError:
                    pass  # Ignore errors removing labels

            # Add labels
            if to_add:
                label_payload = [{"name": label} for label in to_add]
                try:
                    cache._api_request(
                        f"/pages/{args.page_id}/labels",
                        method="POST",
                        data=label_payload
                    )
                except RuntimeError as e:
                    print(f"Warning: Failed to add labels: {e}", file=sys.stderr)

            if to_add or to_remove:
                changes.append("labels")

        # Invalidate cache
        cache.invalidate_page(args.page_id)

        # Get space key for URL
        space_key = ""
        if page.get("spaceId"):
            spaces = cache.get_spaces()
            for s in spaces:
                if s["id"] == page["spaceId"]:
                    space_key = s["key"]
                    break

        page_data = {
            "id": result["id"],
            "title": result["title"],
            "version": result.get("version", {}).get("number", new_version),
            "space": space_key,
        }

        # Format output
        if args.format == "compact":
            output = format_compact(page_data, changes, base_url)
        elif args.format == "text":
            output = format_text(page_data, changes, base_url)
        else:
            output = format_json(page_data, changes, base_url)

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

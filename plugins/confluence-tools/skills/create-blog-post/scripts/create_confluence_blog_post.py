#!/usr/bin/env python3
"""
Create a Confluence blog post with token-efficient output.

Usage:
    python create_confluence_blog_post.py --space SPACE --title TITLE [options]

Examples:
    python create_confluence_blog_post.py --space DEV --title "Release Notes"
    python create_confluence_blog_post.py --space DEV --title "Update" --body "<p>Content</p>"
    python create_confluence_blog_post.py --space DEV --title "Post" --body-file post.md --markdown
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


def format_compact(post: dict, base_url: str) -> str:
    """Format created blog post as compact output."""
    url = f"{base_url}/wiki/spaces/{post['space']}/blog/{post['id']}"
    return f"CREATED|{post['id']}|{post['title']}|{post['space']}|blogpost\nURL:{url}"


def format_text(post: dict, base_url: str) -> str:
    """Format created blog post as readable text."""
    url = f"{base_url}/wiki/spaces/{post['space']}/blog/{post['id']}"
    lines = [
        f"Blog Post Created: {post['title']}",
        f"ID: {post['id']}",
        f"Space: {post['space']}",
        f"Type: blogpost",
        f"URL: {url}",
    ]
    return "\n".join(lines)


def format_json(post: dict, base_url: str) -> str:
    """Format created blog post as JSON."""
    url = f"{base_url}/wiki/spaces/{post['space']}/blog/{post['id']}"
    output = {
        "id": post["id"],
        "title": post["title"],
        "space": post["space"],
        "type": "blogpost",
        "url": url,
    }
    return json.dumps(output)


def main():
    parser = argparse.ArgumentParser(
        description="Create a Confluence blog post"
    )
    parser.add_argument(
        "--space", "-s",
        required=True,
        help="Space key"
    )
    parser.add_argument(
        "--title", "-t",
        required=True,
        help="Blog post title"
    )
    parser.add_argument(
        "--body", "-b",
        default="",
        help="Post body in storage format (HTML) or markdown (with --markdown)"
    )
    parser.add_argument(
        "--body-file",
        help="Read body content from file (use '-' for stdin)"
    )
    parser.add_argument(
        "--markdown", "-m",
        action="store_true",
        help="Treat body content as markdown and convert to Confluence format"
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

        # Convert markdown to Confluence format if requested
        if args.markdown and body:
            body = markdown_to_confluence(body)

        # Build request payload for blog post (using v2 API)
        payload = {
            "spaceId": space_id,
            "title": args.title,
            "body": {
                "representation": "storage",
                "value": body or "<p></p>"  # Empty paragraph if no body
            }
        }

        # Create blog post using the blogposts endpoint
        result = cache._api_request("/blogposts", method="POST", data=payload)

        post_data = {
            "id": result["id"],
            "title": result["title"],
            "space": args.space,
        }

        # Add labels if specified
        if args.labels:
            label_list = [l.strip() for l in args.labels.split(",") if l.strip()]
            if label_list:
                label_payload = [{"name": label} for label in label_list]
                try:
                    cache._api_request(
                        f"/blogposts/{result['id']}/labels",
                        method="POST",
                        data=label_payload
                    )
                except RuntimeError as e:
                    print(f"Warning: Failed to add labels: {e}", file=sys.stderr)

        # Format output
        if args.format == "compact":
            output = format_compact(post_data, base_url)
        elif args.format == "text":
            output = format_text(post_data, base_url)
        else:
            output = format_json(post_data, base_url)

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

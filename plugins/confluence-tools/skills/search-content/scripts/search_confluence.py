#!/usr/bin/env python3
"""
Search Confluence content with token-efficient output.

Usage:
    python search_confluence.py QUERY [options]
    python search_confluence.py --label LABEL [options]

Examples:
    python search_confluence.py "authentication"
    python search_confluence.py "API docs" --space DEV
    python search_confluence.py --label "architecture"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from confluence_cache import ConfluenceCache


def build_cql(
    query: str | None,
    space: str | None,
    content_type: str | None,
    label: str | None,
    contributor: str | None,
    modified_after: str | None,
    modified_before: str | None
) -> str:
    """Build CQL query string from parameters."""
    conditions = []

    if query:
        # Escape quotes in query
        escaped_query = query.replace('"', '\\"')
        conditions.append(f'text ~ "{escaped_query}"')

    if space:
        conditions.append(f'space = "{space}"')

    if content_type:
        conditions.append(f'type = {content_type}')

    if label:
        conditions.append(f'label = "{label}"')

    if contributor:
        conditions.append(f'contributor = "{contributor}"')

    if modified_after:
        conditions.append(f'lastModified >= "{modified_after}"')

    if modified_before:
        conditions.append(f'lastModified <= "{modified_before}"')

    # Default to pages if no conditions
    if not conditions:
        conditions.append("type = page")

    return " AND ".join(conditions)


def format_compact(results: list[dict], query: str | None, base_url: str) -> str:
    """Format search results as compact output."""
    lines = []
    query_display = f'"{query}"' if query else "(all)"
    lines.append(f"SEARCH|{len(results)}|{query_display}")

    for r in results:
        space = r.get("space", "")
        content_type = r.get("type", "page")
        lines.append(f"HIT|{r['id']}|{r['title']}|{space}|{content_type}")

    return "\n".join(lines)


def format_text(results: list[dict], query: str | None, base_url: str) -> str:
    """Format search results as readable text."""
    lines = []
    query_display = f'"{query}"' if query else "(all)"
    lines.append(f"Search Results: {query_display} ({len(results)} found)")
    lines.append("")

    for i, r in enumerate(results, 1):
        space = r.get("space", "")
        content_type = r.get("type", "page")
        url = r.get("url", f"{base_url}/wiki/spaces/{space}/pages/{r['id']}")

        lines.append(f"{i}. {r['title']}")
        lines.append(f"   ID: {r['id']} | Space: {space} | Type: {content_type}")
        lines.append(f"   URL: {url}")
        lines.append("")

    return "\n".join(lines)


def format_json(results: list[dict], query: str | None, base_url: str) -> str:
    """Format search results as JSON."""
    output = {
        "query": query or "",
        "count": len(results),
        "results": results
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Search Confluence content"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Search text"
    )
    parser.add_argument(
        "--space", "-s",
        help="Limit search to specific space"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["page", "blogpost", "comment"],
        help="Content type filter"
    )
    parser.add_argument(
        "--label", "-l",
        help="Search for content with specific label"
    )
    parser.add_argument(
        "--contributor",
        help="Search by content contributor"
    )
    parser.add_argument(
        "--modified-after",
        help="Content modified after date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--modified-before",
        help="Content modified before date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum results (default: 25)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["compact", "text", "json"],
        default="compact",
        help="Output format (default: compact)"
    )

    args = parser.parse_args()

    # Validate - need at least one search criterion
    if not args.query and not args.label and not args.space and not args.contributor:
        parser.error("At least one search criterion required (query, --label, --space, or --contributor)")

    # Check environment
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
    if not base_url:
        print("ERROR: CONFLUENCE_BASE_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    # Initialize cache
    cache = ConfluenceCache()

    try:
        # Build CQL query
        cql = build_cql(
            args.query,
            args.space,
            args.type,
            args.label,
            args.contributor,
            args.modified_after,
            args.modified_before
        )

        # Execute search using v1 API (CQL search)
        encoded_cql = quote(cql)
        result = cache._api_request(
            f"/content/search?cql={encoded_cql}&limit={args.limit}",
            api_version="v1"
        )

        # Process results
        results = []
        for r in result.get("results", []):
            space_key = r.get("space", {}).get("key", "")
            page_id = r["id"]

            # Build URL
            if r.get("type") == "blogpost":
                url = f"{base_url}/wiki/spaces/{space_key}/blog/{page_id}"
            else:
                url = f"{base_url}/wiki/spaces/{space_key}/pages/{page_id}"

            results.append({
                "id": page_id,
                "title": r["title"],
                "space": space_key,
                "type": r.get("type", "page"),
                "url": url
            })

        if not results:
            print(f"No results found for: {args.query or '(criteria)'}", file=sys.stderr)
            sys.exit(0)

        # Format output
        if args.format == "compact":
            output = format_compact(results, args.query, base_url)
        elif args.format == "text":
            output = format_text(results, args.query, base_url)
        else:
            output = format_json(results, args.query, base_url)

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

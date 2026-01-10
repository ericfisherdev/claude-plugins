#!/usr/bin/env python3
"""
Shared Confluence cache module for confluence-tools plugin.

Caches space metadata, page hierarchies, labels, and other frequently-accessed
data to reduce API calls and improve performance.

Cache location: ~/.confluence-tools-cache.json

Usage:
    from confluence_cache import ConfluenceCache

    cache = ConfluenceCache()
    spaces = cache.get_spaces()  # Returns cached or fetches fresh
    cache.refresh_spaces()       # Force refresh
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import base64


# Cache expiry times (in hours)
CACHE_EXPIRY = {
    "spaces": 24,
    "space_pages": 4,      # Page tree for a space
    "page_content": 1,     # Individual page content
    "labels": 12,
    "users": 4,
    "page_ancestors": 24,  # Parent hierarchy rarely changes
}

DEFAULT_CACHE_PATH = Path.home() / ".confluence-tools-cache.json"


class ConfluenceCache:
    """Manages cached Confluence metadata for token-efficient operations."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self.cache = self._load_cache()
        self._base_url = os.environ.get("CONFLUENCE_BASE_URL", "")

    def _load_cache(self) -> dict:
        """Load cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"_meta": {"created": datetime.now().isoformat()}}
        return {"_meta": {"created": datetime.now().isoformat()}}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        self.cache["_meta"]["updated"] = datetime.now().isoformat()
        try:
            with open(self.cache_path, "w") as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache: {e}", file=sys.stderr)

    def _is_expired(self, cache_key: str) -> bool:
        """Check if a cache entry is expired."""
        if cache_key not in self.cache:
            return True
        entry = self.cache[cache_key]
        if "_cached_at" not in entry:
            return True

        cached_at = datetime.fromisoformat(entry["_cached_at"])
        # Extract base key for expiry lookup (e.g., "space_pages_DEV" -> "space_pages")
        base_key = cache_key.split("_")[0] + "_" + cache_key.split("_")[1] if "_" in cache_key else cache_key
        for expiry_key in CACHE_EXPIRY:
            if cache_key.startswith(expiry_key):
                expiry_hours = CACHE_EXPIRY[expiry_key]
                break
        else:
            expiry_hours = 24
        return datetime.now() - cached_at > timedelta(hours=expiry_hours)

    def _get_auth_header(self) -> str:
        """Generate Basic Auth header."""
        email = os.environ.get("CONFLUENCE_EMAIL")
        token = os.environ.get("CONFLUENCE_API_TOKEN")
        if not email or not token:
            raise EnvironmentError(
                "CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN environment variables required"
            )
        credentials = f"{email}:{token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _api_request(
        self,
        path: str,
        method: str = "GET",
        data: Optional[dict] = None,
        api_version: str = "v2"
    ) -> dict:
        """Make authenticated API request to Confluence.

        Args:
            path: API path (without base URL)
            method: HTTP method
            data: Request body data
            api_version: "v1" or "v2" (default v2 for modern API)
        """
        if not self._base_url:
            self._base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
        if not self._base_url:
            raise EnvironmentError("CONFLUENCE_BASE_URL environment variable required")

        # Build full URL based on API version
        if api_version == "v2":
            base = f"{self._base_url.rstrip('/')}/wiki/api/v2"
        else:
            base = f"{self._base_url.rstrip('/')}/wiki/rest/api"

        url = f"{base}{path}"
        req = Request(url, method=method)
        req.add_header("Authorization", self._get_auth_header())
        req.add_header("Accept", "application/json")

        if data:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode()

        try:
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"Confluence API error {e.code}: {error_body}")
        except URLError as e:
            raise ConnectionError(f"Failed to connect to Confluence: {e.reason}")

    # === Space Methods ===

    def get_spaces(self, force_refresh: bool = False) -> list[dict]:
        """Get list of spaces (cached)."""
        if force_refresh or self._is_expired("spaces"):
            self.refresh_spaces()
        return self.cache.get("spaces", {}).get("data", [])

    def refresh_spaces(self) -> list[dict]:
        """Fetch and cache spaces from Confluence."""
        spaces = []
        cursor = None

        while True:
            path = "/spaces?limit=100"
            if cursor:
                path += f"&cursor={cursor}"

            result = self._api_request(path)

            for s in result.get("results", []):
                spaces.append({
                    "id": s["id"],
                    "key": s["key"],
                    "name": s["name"],
                    "type": s.get("type", "global"),
                    "status": s.get("status", "current"),
                })

            # Check for more pages
            links = result.get("_links", {})
            if "next" not in links:
                break
            # Extract cursor from next link
            next_link = links["next"]
            if "cursor=" in next_link:
                cursor = next_link.split("cursor=")[1].split("&")[0]
            else:
                break

        self.cache["spaces"] = {
            "_cached_at": datetime.now().isoformat(),
            "data": spaces
        }
        self._save_cache()
        return spaces

    def get_space_by_key(self, key: str) -> Optional[dict]:
        """Get space by key from cache."""
        spaces = self.get_spaces()
        key_upper = key.upper()
        for s in spaces:
            if s["key"].upper() == key_upper:
                return s
        return None

    def get_space_id(self, key: str) -> Optional[str]:
        """Get space ID by key."""
        space = self.get_space_by_key(key)
        return space["id"] if space else None

    # === Page Methods ===

    def get_page(self, page_id: str, force_refresh: bool = False) -> Optional[dict]:
        """Get a page by ID (cached)."""
        cache_key = f"page_{page_id}"
        if not force_refresh and cache_key in self.cache:
            entry = self.cache[cache_key]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=CACHE_EXPIRY["page_content"]):
                    return entry.get("data")

        return self.refresh_page(page_id)

    def refresh_page(self, page_id: str) -> Optional[dict]:
        """Fetch and cache a page."""
        try:
            result = self._api_request(
                f"/pages/{page_id}?body-format=storage"
            )

            page = {
                "id": result["id"],
                "title": result["title"],
                "spaceId": result.get("spaceId", ""),
                "parentId": result.get("parentId", ""),
                "parentType": result.get("parentType", ""),
                "status": result.get("status", "current"),
                "createdAt": result.get("createdAt", ""),
                "version": result.get("version", {}).get("number", 1),
                "body": result.get("body", {}).get("storage", {}).get("value", ""),
            }

            cache_key = f"page_{page_id}"
            self.cache[cache_key] = {
                "_cached_at": datetime.now().isoformat(),
                "data": page
            }
            self._save_cache()
            return page
        except RuntimeError:
            return None

    def get_page_by_title(self, space_key: str, title: str) -> Optional[dict]:
        """Find a page by title in a space."""
        space_id = self.get_space_id(space_key)
        if not space_id:
            return None

        # Use CQL search
        encoded_title = quote(title)
        result = self._api_request(
            f"/pages?space-id={space_id}&title={encoded_title}&limit=1"
        )

        pages = result.get("results", [])
        if pages:
            return self.get_page(pages[0]["id"])
        return None

    def get_pages_in_space(
        self,
        space_key: str,
        parent_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> list[dict]:
        """Get pages in a space, optionally under a parent (cached)."""
        cache_key = f"space_pages_{space_key}_{parent_id or 'root'}"

        if not force_refresh and cache_key in self.cache:
            entry = self.cache[cache_key]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=CACHE_EXPIRY["space_pages"]):
                    return entry.get("data", [])

        return self.refresh_pages_in_space(space_key, parent_id)

    def refresh_pages_in_space(
        self,
        space_key: str,
        parent_id: Optional[str] = None
    ) -> list[dict]:
        """Fetch and cache pages in a space."""
        space_id = self.get_space_id(space_key)
        if not space_id:
            return []

        pages = []
        cursor = None

        while True:
            if parent_id:
                path = f"/pages/{parent_id}/children?limit=100"
            else:
                path = f"/spaces/{space_id}/pages?depth=root&limit=100"

            if cursor:
                path += f"&cursor={cursor}"

            result = self._api_request(path)

            for p in result.get("results", []):
                pages.append({
                    "id": p["id"],
                    "title": p["title"],
                    "parentId": p.get("parentId", ""),
                    "status": p.get("status", "current"),
                    "createdAt": p.get("createdAt", ""),
                })

            links = result.get("_links", {})
            if "next" not in links:
                break
            next_link = links["next"]
            if "cursor=" in next_link:
                cursor = next_link.split("cursor=")[1].split("&")[0]
            else:
                break

        cache_key = f"space_pages_{space_key}_{parent_id or 'root'}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": pages
        }
        self._save_cache()
        return pages

    def get_page_children(self, page_id: str, force_refresh: bool = False) -> list[dict]:
        """Get child pages of a page (cached)."""
        cache_key = f"page_children_{page_id}"

        if not force_refresh and cache_key in self.cache:
            entry = self.cache[cache_key]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=CACHE_EXPIRY["space_pages"]):
                    return entry.get("data", [])

        return self.refresh_page_children(page_id)

    def refresh_page_children(self, page_id: str) -> list[dict]:
        """Fetch and cache child pages."""
        pages = []
        cursor = None

        while True:
            path = f"/pages/{page_id}/children?limit=100"
            if cursor:
                path += f"&cursor={cursor}"

            result = self._api_request(path)

            for p in result.get("results", []):
                pages.append({
                    "id": p["id"],
                    "title": p["title"],
                    "status": p.get("status", "current"),
                    "createdAt": p.get("createdAt", ""),
                })

            links = result.get("_links", {})
            if "next" not in links:
                break
            next_link = links["next"]
            if "cursor=" in next_link:
                cursor = next_link.split("cursor=")[1].split("&")[0]
            else:
                break

        cache_key = f"page_children_{page_id}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": pages
        }
        self._save_cache()
        return pages

    def get_page_ancestors(self, page_id: str) -> list[dict]:
        """Get ancestors (parent chain) of a page."""
        cache_key = f"page_ancestors_{page_id}"

        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=CACHE_EXPIRY["page_ancestors"]):
                    return entry.get("data", [])

        # Fetch page with ancestors
        try:
            # Use v1 API for ancestors
            result = self._api_request(
                f"/content/{page_id}?expand=ancestors",
                api_version="v1"
            )

            ancestors = []
            for a in result.get("ancestors", []):
                ancestors.append({
                    "id": a["id"],
                    "title": a["title"],
                    "type": a.get("type", "page"),
                })

            self.cache[cache_key] = {
                "_cached_at": datetime.now().isoformat(),
                "data": ancestors
            }
            self._save_cache()
            return ancestors
        except RuntimeError:
            return []

    # === Label Methods ===

    def get_labels(self, page_id: str, force_refresh: bool = False) -> list[str]:
        """Get labels for a page (cached)."""
        cache_key = f"labels_{page_id}"

        if not force_refresh and cache_key in self.cache:
            entry = self.cache[cache_key]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=CACHE_EXPIRY["labels"]):
                    return entry.get("data", [])

        return self.refresh_labels(page_id)

    def refresh_labels(self, page_id: str) -> list[str]:
        """Fetch and cache labels for a page."""
        try:
            result = self._api_request(f"/pages/{page_id}/labels")
            labels = [l["name"] for l in result.get("results", [])]

            cache_key = f"labels_{page_id}"
            self.cache[cache_key] = {
                "_cached_at": datetime.now().isoformat(),
                "data": labels
            }
            self._save_cache()
            return labels
        except RuntimeError:
            return []

    # === User Methods ===

    def get_current_user(self) -> dict:
        """Get current authenticated user."""
        if "current_user" in self.cache:
            entry = self.cache["current_user"]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=CACHE_EXPIRY["users"]):
                    return entry.get("data", {})

        result = self._api_request("/user/current", api_version="v1")
        user = {
            "accountId": result.get("accountId", ""),
            "displayName": result.get("displayName", ""),
            "email": result.get("email", ""),
        }

        self.cache["current_user"] = {
            "_cached_at": datetime.now().isoformat(),
            "data": user
        }
        self._save_cache()
        return user

    # === Search Methods ===

    def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 25
    ) -> list[dict]:
        """Search for pages using CQL."""
        cql_parts = [f'type=page AND text~"{query}"']
        if space_key:
            cql_parts.append(f'space="{space_key}"')

        cql = " AND ".join(cql_parts)
        encoded_cql = quote(cql)

        result = self._api_request(
            f"/content/search?cql={encoded_cql}&limit={limit}",
            api_version="v1"
        )

        pages = []
        for p in result.get("results", []):
            pages.append({
                "id": p["id"],
                "title": p["title"],
                "space": p.get("space", {}).get("key", ""),
                "type": p.get("type", "page"),
                "_links": p.get("_links", {}),
            })

        return pages

    # === Utility Methods ===

    def invalidate_page(self, page_id: str) -> None:
        """Invalidate cache for a specific page."""
        keys_to_remove = [
            f"page_{page_id}",
            f"labels_{page_id}",
            f"page_children_{page_id}",
            f"page_ancestors_{page_id}",
        ]
        for key in keys_to_remove:
            if key in self.cache:
                del self.cache[key]
        self._save_cache()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache = {"_meta": {"created": datetime.now().isoformat()}}
        self._save_cache()

    def get_cache_info(self) -> dict:
        """Get cache metadata for debugging."""
        info = {"path": str(self.cache_path), "entries": {}}
        for key, value in self.cache.items():
            if key == "_meta":
                info["meta"] = value
            elif isinstance(value, dict) and "_cached_at" in value:
                data = value.get("data", [])
                if isinstance(data, list):
                    item_count = len(data)
                elif isinstance(data, dict):
                    item_count = len(data)
                else:
                    item_count = 1
                info["entries"][key] = {
                    "cached_at": value["_cached_at"],
                    "item_count": item_count
                }
        return info


# CLI interface for cache management
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Confluence cache management")
    parser.add_argument(
        "command",
        choices=["info", "clear", "refresh-spaces", "spaces"],
        help="Command to run"
    )
    args = parser.parse_args()

    cache = ConfluenceCache()

    if args.command == "info":
        info = cache.get_cache_info()
        print(json.dumps(info, indent=2))

    elif args.command == "clear":
        cache.clear_cache()
        print("Cache cleared")

    elif args.command == "refresh-spaces":
        print("Refreshing spaces...")
        spaces = cache.refresh_spaces()
        print(f"Cached {len(spaces)} spaces")

    elif args.command == "spaces":
        spaces = cache.get_spaces()
        if not spaces:
            print("No spaces found (run 'refresh-spaces' first)")
        else:
            print("Spaces:")
            for s in spaces:
                print(f"  {s['key']}: {s['name']} ({s['type']})")

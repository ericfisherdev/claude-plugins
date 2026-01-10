#!/usr/bin/env python3
"""
Shared Jira cache module for jira-tools plugin.

Caches project metadata, issue types, statuses, users, and other
frequently-accessed data to reduce API calls and improve performance.

Cache location: ~/.jira-tools-cache.json

Usage:
    from jira_cache import JiraCache

    cache = JiraCache()
    projects = cache.get_projects()  # Returns cached or fetches fresh
    cache.refresh_projects()         # Force refresh
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import base64


# Cache expiry times (in hours)
CACHE_EXPIRY = {
    "projects": 24,
    "issue_types": 24,
    "statuses": 24,
    "priorities": 24,
    "users": 4,
    "components": 12,
    "labels": 12,
    "sprints": 4,  # Sprint metadata
    # Issue cache categories (separated by sprint status)
    "issues_active_sprint": 1,   # Active sprint issues change frequently
    "issues_backlog": 12,        # Backlog issues change less often
    "issues_past_sprints": 24,   # Closed sprint issues rarely change
    "issues": 1,                 # Legacy/uncategorized (for backwards compat)
}

# Sprint state constants
SPRINT_STATE_ACTIVE = "active"
SPRINT_STATE_CLOSED = "closed"
SPRINT_STATE_FUTURE = "future"

# Issue category constants
ISSUE_CATEGORY_ACTIVE_SPRINT = "active_sprint"
ISSUE_CATEGORY_BACKLOG = "backlog"
ISSUE_CATEGORY_PAST_SPRINTS = "past_sprints"

DEFAULT_CACHE_PATH = Path.home() / ".jira-tools-cache.json"


class JiraCache:
    """Manages cached Jira metadata for token-efficient operations."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self.cache = self._load_cache()
        self._base_url = os.environ.get("JIRA_BASE_URL", "")

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
        expiry_hours = CACHE_EXPIRY.get(cache_key, 24)
        return datetime.now() - cached_at > timedelta(hours=expiry_hours)

    def _get_auth_header(self) -> str:
        """Generate Basic Auth header."""
        email = os.environ.get("JIRA_EMAIL")
        token = os.environ.get("JIRA_API_TOKEN")
        if not email or not token:
            raise EnvironmentError(
                "JIRA_EMAIL and JIRA_API_TOKEN environment variables required"
            )
        credentials = f"{email}:{token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _api_request(self, path: str, method: str = "GET", data: Optional[dict] = None) -> dict:
        """Make authenticated API request to Jira."""
        if not self._base_url:
            self._base_url = os.environ.get("JIRA_BASE_URL", "")
        if not self._base_url:
            raise EnvironmentError("JIRA_BASE_URL environment variable required")

        url = urljoin(self._base_url, path)
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
            raise RuntimeError(f"Jira API error {e.code}: {error_body}")
        except URLError as e:
            raise ConnectionError(f"Failed to connect to Jira: {e.reason}")

    # === Project Methods ===

    def get_projects(self, force_refresh: bool = False) -> list[dict]:
        """Get list of projects (cached)."""
        if force_refresh or self._is_expired("projects"):
            self.refresh_projects()
        return self.cache.get("projects", {}).get("data", [])

    def refresh_projects(self) -> list[dict]:
        """Fetch and cache projects from Jira."""
        result = self._api_request("/rest/api/3/project/search?maxResults=100")
        projects = []
        for p in result.get("values", []):
            projects.append({
                "id": p["id"],
                "key": p["key"],
                "name": p["name"],
            })
        self.cache["projects"] = {
            "_cached_at": datetime.now().isoformat(),
            "data": projects
        }
        self._save_cache()
        return projects

    def get_project_by_key(self, key: str) -> Optional[dict]:
        """Get project by key from cache."""
        projects = self.get_projects()
        key_upper = key.upper()
        for p in projects:
            if p["key"].upper() == key_upper:
                return p
        return None

    # === Issue Type Methods ===

    def get_issue_types(self, project_key: str, force_refresh: bool = False) -> list[dict]:
        """Get issue types for a project (cached)."""
        cache_key = f"issue_types_{project_key}"
        if force_refresh or self._is_expired(cache_key):
            self.refresh_issue_types(project_key)
        return self.cache.get(cache_key, {}).get("data", [])

    def refresh_issue_types(self, project_key: str) -> list[dict]:
        """Fetch and cache issue types for a project."""
        result = self._api_request(f"/rest/api/3/issue/createmeta/{project_key}/issuetypes")
        issue_types = []
        for it in result.get("issueTypes", []):
            issue_types.append({
                "id": it["id"],
                "name": it["name"],
                "subtask": it.get("subtask", False),
            })
        cache_key = f"issue_types_{project_key}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": issue_types
        }
        self._save_cache()
        return issue_types

    def get_issue_type_by_name(self, project_key: str, name: str) -> Optional[dict]:
        """Get issue type by name from cache."""
        issue_types = self.get_issue_types(project_key)
        name_lower = name.lower()
        for it in issue_types:
            if it["name"].lower() == name_lower:
                return it
        return None

    # === Status Methods ===

    def get_statuses(self, project_key: str, force_refresh: bool = False) -> list[dict]:
        """Get statuses for a project (cached)."""
        cache_key = f"statuses_{project_key}"
        if force_refresh or self._is_expired(cache_key):
            self.refresh_statuses(project_key)
        return self.cache.get(cache_key, {}).get("data", [])

    def refresh_statuses(self, project_key: str) -> list[dict]:
        """Fetch and cache statuses for a project."""
        result = self._api_request(f"/rest/api/3/project/{project_key}/statuses")
        statuses = []
        seen = set()
        for issue_type in result:
            for s in issue_type.get("statuses", []):
                if s["id"] not in seen:
                    statuses.append({
                        "id": s["id"],
                        "name": s["name"],
                        "category": s.get("statusCategory", {}).get("name", ""),
                    })
                    seen.add(s["id"])
        cache_key = f"statuses_{project_key}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": statuses
        }
        self._save_cache()
        return statuses

    # === Priority Methods ===

    def get_priorities(self, force_refresh: bool = False) -> list[dict]:
        """Get priorities (cached)."""
        if force_refresh or self._is_expired("priorities"):
            self.refresh_priorities()
        return self.cache.get("priorities", {}).get("data", [])

    def refresh_priorities(self) -> list[dict]:
        """Fetch and cache priorities."""
        result = self._api_request("/rest/api/3/priority")
        priorities = []
        for p in result:
            priorities.append({
                "id": p["id"],
                "name": p["name"],
            })
        self.cache["priorities"] = {
            "_cached_at": datetime.now().isoformat(),
            "data": priorities
        }
        self._save_cache()
        return priorities

    def get_priority_by_name(self, name: str) -> Optional[dict]:
        """Get priority by name from cache."""
        priorities = self.get_priorities()
        name_lower = name.lower()
        for p in priorities:
            if p["name"].lower() == name_lower:
                return p
        return None

    # === User Methods ===

    def get_users(self, project_key: str, force_refresh: bool = False) -> list[dict]:
        """Get assignable users for a project (cached)."""
        cache_key = f"users_{project_key}"
        if force_refresh or self._is_expired(cache_key):
            self.refresh_users(project_key)
        return self.cache.get(cache_key, {}).get("data", [])

    def refresh_users(self, project_key: str) -> list[dict]:
        """Fetch and cache assignable users for a project."""
        result = self._api_request(
            f"/rest/api/3/user/assignable/search?project={project_key}&maxResults=100"
        )
        users = []
        for u in result:
            users.append({
                "accountId": u["accountId"],
                "displayName": u.get("displayName", ""),
                "emailAddress": u.get("emailAddress", ""),
            })
        cache_key = f"users_{project_key}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": users
        }
        self._save_cache()
        return users

    def get_user_by_name(self, project_key: str, name: str) -> Optional[dict]:
        """Get user by display name from cache."""
        users = self.get_users(project_key)
        name_lower = name.lower()
        for u in users:
            if name_lower in u["displayName"].lower():
                return u
        return None

    def get_current_user(self) -> dict:
        """Get current authenticated user."""
        if "current_user" in self.cache and not self._is_expired("current_user"):
            return self.cache["current_user"]["data"]

        result = self._api_request("/rest/api/3/myself")
        user = {
            "accountId": result["accountId"],
            "displayName": result.get("displayName", ""),
            "emailAddress": result.get("emailAddress", ""),
        }
        self.cache["current_user"] = {
            "_cached_at": datetime.now().isoformat(),
            "data": user
        }
        self._save_cache()
        return user

    # === Component Methods ===

    def get_components(self, project_key: str, force_refresh: bool = False) -> list[dict]:
        """Get components for a project (cached)."""
        cache_key = f"components_{project_key}"
        if force_refresh or self._is_expired(cache_key):
            self.refresh_components(project_key)
        return self.cache.get(cache_key, {}).get("data", [])

    def refresh_components(self, project_key: str) -> list[dict]:
        """Fetch and cache components for a project."""
        result = self._api_request(f"/rest/api/3/project/{project_key}/components")
        components = []
        for c in result:
            components.append({
                "id": c["id"],
                "name": c["name"],
            })
        cache_key = f"components_{project_key}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": components
        }
        self._save_cache()
        return components

    # === Label Methods ===

    def get_labels(self, force_refresh: bool = False) -> list[str]:
        """Get all labels (cached)."""
        if force_refresh or self._is_expired("labels"):
            self.refresh_labels()
        return self.cache.get("labels", {}).get("data", [])

    def refresh_labels(self) -> list[str]:
        """Fetch and cache labels."""
        result = self._api_request("/rest/api/3/label?maxResults=1000")
        labels = result.get("values", [])
        self.cache["labels"] = {
            "_cached_at": datetime.now().isoformat(),
            "data": labels
        }
        self._save_cache()
        return labels

    # === Sprint Methods ===

    def get_board_for_project(self, project_key: str, force_refresh: bool = False) -> Optional[dict]:
        """Get the primary board for a project (cached)."""
        cache_key = f"board_{project_key}"
        if not force_refresh and cache_key in self.cache:
            entry = self.cache[cache_key]
            if "_cached_at" in entry:
                cached_at = datetime.fromisoformat(entry["_cached_at"])
                if datetime.now() - cached_at <= timedelta(hours=24):
                    return entry.get("data")

        # Fetch boards for the project
        try:
            result = self._api_request(
                f"/rest/agile/1.0/board?projectKeyOrId={project_key}&maxResults=1"
            )
            boards = result.get("values", [])
            if boards:
                board = {
                    "id": boards[0]["id"],
                    "name": boards[0]["name"],
                    "type": boards[0].get("type", ""),
                }
                self.cache[cache_key] = {
                    "_cached_at": datetime.now().isoformat(),
                    "data": board
                }
                self._save_cache()
                return board
        except RuntimeError:
            pass  # Board API may not be available
        return None

    def get_sprints(self, project_key: str, state: Optional[str] = None, force_refresh: bool = False) -> list[dict]:
        """Get sprints for a project (cached).

        Args:
            project_key: Project key
            state: Filter by state ('active', 'closed', 'future') or None for all
            force_refresh: Force refresh from API
        """
        cache_key = f"sprints_{project_key}"
        if not force_refresh and not self._is_expired(cache_key):
            sprints = self.cache.get(cache_key, {}).get("data", [])
            if state:
                return [s for s in sprints if s.get("state") == state]
            return sprints

        return self.refresh_sprints(project_key, state)

    def refresh_sprints(self, project_key: str, state_filter: Optional[str] = None) -> list[dict]:
        """Fetch and cache sprints for a project."""
        board = self.get_board_for_project(project_key)
        if not board:
            return []

        # Fetch all sprints (active, closed, future)
        sprints = []
        try:
            # Get active and future sprints
            for state in ["active", "future", "closed"]:
                result = self._api_request(
                    f"/rest/agile/1.0/board/{board['id']}/sprint?state={state}&maxResults=50"
                )
                for s in result.get("values", []):
                    sprints.append({
                        "id": s["id"],
                        "name": s["name"],
                        "state": s.get("state", ""),
                        "startDate": s.get("startDate", ""),
                        "endDate": s.get("endDate", ""),
                        "completeDate": s.get("completeDate", ""),
                    })
        except RuntimeError:
            pass  # Sprint API may fail

        cache_key = f"sprints_{project_key}"
        self.cache[cache_key] = {
            "_cached_at": datetime.now().isoformat(),
            "data": sprints
        }
        self._save_cache()

        if state_filter:
            return [s for s in sprints if s.get("state") == state_filter]
        return sprints

    def get_active_sprint(self, project_key: str) -> Optional[dict]:
        """Get the currently active sprint for a project."""
        sprints = self.get_sprints(project_key, state=SPRINT_STATE_ACTIVE)
        return sprints[0] if sprints else None

    def get_sprint_by_id(self, project_key: str, sprint_id: int) -> Optional[dict]:
        """Get a specific sprint by ID from cache."""
        sprints = self.get_sprints(project_key)
        for s in sprints:
            if s["id"] == sprint_id:
                return s
        return None

    def _determine_issue_category(self, issue: dict) -> str:
        """Determine which cache category an issue belongs to based on sprint status."""
        sprint_info = issue.get("sprint")
        if not sprint_info:
            return ISSUE_CATEGORY_BACKLOG

        # If sprint info is provided as dict with state
        if isinstance(sprint_info, dict):
            state = sprint_info.get("state", "")
            if state == SPRINT_STATE_ACTIVE:
                return ISSUE_CATEGORY_ACTIVE_SPRINT
            elif state == SPRINT_STATE_CLOSED:
                return ISSUE_CATEGORY_PAST_SPRINTS
            else:
                return ISSUE_CATEGORY_BACKLOG

        # If sprint info is just an ID or name, treat as active
        return ISSUE_CATEGORY_ACTIVE_SPRINT

    # === Issue Cache Methods (Sprint-Aware) ===

    def _get_issue_cache_key(self, category: str) -> str:
        """Get the cache key for an issue category."""
        return f"issues_{category}"

    def _get_category_expiry(self, category: str) -> int:
        """Get expiry hours for an issue category."""
        cache_key = f"issues_{category}"
        return CACHE_EXPIRY.get(cache_key, CACHE_EXPIRY.get("issues", 1))

    def get_cached_issue(self, issue_key: str) -> Optional[dict]:
        """Get a cached issue by key, searching all categories."""
        issue_key = issue_key.upper()

        # Search all issue categories
        for category in [ISSUE_CATEGORY_ACTIVE_SPRINT, ISSUE_CATEGORY_BACKLOG, ISSUE_CATEGORY_PAST_SPRINTS]:
            cache_key = self._get_issue_cache_key(category)
            if cache_key not in self.cache:
                continue
            issues = self.cache[cache_key].get("data", {})
            issue = issues.get(issue_key)
            if issue:
                # Check if expired based on category TTL
                cached_at = datetime.fromisoformat(issue.get("_cached_at", "2000-01-01"))
                expiry_hours = self._get_category_expiry(category)
                if datetime.now() - cached_at <= timedelta(hours=expiry_hours):
                    return issue

        # Fallback: check legacy "issues" cache for backwards compatibility
        if "issues" in self.cache:
            issues = self.cache["issues"].get("data", {})
            issue = issues.get(issue_key)
            if issue:
                cached_at = datetime.fromisoformat(issue.get("_cached_at", "2000-01-01"))
                if datetime.now() - cached_at <= timedelta(hours=1):
                    return issue

        return None

    def set_cached_issue(self, issue_key: str, issue_data: dict, category: Optional[str] = None) -> None:
        """Cache a single issue in the appropriate category.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            issue_data: Issue data dict (should include 'sprint' field for auto-categorization)
            category: Explicit category ('active_sprint', 'backlog', 'past_sprints') or None for auto
        """
        if category is None:
            category = self._determine_issue_category(issue_data)

        cache_key = self._get_issue_cache_key(category)
        if cache_key not in self.cache:
            self.cache[cache_key] = {"_cached_at": datetime.now().isoformat(), "data": {}}

        issue_data["_cached_at"] = datetime.now().isoformat()
        issue_data["_category"] = category
        self.cache[cache_key]["data"][issue_key.upper()] = issue_data
        self.cache[cache_key]["_cached_at"] = datetime.now().isoformat()

        # Remove from other categories to avoid duplicates
        self._remove_issue_from_other_categories(issue_key.upper(), category)
        self._save_cache()

    def _remove_issue_from_other_categories(self, issue_key: str, keep_category: str) -> None:
        """Remove an issue from all categories except the specified one."""
        for category in [ISSUE_CATEGORY_ACTIVE_SPRINT, ISSUE_CATEGORY_BACKLOG, ISSUE_CATEGORY_PAST_SPRINTS]:
            if category == keep_category:
                continue
            cache_key = self._get_issue_cache_key(category)
            if cache_key in self.cache and issue_key in self.cache[cache_key].get("data", {}):
                del self.cache[cache_key]["data"][issue_key]

    def set_cached_issues(self, issues: list[dict], category: Optional[str] = None) -> None:
        """Batch cache multiple issues.

        Args:
            issues: List of issue data dicts
            category: Explicit category for all issues, or None to auto-categorize each
        """
        now = datetime.now().isoformat()
        categorized: dict[str, list[tuple[str, dict]]] = {
            ISSUE_CATEGORY_ACTIVE_SPRINT: [],
            ISSUE_CATEGORY_BACKLOG: [],
            ISSUE_CATEGORY_PAST_SPRINTS: [],
        }

        for issue in issues:
            key = issue.get("key", "").upper()
            if not key:
                continue
            issue_category = category if category else self._determine_issue_category(issue)
            issue["_cached_at"] = now
            issue["_category"] = issue_category
            categorized[issue_category].append((key, issue))

        # Store issues in their respective categories
        for cat, items in categorized.items():
            if not items:
                continue
            cache_key = self._get_issue_cache_key(cat)
            if cache_key not in self.cache:
                self.cache[cache_key] = {"_cached_at": now, "data": {}}
            for key, issue in items:
                self.cache[cache_key]["data"][key] = issue
                # Remove from other categories
                self._remove_issue_from_other_categories(key, cat)
            self.cache[cache_key]["_cached_at"] = now

        self._save_cache()

    def get_cached_issues(
        self,
        project_key: Optional[str] = None,
        category: Optional[str] = None
    ) -> list[dict]:
        """Get cached issues, optionally filtered by project and/or category.

        Args:
            project_key: Filter by project key
            category: Filter by category ('active_sprint', 'backlog', 'past_sprints')
        """
        result = []
        now = datetime.now()

        categories = [category] if category else [
            ISSUE_CATEGORY_ACTIVE_SPRINT,
            ISSUE_CATEGORY_BACKLOG,
            ISSUE_CATEGORY_PAST_SPRINTS
        ]

        for cat in categories:
            cache_key = self._get_issue_cache_key(cat)
            if cache_key not in self.cache:
                continue
            issues = self.cache[cache_key].get("data", {})
            expiry_hours = self._get_category_expiry(cat)

            for key, issue in issues.items():
                # Skip expired issues
                cached_at = datetime.fromisoformat(issue.get("_cached_at", "2000-01-01"))
                if now - cached_at > timedelta(hours=expiry_hours):
                    continue
                # Filter by project if specified
                if project_key and not key.startswith(project_key.upper() + "-"):
                    continue
                result.append(issue)

        return result

    def get_backlog_issues(self, project_key: Optional[str] = None) -> list[dict]:
        """Get cached backlog issues."""
        return self.get_cached_issues(project_key, category=ISSUE_CATEGORY_BACKLOG)

    def get_active_sprint_issues(self, project_key: Optional[str] = None) -> list[dict]:
        """Get cached active sprint issues."""
        return self.get_cached_issues(project_key, category=ISSUE_CATEGORY_ACTIVE_SPRINT)

    def get_past_sprint_issues(self, project_key: Optional[str] = None) -> list[dict]:
        """Get cached past sprint issues."""
        return self.get_cached_issues(project_key, category=ISSUE_CATEGORY_PAST_SPRINTS)

    def update_cached_issue_fields(self, issue_key: str, fields: dict) -> bool:
        """Update specific fields of a cached issue. Returns True if updated."""
        issue_key = issue_key.upper()

        # Find the issue in any category
        for category in [ISSUE_CATEGORY_ACTIVE_SPRINT, ISSUE_CATEGORY_BACKLOG, ISSUE_CATEGORY_PAST_SPRINTS]:
            cache_key = self._get_issue_cache_key(category)
            if cache_key not in self.cache:
                continue
            issues = self.cache[cache_key].get("data", {})
            if issue_key not in issues:
                continue

            issue = issues[issue_key]
            # Update fields
            for field, value in fields.items():
                if field not in ("_cached_at", "_category"):
                    issue[field] = value
            issue["_cached_at"] = datetime.now().isoformat()

            # Check if category should change based on sprint update
            if "sprint" in fields:
                new_category = self._determine_issue_category(issue)
                if new_category != category:
                    # Move to new category
                    del issues[issue_key]
                    self.set_cached_issue(issue_key, issue, new_category)
                    return True

            self._save_cache()
            return True

        return False

    def move_issues_to_past_sprints(self, sprint_id: int, project_key: str) -> int:
        """Move all issues from a sprint to past_sprints category when sprint closes.

        Returns count of issues moved.
        """
        moved = 0
        cache_key = self._get_issue_cache_key(ISSUE_CATEGORY_ACTIVE_SPRINT)
        if cache_key not in self.cache:
            return 0

        issues = self.cache[cache_key].get("data", {})
        to_move = []

        for key, issue in issues.items():
            if not key.startswith(project_key.upper() + "-"):
                continue
            sprint_info = issue.get("sprint")
            if isinstance(sprint_info, dict) and sprint_info.get("id") == sprint_id:
                to_move.append((key, issue))
            elif sprint_info == sprint_id:
                to_move.append((key, issue))

        for key, issue in to_move:
            # Update sprint state to closed
            if isinstance(issue.get("sprint"), dict):
                issue["sprint"]["state"] = SPRINT_STATE_CLOSED
            # Move to past sprints
            del issues[key]
            self.set_cached_issue(key, issue, ISSUE_CATEGORY_PAST_SPRINTS)
            moved += 1

        if moved:
            self._save_cache()
        return moved

    def clear_cached_issues(
        self,
        project_key: Optional[str] = None,
        category: Optional[str] = None
    ) -> int:
        """Clear cached issues, optionally filtered by project and/or category.

        Returns count of issues cleared.
        """
        count = 0
        categories = [category] if category else [
            ISSUE_CATEGORY_ACTIVE_SPRINT,
            ISSUE_CATEGORY_BACKLOG,
            ISSUE_CATEGORY_PAST_SPRINTS
        ]

        for cat in categories:
            cache_key = self._get_issue_cache_key(cat)
            if cache_key not in self.cache:
                continue

            if project_key:
                # Clear only issues for this project
                issues = self.cache[cache_key].get("data", {})
                prefix = project_key.upper() + "-"
                to_remove = [k for k in issues if k.startswith(prefix)]
                for k in to_remove:
                    del issues[k]
                count += len(to_remove)
            else:
                # Clear all in this category
                count += len(self.cache[cache_key].get("data", {}))
                self.cache[cache_key] = {"_cached_at": datetime.now().isoformat(), "data": {}}

        # Also clear legacy cache for backwards compatibility
        if "issues" in self.cache and not category:
            if project_key:
                issues = self.cache["issues"].get("data", {})
                prefix = project_key.upper() + "-"
                to_remove = [k for k in issues if k.startswith(prefix)]
                for k in to_remove:
                    del issues[k]
                count += len(to_remove)
            else:
                count += len(self.cache["issues"].get("data", {}))
                del self.cache["issues"]

        self._save_cache()
        return count

    # === Utility Methods ===

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
                    "expired": self._is_expired(key),
                    "item_count": item_count
                }
        return info


# CLI interface for cache management
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Jira cache management")
    parser.add_argument(
        "command",
        choices=["info", "clear", "refresh", "clear-issues", "sprints", "close-sprint"],
        help="Command to run"
    )
    parser.add_argument("--project", "-p", help="Project key for project-specific operations")
    parser.add_argument(
        "--category", "-c",
        choices=["active_sprint", "backlog", "past_sprints"],
        help="Issue category filter for clear-issues"
    )
    parser.add_argument("--sprint-id", "-s", type=int, help="Sprint ID for close-sprint command")
    args = parser.parse_args()

    cache = JiraCache()

    if args.command == "info":
        info = cache.get_cache_info()
        print(json.dumps(info, indent=2))

    elif args.command == "clear":
        cache.clear_cache()
        print("Cache cleared")

    elif args.command == "clear-issues":
        count = cache.clear_cached_issues(args.project, args.category)
        filters = []
        if args.project:
            filters.append(f"project {args.project}")
        if args.category:
            filters.append(f"category {args.category}")
        filter_str = f" ({', '.join(filters)})" if filters else ""
        print(f"Cleared {count} cached issues{filter_str}")

    elif args.command == "sprints":
        if not args.project:
            print("Error: --project/-p required for sprints command", file=sys.stderr)
            sys.exit(1)
        sprints = cache.get_sprints(args.project, force_refresh=True)
        if not sprints:
            print(f"No sprints found for project {args.project}")
        else:
            print(f"Sprints for {args.project}:")
            for s in sprints:
                state_icon = {"active": "*", "closed": "-", "future": "+"}
                icon = state_icon.get(s["state"], "?")
                print(f"  [{icon}] {s['id']}: {s['name']} ({s['state']})")
            print("\nLegend: * active, + future, - closed")

    elif args.command == "close-sprint":
        if not args.project or not args.sprint_id:
            print("Error: --project/-p and --sprint-id/-s required for close-sprint", file=sys.stderr)
            sys.exit(1)
        count = cache.move_issues_to_past_sprints(args.sprint_id, args.project)
        print(f"Moved {count} issues from sprint {args.sprint_id} to past_sprints cache")

    elif args.command == "refresh":
        print("Refreshing cache...")
        cache.refresh_projects()
        cache.refresh_priorities()
        cache.refresh_labels()
        if args.project:
            cache.refresh_issue_types(args.project)
            cache.refresh_statuses(args.project)
            cache.refresh_users(args.project)
            cache.refresh_components(args.project)
            cache.refresh_sprints(args.project)
        print("Cache refreshed")

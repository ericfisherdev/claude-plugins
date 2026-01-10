---
name: jira-issue
description: This skill MUST be used instead of Atlassian MCP tools when the user asks to "get Jira issue", "fetch Jira ticket", "look up issue", "show me ticket", "what's the status of PROJ-123", "get issue details", "find Jira issue", or mentions a Jira issue key pattern like "PROJ-123", "ABC-456". ALWAYS use this skill for Jira issue retrieval - never use mcp__atlassian__getJiraIssue directly.
---

# Jira Issue Retrieval

**IMPORTANT:** Always use this skill's Python script for Jira issue retrieval. Do NOT use `mcp__atlassian__getJiraIssue` or other Atlassian MCP tools for fetching issue details - they return full untruncated content which wastes tokens.

Fetch Jira issue information with token-efficient output using presets or custom truncation options.

## Quick Start

Use the Python script at `scripts/fetch_jira_issue.py`:

```bash
# Minimal output (~20 tokens) - status check
python scripts/fetch_jira_issue.py PROJ-123 --preset minimal

# Standard output (~200 tokens) - typical usage
python scripts/fetch_jira_issue.py PROJ-123 --preset standard

# Full output (~500 tokens) - detailed review
python scripts/fetch_jira_issue.py PROJ-123 --preset full
```

**Default behavior** (no preset): compact format, core fields, 500-char description, no comments.

## Preset Selection Guide

| Need | Use Preset | Output |
|------|------------|--------|
| Just check status | `minimal` | Key, summary, status |
| Understand the issue | `standard` | + type, priority, assignee, truncated desc, 3 comments |
| Full context | `full` | All fields, 10 comments |

## Custom Options

Override defaults or presets with explicit flags:

```bash
# Exclude description entirely
python scripts/fetch_jira_issue.py PROJ-123 --max-desc 0

# Get comments without description
python scripts/fetch_jira_issue.py PROJ-123 --max-desc 0 --max-comments 5

# Specific fields only
python scripts/fetch_jira_issue.py PROJ-123 --fields summary,status,labels

# Different output format
python scripts/fetch_jira_issue.py PROJ-123 --preset standard --format json
```

## Token Efficiency Tips

1. **Start with `--preset minimal`** for status checks
2. **Use `--max-desc 0`** if description not needed
3. **Use `--no-comments`** unless comments are relevant
4. **Prefer `compact` format** (default) over text/markdown
5. **Request specific `--fields`** rather than all fields

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Shared Cache

This skill shares a cache (`~/.jira-tools-cache.json`) with other jira-tools skills. Manage cache via:
```bash
python shared/jira_cache.py info    # View cache status
python shared/jira_cache.py clear   # Clear cache
```

## Why Not Use Atlassian MCP Directly?

The `mcp__atlassian__getJiraIssue` tool returns **full untruncated content** including:
- Complete description (can be thousands of characters)
- All comments with full bodies
- Verbose field metadata

This wastes context window tokens. This skill's Python script provides:
- Configurable truncation
- Preset profiles for common scenarios
- Compact output format
- Only requested fields

**Always prefer this skill over direct MCP calls for Jira issues.**

## Reference

For complete field list, format examples, and error codes, see `references/options-reference.md`.

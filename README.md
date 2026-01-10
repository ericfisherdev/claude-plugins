# ericfisherdev-plugins

QOL plugins for Claude Code by ericfisherdev.

## Installation

Add this marketplace to Claude Code:

```bash
claude plugins:add https://github.com/ericfisherdev/claude-plugins
```

Or install individual plugins:

```bash
claude plugins:add ericfisherdev-plugins/jira-tools
```

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [jira-tools](#jira-tools) | Jira integration tools for token-efficient issue retrieval with truncation options | 1.0.0 |
| [confluence-tools](#confluence-tools) | Confluence integration tools for token-efficient page management with caching | 1.0.0 |

---

## Plugin Details

### jira-tools

Jira integration tools for fetching and managing issue information efficiently. Uses shared caching to reduce API calls and provides token-efficient output.

**Skills:**

| Skill | Description |
|-------|-------------|
| `/jira-issue` | Fetch single issue details with preset-based truncation |
| `/backlog-summary` | Get token-efficient summary of multiple issues with sprint-aware caching |
| `/create-issue` | Create Jira issues with cached metadata lookups |
| `/update-issue` | Update issues (status, assignee, labels, comments) |
| `/issue-analysis` | Analyze an issue and create implementation plans |
| `/analyze-backlog` | Auto-analyze top 3 unanalyzed backlog issues |

**Features:**
- Token-efficient output with configurable truncation
- Preset profiles (minimal, standard, full) for common use cases
- Sprint-aware caching with different TTLs per category
- Shared cache for metadata (users, priorities, components)
- Human-readable names instead of IDs

**Usage Examples:**

```bash
# Fetch issue with minimal output (~20 tokens)
/jira-issue PROJ-123 --preset minimal

# Get backlog summary
/backlog-summary PROJ --scope backlog

# Create a bug
/create-issue --project PROJ --type Bug --summary "Login fails"

# Update issue status
/update-issue PROJ-123 --status "In Progress"

# Analyze an issue for implementation
/issue-analysis PROJ-123

# Auto-analyze unanalyzed backlog items
/analyze-backlog PROJ
```

**Requirements:**
- Environment variables: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`

**Cache Location:**
```
~/.jira-tools-cache.json
```

---

### confluence-tools

Confluence integration tools for managing wiki pages efficiently. Uses shared caching to reduce API calls and provides token-efficient output.

**Skills:**

| Skill | Description |
|-------|-------------|
| `/confluence-page` | Fetch single page details with preset-based truncation |
| `/list-pages` | List pages in a space or under a parent with tree view |
| `/create-page` | Create Confluence pages with storage format support |
| `/update-page` | Update pages (title, body, labels) with version management |
| `/create-folder` | Create folder-like pages for organization |
| `/search-content` | Search Confluence using CQL queries |

**Features:**
- Token-efficient output with configurable truncation
- Preset profiles (minimal, standard, full) for common use cases
- Shared cache for spaces, pages, and labels
- Automatic version management for updates
- CQL-based search with multiple filters

**Usage Examples:**

```bash
# Fetch page with minimal output
/confluence-page 123456 --preset minimal

# List pages in a space as tree
/list-pages --space DEV --depth 2 --format tree

# Create a new page
/create-page --space DEV --title "API Docs" --body "<p>Content here</p>"

# Update page content
/update-page 123456 --body "<p>Updated content</p>"

# Create folder structure
/create-folder --space DEV --title "Documentation"

# Search for pages
/search-content "authentication" --space DEV
```

**Requirements:**
- Environment variables: `CONFLUENCE_BASE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`

**Cache Location:**
```
~/.confluence-tools-cache.json
```

---

## Contributing

To add a new plugin:

1. Create a directory under `plugins/{plugin-name}/`
2. Add a `plugin.json` manifest in `plugins/{plugin-name}/.claude-plugin/`
3. Add commands, agents, skills, or hooks as needed
4. Register the plugin in `.claude-plugin/marketplace.json`
5. Document the plugin in this README

## License

MIT

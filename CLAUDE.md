# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code plugin marketplace repository (`ericfisherdev-plugins`) containing QOL plugins by ericfisherdev. Plugins extend Claude Code's functionality through commands, agents, skills, and hooks.

## Architecture

```
.claude-plugin/
├── marketplace.json          # Plugin registry (lists all available plugins)
└── plugins/
    └── {plugin-name}/
        ├── .claude-plugin/
        │   └── plugin.json   # Plugin manifest (name, version, description)
        ├── commands/         # Slash commands (*.md files with YAML frontmatter)
        ├── agents/           # Subagents (*.md files)
        ├── skills/           # Skills (*.md files)
        └── hooks/            # Event hooks (*.md files)
```

### Plugin Registration

All plugins must be registered in `.claude-plugin/marketplace.json` with:
- `name`: Plugin identifier
- `source`: Relative path to plugin directory
- `description`: Brief description
- `version`: Semantic version
- `keywords`: Searchable tags

### Versioning

Version numbers must be incremented for every commit that modifies a plugin:

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Skill updates (bug fixes, improvements) | +0.0.1 | 1.3.0 → 1.3.1 |
| New skills added | +0.1.0 | 1.3.1 → 1.4.0 |

Update versions in all three locations:
1. `plugins/{plugin-name}/.claude-plugin/plugin.json`
2. `.claude-plugin/marketplace.json`
3. `README.md` (version table)

### Command Structure

Commands are markdown files with YAML frontmatter:
```yaml
---
name: command-name
description: 'Brief description shown to users'
argument-hint: '[optional-args] [--flags]'
---

# Command instructions in markdown
```

## Current Plugins

### claudefluence
Publishes local markdown documents to Confluence with cached space configurations.
- Location: `.claude-plugin/plugins/claudefluence/`
- Command: `/claudefluence:publish`
- Cache: `.claudefluence/claudefluence-{SPACE_KEY}-cache.yml`

Requires Atlassian MCP server integration for Confluence API access.

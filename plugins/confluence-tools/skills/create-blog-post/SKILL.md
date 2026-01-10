---
name: create-blog-post
description: This skill MUST be used when the user asks to "create a blog post", "add a blog entry", "write a blog in Confluence", "publish a blog post", "create a Confluence blog", or otherwise requests creating new blog posts in Confluence. ALWAYS use this skill for Confluence blog post creation.
---

# Create Confluence Blog Post

**IMPORTANT:** Always use this skill's Python script for creating Confluence blog posts. Blog posts are date-stamped entries that appear in a space's blog section, separate from regular pages.

## Markdown Content Handling

**CRITICAL:** When uploading markdown content to Confluence, you MUST use the `--markdown` flag:

- **Files with `.md` extension** → ALWAYS add `--markdown`
- **Content containing markdown syntax** (headers with #, lists with -, code blocks with ```) → ALWAYS add `--markdown`
- **User asks to upload/publish a markdown file** → ALWAYS add `--markdown`

Without the `--markdown` flag, markdown content will appear as raw unformatted text in Confluence.

## Quick Start

Use the Python script at `scripts/create_confluence_blog_post.py`:

```bash
# Create blog post in a space
python scripts/create_confluence_blog_post.py --space DEV --title "Sprint 42 Retrospective"

# Create with content
python scripts/create_confluence_blog_post.py --space DEV --title "Release Notes v2.0" \
  --body "<p>We're excited to announce version 2.0!</p>"

# Create from markdown file
python scripts/create_confluence_blog_post.py --space DEV --title "Weekly Update" \
  --body-file update.md --markdown

# Create with labels
python scripts/create_confluence_blog_post.py --space DEV --title "Architecture Decision" \
  --labels "adr,architecture" --body "<p>We decided to use microservices.</p>"
```

## Options

| Option | Description |
|--------|-------------|
| `--space`, `-s` | Space key (required) |
| `--title`, `-t` | Blog post title (required) |
| `--body`, `-b` | Post body in storage format (HTML) or markdown |
| `--body-file` | Read body content from file |
| `--markdown`, `-m` | Convert body content from markdown to Confluence format |
| `--labels`, `-l` | Comma-separated labels to add |
| `--format`, `-f` | Output: compact (default), text, json |

## Blog Posts vs Pages

| Feature | Blog Post | Page |
|---------|-----------|------|
| Date-stamped | Yes (published date) | No |
| Location | Space's blog section | Page hierarchy |
| URL format | `/blog/YYYY/MM/DD/title` | `/pages/id/title` |
| Navigation | Chronological feed | Tree structure |
| Use case | News, updates, announcements | Documentation, reference |

## Common Workflows

### Create Release Announcement
```bash
python scripts/create_confluence_blog_post.py \
  --space DEV \
  --title "Release v2.5.0 - New Dashboard Features" \
  --labels "release,announcement" \
  --body "<h2>What's New</h2><ul><li>New dashboard widgets</li><li>Performance improvements</li></ul>"
```

### Create Sprint Retrospective
```bash
python scripts/create_confluence_blog_post.py \
  --space TEAM \
  --title "Sprint 42 Retrospective" \
  --labels "retrospective,sprint" \
  --body-file retro-notes.md --markdown
```

### Create Weekly Update
```bash
python scripts/create_confluence_blog_post.py \
  --space DEV \
  --title "Weekly Engineering Update - Jan 10" \
  --labels "weekly-update" \
  --body "<p>This week's highlights...</p>"
```

### Create from Markdown File
```bash
python scripts/create_confluence_blog_post.py \
  --space DEV \
  --title "Technical Deep Dive: Caching Strategy" \
  --body-file caching-post.md --markdown \
  --labels "technical,deep-dive"
```

## Output Formats

**compact** (default):
```
CREATED|123456|Release Notes v2.0|DEV|blogpost
URL:https://yoursite.atlassian.net/wiki/spaces/DEV/blog/123456
```

**text**:
```
Blog Post Created: Release Notes v2.0
ID: 123456
Space: DEV
Type: blogpost
URL: https://yoursite.atlassian.net/wiki/spaces/DEV/blog/123456
```

**json**:
```json
{"id":"123456","title":"Release Notes v2.0","space":"DEV","type":"blogpost","url":"..."}
```

## Environment Setup

Requires environment variables:
- `CONFLUENCE_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `CONFLUENCE_EMAIL` - Your Atlassian account email
- `CONFLUENCE_API_TOKEN` - API token from Atlassian account settings

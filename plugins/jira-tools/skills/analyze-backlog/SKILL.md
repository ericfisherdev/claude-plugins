---
name: analyze-backlog
description: This skill MUST be used when the user asks to "analyze backlog issues", "analyze backlog", "analyze top backlog items", "Claude analyze tickets", "run analysis on backlog", "AI analyze Jira issues", "bulk analyze issues", "analyze unanalyzed tickets", or wants to have Claude automatically analyze and annotate multiple backlog issues. This skill finds the top 3 backlog issues without the claude-analyzed label, performs issue-analysis on each, and updates the Jira description with a Claude Analysis section.
---

# Jira Backlog Analysis

Automatically analyze the top 3 backlog issues that haven't been analyzed yet, generate implementation plans, and update the tickets with the analysis.

## What This Skill Does

1. **Gets list of unanalyzed issues**: Queries Jira directly for backlog issues missing the `claude-analyzed` label
2. **Processes each issue sequentially (just-in-time)**:
   - Fetches fresh issue details from Jira (not cache)
   - Verifies issue still needs analysis
   - Analyzes codebase using the `issue-analysis` workflow
   - Creates implementation plan
   - Updates description immediately (appends "Claude Analysis" section, preserving original text)
   - Adds `claude-analyzed` label
3. **Returns results**: Shows summary of all updated tickets

This just-in-time approach prevents race conditions where someone else modifies a later issue while you're working on an earlier one.

## Quick Start

When this skill is invoked, follow these steps:

### Step 1: Get List of Issues to Analyze

First, get the issue keys for backlog issues that don't have the `claude-analyzed` label:

```bash
python plugins/jira-tools/skills/analyze-backlog/scripts/analyze_backlog.py find PROJECT --max-results 3 --format compact
```

**IMPORTANT:** This command queries Jira directly (no cache) to ensure we get the current state of labels. This prevents conflicts where another person may have already analyzed an issue before our cache updated.

If no issues are found, inform the user that all backlog issues have already been analyzed.

**Save the list of issue keys** (e.g., `PROJ-101`, `PROJ-102`, `PROJ-103`) to process sequentially.

### Step 2: Process Each Issue (Just-In-Time)

**CRITICAL:** Process issues ONE AT A TIME. Do NOT fetch all issue details upfront. This prevents race conditions where someone else modifies a later issue while you're working on an earlier one.

For each issue key in the list, complete the FULL cycle before moving to the next:

#### 2a. Fetch Fresh Issue Details

Query Jira for the CURRENT state of this specific issue:

```bash
python plugins/jira-tools/skills/analyze-backlog/scripts/analyze_backlog.py get ISSUE-KEY --format text
```

This fetches the latest description, labels, and status directly from Jira.

**Before proceeding, verify the issue still needs analysis:**
- If it now has the `claude-analyzed` label, skip to the next issue (someone else analyzed it)
- If the issue no longer exists or is inaccessible, skip to the next issue

#### 2b. Analyze the Codebase

Based on the freshly-fetched issue details, follow the `issue-analysis` skill workflow:

1. **Search for relevant files** using labels as hints
2. **Find existing patterns** and similar implementations
3. **Identify dependencies** and affected areas
4. **Check for existing test coverage**
5. **Check if already fixed**: Search for recent commits or existing code

#### 2c. Create Implementation Plan

Generate a concise plan with:
- Summary of what will be implemented
- Pre-conditions and dependencies
- Implementation steps with pseudo-code
- Testing strategy
- Estimated scope (files to modify, complexity)

#### 2d. Update the Issue Immediately

Update this issue NOW, before moving to the next one:

```bash
python plugins/jira-tools/skills/analyze-backlog/scripts/analyze_backlog.py update ISSUE-KEY --analysis "ANALYSIS_TEXT"
```

This script:
- Fetches the CURRENT description from Jira (in case it changed)
- Appends the Claude Analysis section
- Adds the `claude-analyzed` label
- Returns the updated issue info

**Analysis format to pass:**

```
### Summary
[One-sentence description of what will be implemented]

### Pre-conditions
- [Any setup, dependencies, or prerequisites]

### Implementation Steps

#### 1. [First major step]
**Files:** `path/to/file.ext`

[Brief description]

```pseudo
// Pseudo-code showing the approach
```

#### 2. [Second major step]
...

### Testing Strategy
- [How to verify the implementation]

### Estimated Scope
- Files to modify: X
- New files: Y
- Complexity: Low/Medium/High
```

#### 2e. Record Result and Continue

Note the result for this issue, then repeat steps 2a-2d for the next issue in the list.

### Step 3: Return Results

After processing all issues, provide a summary:

```
## Backlog Analysis Complete

Analyzed and updated 3 issues:

### ISSUE-1: [Summary]
- Status: [Current Status]
- Complexity: [Low/Medium/High]
- URL: https://yoursite.atlassian.net/browse/ISSUE-1

### ISSUE-2: [Summary]
- Status: [Current Status]
- Complexity: [Low/Medium/High]
- URL: https://yoursite.atlassian.net/browse/ISSUE-2

### ISSUE-3: [Summary]
- Status: [Current Status]
- Complexity: [Low/Medium/High]
- URL: https://yoursite.atlassian.net/browse/ISSUE-3
```

## Special Cases

### Already Fixed Issues

If analysis reveals an issue is already fixed:
- Still update the description with the "Already Fixed" finding
- Include evidence (file paths, code snippets)
- Add the `claude-analyzed` label
- Recommend closing the issue

### Insufficient Context

If an issue lacks enough detail to create a meaningful plan:
- Note the missing information in the analysis
- Provide what analysis is possible
- Recommend adding more detail to the ticket

### No Backlog Issues Found

If no unanalyzed backlog issues exist:
- Inform the user: "All backlog issues have been analyzed (have the claude-analyzed label)"
- Suggest using `--refresh` flag on backlog-summary to force refresh cache

## Environment Setup

Requires three environment variables:
- `JIRA_BASE_URL` - e.g., `https://yoursite.atlassian.net`
- `JIRA_EMAIL` - Your Jira account email
- `JIRA_API_TOKEN` - API token from Atlassian account settings

## Cache Usage

This skill uses the shared cache (`~/.jira-tools-cache.json`):
- **Does NOT read from cache** for finding or fetching issues (always queries Jira directly to prevent race conditions)
- **Writes to cache** after updating issues (keeps cache fresh for other skills)
- Uses cache for user and priority lookups during updates

## Tips

1. **Run during quiet times**: Analysis involves codebase exploration which takes time
2. **Review before implementing**: The analysis provides a starting point, not final decisions
3. **Re-run periodically**: New issues in backlog won't have the label yet

## Notes

- The `claude-analyzed` label is **automatically created** in Jira when first applied - no manual setup required
- Labels in Jira are created on-the-fly when added to any issue

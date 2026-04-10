---
name: review-watch
description: This skill MUST be used when the user asks to "watch PRs", "monitor PRs", "review watch", "auto-merge", "watch pull requests", "manage PR lifecycle", "auto-fix CI", "watch for reviews", or wants automated PR monitoring with CI fix, review response, and merge capabilities.
---

# PR Review Watch

Monitor a pull request and automatically manage its lifecycle until merge.

## Usage

```
/review-watch [pr-number-or-url]
```

- If a PR number or URL is given, watch only that PR.
- If no argument is given, watch **all open and draft PRs** in the current repo.

## Behavior

Run a check loop every 5 minutes using the `/loop` skill.

### Multi-PR mode (no argument)

On each iteration:
1. Fetch all open/draft PRs authored by the current user: `gh pr list --state open --author "@me" --json number,title,isDraft,headRefName,baseRefName --limit 50`
2. For each PR, evaluate the priority-ordered actions below.
3. Process PRs sequentially. Use a **worktree per PR** to avoid branch switching conflicts:
   - Check out each PR's branch in its own worktree (create if needed, reuse if exists)
   - Perform the action in that worktree
   - Push from that worktree
4. After processing all PRs, log a summary: "Checked N PRs. Actions taken: PR #X (rebased), PR #Y (CI fix), PR #Z (waiting)."
5. PRs that have been merged are automatically removed from future iterations.

### Single-PR mode (argument given)

On each iteration, evaluate the single PR and take exactly one action (the highest-priority applicable action). After taking an action, wait for the next iteration before re-evaluating.

### Priority-ordered actions (first match wins)

1. **Merge conflicts** — If the PR has merge conflicts, resolve them:
   - `git fetch origin main && git rebase origin/main`
   - Resolve conflicts by reading both sides and choosing the correct resolution
   - `git rebase --continue`, then force-push the branch
   - Log: "Resolved merge conflicts and rebased on main"

2. **Rebase on main** — If the PR's base branch is not `main` AND that base branch has already been merged into main:
   - Change the PR base to `main` via `gh pr edit <num> --base main`
   - `git fetch origin main && git rebase origin/main`
   - Force-push the branch
   - Log: "Base branch was merged into main. Rebased PR on main."

3. **CI failure (draft PR)** — If the PR is a draft and CI checks have failed:
   - Read the failing check logs via `gh run view <run-id> --log-failed`
   - Diagnose and fix the issue in code
   - Commit with message `fix: <description of what was fixed>`
   - Push and wait for CI to run again
   - Log: "CI failed: <check-name>. Applied fix in <commit-hash>."
   - On next iteration, re-check CI. Repeat until green.

4. **CI passes (draft PR)** — If the PR is a draft and all CI checks pass:
   - If the PR's base branch is **not** `main`, skip this action — do not mark as ready for review. Log: "CI passed but base branch is <branch>, not main. Skipping ready-for-review."
   - `gh pr ready <num>`
   - Log: "All CI checks passed. Marked PR as ready for review."

5. **Changes requested** — If the PR has review comments requesting changes:
   - Read each unresolved review comment/thread
   - For each request, either:
     - **Apply the change**: make the code change, commit, reply to the comment with: `@<reviewer> Applied in <commit-hash>. <brief explanation of what changed>.`, then resolve the thread via `gh api --method PATCH repos/{owner}/{repo}/pulls/comments/{comment_id} -f body="..."` or the GraphQL `resolveReviewThread` mutation.
     - **Decline the change**: reply to the comment with: `@<reviewer> Skipping this — <reason>.` (e.g., "this is intentional because...", "out of scope for this PR", "conflicts with design spec X"), then resolve the thread — declined comments are still resolved since no further action is needed.
   - After replying and resolving, push all commits
   - Log: "Addressed N review comments from @reviewer (N resolved)."

6. **Approved + on main** — If the PR has at least one approval, zero requested-changes reviews, is based on `main`, and CI is green:
   - `gh pr merge <num> --rebase --delete-branch`
   - Clean up the worktree for this PR if one exists
   - Log: "PR #N approved and CI green. Merged via rebase into main."
   - In single-PR mode: stop the loop.
   - In multi-PR mode: continue to the next PR. If all watched PRs have been merged, stop the loop.

7. **No action needed** — If none of the above apply (e.g., PR is in review, waiting for reviewer):
   - Log: "Waiting. Status: <draft|review|approved>, CI: <pending|pass|fail>, base: <branch>."

### State detection commands

Use these `gh` commands to detect PR state:

```bash
# Full PR state (JSON)
gh pr view <num> --json state,isDraft,baseRefName,headRefName,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,reviews

# CI check status
gh pr checks <num> --json name,state,conclusion

# Review comments (unresolved)
gh api repos/{owner}/{repo}/pulls/<num>/reviews
gh api repos/{owner}/{repo}/pulls/<num>/comments
```

### CodeRabbit rate limit handling

When checking PR comments, look for comments from `coderabbitai` (or `coderabbitai[bot]`) that contain "Rate limit exceeded" or "rate limit". If found:
- Do **not** post `@coderabbitai review` immediately — that will hit the rate limit again.
- Log: "CodeRabbit rate-limited. Will retry review request on next loop iteration."
- On the **next** loop iteration, if the rate limit comment is still the most recent CodeRabbit comment (i.e., no new review has appeared):
  - First check whether `coderabbitai[bot]` has already submitted an **approving review** on the PR (`gh pr view <num> --json reviews` — look for `state: "APPROVED"` from `coderabbitai[bot]`). If already approved, skip — no need to re-request a review.
  - If not approved, post a PR comment: `@coderabbitai review`
  - Log: "Posted @coderabbitai review (retry after rate limit)."

### Safety rules

- **Never force-push to main.** Only force-push feature branches after rebase.
- **Never merge without at least one approval.**
- **Never dismiss reviews.** Only address or reply to them.
- **Never modify files outside the PR's diff scope** when fixing CI or addressing reviews.
- **If a CI fix requires more than 3 attempts**, stop the loop and report: "CI fix failed after 3 attempts. Manual intervention needed."
- **If a review comment is ambiguous**, reply asking for clarification rather than guessing.
- **Always use `--rebase` merge strategy**, never squash or merge commit.
- **Log every action** so the user can see what happened during the watch.

### Conflict resolution strategy

When resolving merge conflicts during rebase:
- Read both the incoming (main) and current (PR) changes
- Prefer the PR's changes when they are the intentional modification
- Prefer main's changes when the PR's side is just stale context
- If both sides made intentional changes to the same code, combine them logically
- After resolution, run any available tests to verify the merge didn't break anything

### Review response guidelines

When addressing code review feedback:
- Read the full thread context, not just the latest comment
- Check if the requested change aligns with the project's CLAUDE.md guidelines
- If the change conflicts with CLAUDE.md or design specs, explain why in the reply
- Keep fixes minimal — only change what the reviewer asked for
- Each review response commit should be atomic (one commit per review thread)

---
name: git-workflow
description: Use when the user asks about git commands, commit messages, branch management, rebasing, merging, resolving merge conflicts, stashing, reverting, or any git workflow in Rust projects. Provides commit message conventions, atomic commit rules, branching strategy, rebase workflow, conflict resolution protocol, stashing patterns, and dangerous-command safeguards.
---

# Git Workflow for Rust Projects

## 0. Authorization Gate

**Never stage, commit, push, merge, rebase, or amend without an explicit command from the user.**
An "explicit command" is a direct statement such as "commit", "stage that file",
"push to origin", or "merge the PR". Implied intent, prior agreement, or
"go ahead" + silence does not count. If unsure, ask.

This rule overrides all other instructions in this skill.

## 1. Commit Message Convention

Use **Conventional Commits** format:

```
<type>(<scope>): <imperative description>

[optional body]

[optional footer]
```

### Types

| Type | When to use |
|------|-------------|
| `feat:` | A new feature |
| `fix:` | A bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `test:` | Adding or fixing tests |
| `chore:` | Build process, CI, tooling, dependencies |
| `perf:` | Performance improvement |
| `style:` | Formatting, missing semicolons (not code logic) |

### Rules

- **Imperative present tense:** "Add feature" not "Added feature" or "Adds feature"
- **Lowercase after type:** `feat: add pagination` not `feat: Add pagination`
- **No period at end of subject line**
- **Scope optional** but encouraged when the change is module-specific: `fix(p2p): handle connection timeout`
- **Breaking changes:** append `!` after type/scope: `feat!: change API endpoint` or add `BREAKING CHANGE:` in footer
- **Body** wraps at 72 characters, explains *why* not *what*

### Examples

```
feat: add session persistence across restarts

Persist session state to disk on every tick so reconnecting peers
can resume without full re-sync.

Closes #142
```

```
refactor(network): extract connection pool from Swarm

Prepares for reusing connections across multiple streams
without coupling to the Swarm lifecycle.
```

```
fix(auth): return error on expired token instead of panic

Replaces unwrap() with proper error propagation so the caller
can decide how to handle expiry.
```

```
chore: bump rustc from 1.80 to 1.82
```

## 2. Branch Naming

```
<type>/<short-description>
```

### Patterns

| Pattern | Example |
|---------|---------|
| `feat/<desc>` | `feat/session-persistence` |
| `fix/<desc>` | `fix/connection-timeout` |
| `refactor/<desc>` | `refactor/extract-pool` |
| `chore/<desc>` | `chore/update-deps` |
| `docs/<desc>` | `docs/api-readme` |

### Rules

- Lowercase, hyphens between words
- Keep under 50 characters
- Delete branch after merge

## 3. Atomic Commits

One commit = one logical change. A commit must:

- **Build successfully** (`cargo build --all-targets`)
- **Pass lints** (`cargo clippy -- -D warnings`, `cargo fmt -- --check`)
- **Pass tests** (`cargo test --all-targets`)
- Be a single concern (don't mix formatting changes with logic changes)

### When to split

Split into multiple commits when a change touches:
- Two unrelated modules (e.g., auth + networking)
- A refactor + a feature in the same file
- Mechanical changes (renames, re-exports) + logic changes

### When to combine

Combine into one commit when:
- Fixing a bug introduced in the same branch's earlier commit (rebase + squash instead of a "fixup" commit)
- Changes are interdependent and don't compile or pass tests individually

## 4. Rebase Workflow

Prefer rebase over merge to maintain a linear history.

### Before pushing (clean up local history)

```bash
git rebase -i HEAD~N
```

Common operations:
- `pick` — keep as-is
- `fixup` / `f` — keep changes but discard the commit message (merge into previous)
- `squash` / `s` — combine with previous, edit message
- `reword` / `r` — edit commit message only
- `edit` / `e` — stop to amend

### Before opening a PR / pulling upstream

```bash
git fetch origin
git rebase origin/main
```

This replays your commits on top of the latest main, avoiding merge commits.

### After rebasing

Use `--force-with-lease` (never bare `--force`):

```bash
git push --force-with-lease
```

### Golden rule

**Never rebase commits that exist on a shared branch** (main, release, or another person's branch). Only rebase your own unpublished commits.

## 5. Conflict Resolution Protocol

When a rebase or merge produces conflicts:

1. **List conflicted files:**
   ```bash
   git status
   ```

2. **Open each file and find conflict markers:**
   ```
   <<<<<<< HEAD
   (your/current change)
   =======
   (incoming change)
   >>>>>>> branch-name
   ```

3. **For each conflict:**
   - Understand both sides — what does each version intend?
   - Choose one side, or write a combined version
   - **Remove the conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`)
   - Verify the result compiles: `cargo build`

4. **Stage and continue:**
   ```bash
   git add <resolved-files>
   git rebase --continue   # or git merge --continue
   ```

5. **If stuck:** `git rebase --abort` or `git merge --abort` to return to the pre-conflict state.

### Conflict prevention

- Pull/rebase frequently to keep branches short-lived
- Communicate with the team when touching shared areas
- Prefer small, focused commits that are easy to reason about

## 6. Stashing

### Common patterns

```bash
# Save current work (including untracked files)
git stash -u

# Save with a descriptive message
git stash push -m "wip: half-done refactor of session handler"

# List stashes
git stash list

# Apply most recent stash and keep it on the stack
git stash apply

# Apply and drop from stack
git stash pop

# Apply a specific stash
git stash apply stash@{2}

# Drop a specific stash
git stash drop stash@{2}
```

### When to stash

- Need to switch branches temporarily (urgent fix on main)
- Need to pull/rebase but have dirty working tree
- Experimenting and want to save a checkpoint without committing

### When NOT to stash

- Work that spans more than a few hours — commit it (even as `wip:` on a feature branch)
- Stashes accumulate and are easily forgotten; prefer commits on a feature branch

## 7. Revert vs. Reset

| Situation | Command | Effect |
|-----------|---------|--------|
| Undo a **published** commit (pushed/shared) | `git revert <commit>` | Creates a new commit that undoes changes. History is preserved. |
| Undo a **local** commit (not pushed) | `git reset --soft HEAD~1` | Keeps changes staged. |
| Discard a local commit and its changes | `git reset --hard HEAD~1` | Destroys changes. Use with extreme caution. |
| Unstage a file | `git reset HEAD <file>` | Keeps file changes but unstages them. |

### Rule of thumb

- **Revert** if the commit has been pushed to a shared branch
- **Reset** only if the commit exists exclusively in your local repo

## 8. PR / Review Flow

1. **Before opening a PR:**
   - `cargo build --all-targets && cargo clippy -- -D warnings && cargo fmt -- --check && cargo test --all-targets`
   - Rebase onto latest `main`
   - Squash fixup commits into logical units

2. **During review:**
   - Address feedback in new commits (don't amend yet) so the reviewer can see the diff
   - Commit messages should clearly respond to each review point

3. **Before merge:**
   - Squash fixup/response commits into the relevant logical commits
   - Rebase onto latest `main` again
   - Write a clean final commit message

4. **Merge strategy:** Prefer **squash merge** or **rebase merge** (linear history). Avoid merge commits.

## 9. Dangerous Command Safeguards

| Don't | Instead |
|-------|---------|
| `git push --force` | `git push --force-with-lease` (aborts if remote has new commits you haven't seen) |
| `git reset --hard HEAD~N` without checking | `git log --oneline -N` first to verify what you're discarding |
| `git commit -m "..."` without body | Write multi-line commit messages explaining *why* |
| `git rebase main` without fetching first | `git fetch origin && git rebase origin/main` |
| Amending pushed commits | Creates divergence; use separate commits or `--force-with-lease` only if you're the sole author of the branch |

## 10. Quick Reference

```bash
# Inspect
git log --oneline --graph -20         # recent history as graph
git diff                              # unstaged changes
git diff --cached                     # staged changes
git status                            # working tree state
git stash list                        # active stashes

# Branch
git checkout -b feature/foo           # create and switch
git branch -d feature/foo             # delete local branch (after merge)

# Remote
git fetch origin                      # fetch without merging
git pull --rebase                     # fetch + rebase (preferred over pull)
git push --force-with-lease           # force push safely

# Cleanup
git clean -fd                         # remove untracked files/dirs
git gc                                # garbage collect (periodic maintenance)
```

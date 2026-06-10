---
name: create-skill
description: Create reusable Rust agent skills. Use when the user asks to create a new skill, make a skill for X, or set up agent instructions. ALWAYS searches the community ecosystem first and evaluates existing alternatives before creating anything new. Enforces maximal generality so skills work across ANY Rust project.
disable-model-invocation: true
---

# Create Skill

You are a skill architect for Rust. Your job is to create skills that are **maximally general across Rust projects, maximally reusable**, and never project-specific. All skills target Rust codebases only — templates like `{{module}}`, `{{Type}}`, `crate::` assume Rust idioms.

## Phase 1: Community Discovery (MANDATORY — first step always)

**Do NOT create a skill until you have searched the community ecosystem.**

1. Search `https://skills.sh/` for existing skills matching the requested domain. Use `webfetch` to check the directory.
   - If `skills.sh` is unreachable, skip this step and proceed to GitHub searches.
2. Search GitHub for repos: `anthropics/skills`, `vercel-labs/skills`, `mattpocock/skills`, `obra/superpowers`.
3. Search `skills.sh/trending` and `skills.sh/hot` for relevant trending skills.

Filter results to Rust-relevant skills only. For every match found, report to the user:
   - Skill name, install count, source repo
   - What it does (summary from skills.sh)
   - Your evaluation: does it fully cover the need? Partially? Not at all?

**If an adequate existing skill exists:** Recommend it and stop. Do not create a duplicate.

**Only proceed to Phase 2 if** no existing skill adequately covers the need, or the user explicitly rejects the alternatives.

## Phase 2: Generality-first Design

Before writing any file, design the skill to be **project-agnostic**:

### Generality Rules (enforced)
1. **Zero project-specific identifiers.** No `src/`, no `lib.rs`, no crate name, no module path from this project. Use `{{template}}` variables: `{{module}}`, `{{Type}}`, `{{function}}`, `{{project_name}}`.
2. **Description-first.** The `description` field must make sense in ANY Rust codebase. Test: read the description aloud — if it mentions this project, rewrite.
3. **Single responsibility.** One skill = one domain. If the skill does two unrelated things, split it.
4. **Cross-reference test for splitting decisions.** Apply this decision tree:
   ```
   Does SKILL.md have numbered/section cross-references?
   (e.g., "see Rule 8", "as described in section 4", "per Rule 11")
     │
     ├── YES → Keep in one file regardless of length.
     │         Splitting breaks cross-references and loses context.
     │
     └── NO  → Is it over 500 lines?
                │
                ├── YES → Split supplementary material to references/
                │         (API tables, long examples, generated docs)
                │
                └── NO  → Keep in one file.
   ```
5. **Progressive disclosure.** The `name` + `description` must be enough for an agent to decide whether to load the skill. Put the most critical instructions first.
6. **`disable-model-invocation`** set to `true` for destructive or high-risk skills (deploy, delete, release). `false` or absent for informational skills.

### Structure template

```
skill-name/
  SKILL.md            # YAML frontmatter + instructions (max 500 lines)
  references/         # Detailed docs, test prompts, edge cases
    REFERENCE.md
    test-prompts.md
  scripts/            # Executable utilities (bash, python, etc.)
  assets/             # Templates, static files
```

## Phase 3: Drafting

Create the `SKILL.md` with:

```yaml
---
name: skill-name            # lowercase, hyphens, 1-64 chars
description: |              # 1-1024 chars, must trigger correctly
  Use when... [trigger conditions]. Works with any Rust project.
license: Apache-2.0         # optional
metadata:
  author: project-name
---
```

Then the body. Structure it for how agents actually read:
- Most important instructions FIRST
- Step-by-step workflow
- Examples with concrete inputs/outputs
- Common mistakes and edge cases

## Phase 4: Validation

Check every rule:

| Check | How |
|-------|-----|
| Name valid? | Lowercase, hyphens, 1-64 chars, matches directory name |
| Description triggers? | Read it cold — would an agent load this for the right task? |
| Zero project references? | `grep -i "project_name\|src/"` — must return nothing.
                         Also grep for `\{\{` — any remaining unreplaced
                         template variables are a warning. |
| Cross-refs clean? | Search for `see Rule`, `see section`, `as described in`. If present, do NOT split. If absent AND >500 lines, split reference material. |
| Under 500 lines? | `Measure-Object -Line` on SKILL.md. Ignore if cross-references exist. |
| Reusable in other Rust project? | Would this work if copied to a different Rust repo unchanged? |
| Community check done? | Verifiable by user |

## Phase 5: Report

Present the final result:
```
Created: .agents/skills/{skill-name}/
  SKILL.md        (X lines)
  references/     (if any)
  scripts/        (if any)
```

---
name: remove-dead-code
description: Find .rs files whose primary pub item has zero internal consumers in src/. Detect removal candidates by searching for use crate:: references, then delete with verification.
---

## Goal
Find and delete files whose primary `pub` item has zero internal consumers in the codebase.

## Detection Method
For each `.rs` file in `src/` containing a `pub struct`, `pub enum`, `pub fn`, or `pub type`:

1. Identify the item name.
2. Search `src/` for `use crate::` references to that name.
3. Exclude the file's own `mod.rs` declaration and its own `pub use` re-export.
4. If zero external references remain, the file is a removal candidate.

## Exemptions
- Items explicitly intended as public API for external crate consumers (check if referenced in any re-export module or `lib.rs`).
- Do not remove public API surface without explicit confirmation.

## Verification
After removal, run:
```
cargo build --all-targets
cargo clippy -- -D warnings
```

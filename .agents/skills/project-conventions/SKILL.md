---
name: project-conventions
description: Rust project conventions, architecture rules, atomic file structure, naming (echo rule), module flattening, error handling with thiserror, inline testing rules, absolute crate:: imports, no trivial accessors, and no positional fields for ANY Rust project.
---

# SYNTAX & ARCHITECTURE GUIDELINES

## Template Convention

All examples use template variables to remain project-agnostic:

| Variable | Meaning | Example replacement |
|---|---|---|
| `{{module}}` | Module path | `auth`, `p2p`, `inventory` |
| `{{Type}}` | PascalCase type name | `Config`, `Credentials` |
| `{{type}}` | snake_case type name (lowercase of `{{Type}}`) | `config`, `credentials` |
| `{{function}}` | snake_case function name | `authenticate`, `broadcast` |
| `{{submodule}}` | Subdirectory name | `system`, `component`, `resource` |

Replace these with actual names from your project. Never use template variables literally in code — the compiler will reject them.

## 1. Rule Priority
This file's rules override standard Rust conventions. Treat this file as the absolute source of truth for architecture, naming, file structure, and error handling.

## 2. Domain / Feature Mapping
The project is divided into isolated domain/feature modules. In these rules, we use `{{module}}` as a template variable meaning "your module path" (e.g., `p2p`, `auth`, `inventory`). **IMPORTANT: `{{module}}` is not valid Rust syntax. Never use it literally — you must replace it with the actual module name. The compiler will reject `crate::{{module}}::Config;` immediately with a syntax error.**

## 3. Atomic File Structure & Naming (CRITICAL)
Every file must contain exactly **one** primary logic unit (one function, one struct, or one enum).
**Rule:** The filename MUST have the exact same name as the core item inside it.
- **Functions:** Filename exactly matches the function name (e.g., `authenticate.rs` for `pub fn authenticate`).
- **Structs/Enums:** Filename exactly matches the type name (e.g., `Credentials.rs` for `pub struct Credentials`).
- **Struct Decomposition (mandatory for every struct with impls):** If a struct has any hand-written `impl` blocks (inherent or trait) in source code, you MUST decompose into subfolders. There is no length threshold. `#[derive(...)]` macros do NOT trigger decomposition — only visible, hand-written `impl` blocks count.

  **Structure:**
  - `StructName.rs` — struct definition **plus `impl TypeName { pub const ... }` blocks (associated constants, real bodies)** plus **`impl Default` (if any, real body)** plus ALL other `impl` blocks (inherent and trait) as **thin delegates** (one-line call to `TypeNameMethod::function_name()`). No method bodies, no business logic, no tests.

  > **Why `impl Default` is an exception:** `Default` is uniformly trivial (one-liner constructor or literal fields), exempt from testing as a trivial method (Rule 8), and extracting it into `DefaultMethod/default.rs` would add a file for no architectural benefit. This exception is pragmatic and does not extend to any other trait or inherent impl.

  > **`#[rustfmt::skip]` on thin delegate impl blocks:** rustfmt expands single-line function bodies to three lines by default. To preserve the one-liner thin delegates, annotate every thin delegate `impl` block with `#[rustfmt::skip]`. The `impl Default` block (which has a real body) is NOT skipped — only the delegate-only impl blocks. See the example below.
  - `StructNameMethod/` — each public method and each trait method gets its own file with a **free function** whose name matches the method exactly. The body and inline test live here.
  - `StructNameMethod/mod.rs` — module declarations plus re-exports to flatten single-method modules. Free functions are module-level items, but they exist exclusively as infrastructure consumed by `StructName.rs`. Re-exporting them at the crate root would leak implementation detail. However, within `StructNameMethod/mod.rs`, `pub use` MUST be used to flatten the path from `new::new` to `new`, so that the struct file can call `config_method::new()` instead of `config_method::new::new()`.

  > **Clarification — struct def goes in `StructName.rs`, not in mod.rs:** The struct definition MUST live in the top-level `StructName.rs` file (sibling of `StructNameMethod/`). Never put it inside a `mod.rs`. This keeps mod.rs pure per Rule 6 and prevents the ambiguity of "which file defines the type?"

  **Named defaults (concept only — no special file placement):**
  A "named default" is a preset constructor (e.g., `Config::coop()`, `Config::pvp()`). It follows the same decomposition rule as any other method — goes in `StructNameMethod/` as a free function. The term exists only to distinguish presets from generic constructors or builders.
  
  A method qualifies as a named default when ALL hold:
  1. Returns `StructName`, takes no `self` receiver
  2. Return value is statically determined (literal field values, no params)
  3. Purpose is to provide a preset configuration variant

  Examples: `Config::coop()`, `Config::pvp()`, `Config::mmo()`, `Config::lan_coop()`
  Counterexamples: `Config::new()` — generic constructor; `Config::with_auto_accept(mut self, ...)` — builder, takes self; `BevyLibp2pPlugin::new(config)` — takes runtime parameter

  Delegation: a method that calls another named default and returns its result unchanged is itself a named default.

  > **Delegation call rule:** When a function in `StructNameMethod/` delegates to another method of the same struct, it MUST call it through the struct's public API (e.g., `Config::coop()`), NOT directly by name (e.g., not `coop()`). The struct method in `StructName.rs` is the authoritative API surface — all callers, including other `StructNameMethod/` functions, must route through it. Example chain: `Config::lan_coop()` → `ConfigMethod::lan_coop()` → `Config::coop()` → `ConfigMethod::coop()`.

  **Example (directory layout only — see [references/EXAMPLES.md](./references/EXAMPLES.md) for full code):**
  ```
  Config.rs               # struct + Default + thin delegate impl blocks
  ConfigMethod/
    mod.rs                # pub mod declarations + pub use flattening
    new.rs                # pub fn new() -> Config + tests
    coop.rs               # pub fn coop() -> Config + tests
    with_timeout.rs       # pub fn with_timeout(cfg: Config, ms: u64) -> Config + tests
  ```

  **`*Method/` free function naming — MUST match the method:**
  The function name in `*Method/*.rs` MUST be identical to the method name (including trait methods like `fmt`). The `*Method/` module path provides disambiguation — `ConfigMethod::fmt` is unambiguous. In test modules, use `use super::fmt as display_fmt;` if the standard `fmt` module is also needed.

**Directory module declarations — PascalCase directly (no `#[path]`):**
Because `non_snake_case` is allowed at the crate level, directory modules (directories, not `.rs` files) use PascalCase directly with no `#[path]`:
  ```rust
  // p2p/mod.rs — no #[path], no snake_case alias
  pub mod ConfigMethod;   // resolves to ConfigMethod/mod.rs
  ```
  Only `.rs` files where filename == struct name need `#[path]` (see section below). Directory modules have no type-namespace collision and require no `#[path]` — use PascalCase directly.

  **Benefits of this decomposition:**
  - `StructName.rs` shows every public method signature at a glance — the complete API surface without scrolling through bodies.
  - Individual files can be `#[cfg(feature = "...")]`-gated for optional features without cluttering a single file.
  - Each file carries its own self-contained test.
  - The struct definition (plus Default) remains a minimal, readable declaration.

  **Feature gating convention:** `#[cfg(feature = "...")]` on individual files in `StructNameMethod/` is supported by this architecture. However, do not add feature flags unless explicitly requested.

  **Helper exception:** Small private helper functions used **exclusively by the file's single primary item** are permitted in the same file. They do not count as additional primary logic units. If a helper grows large enough to warrant its own file, extract it.

**Crate-level `non_snake_case` allow — REQUIRED:**
Because filenames match their PascalCase item names (e.g., `Credentials.rs` for `struct Credentials`), a `pub mod Credentials;` declaration would violate Rust's snake_case convention. Suppress this by setting `[lints.rust] non_snake_case = "allow"` in `Cargo.toml`. This applies the lint to all crate targets uniformly. (If Cargo.toml is unavailable, `#![allow(non_snake_case)]` in `src/lib.rs` is the fallback.) Never use both — the `lib.rs` allow MUST be removed once `Cargo.toml` has the lint setting.

With that allow in place, `pub mod Credentials;` resolves to `Credentials.rs`. However, since every `.rs` file's name matches its core item, `pub mod Credentials;` + `pub use Credentials::Credentials;` would collide in the type namespace — both the module and the re-exported type would claim the name `Credentials`. The `#[path]` attribute resolves this:

### `.rs` File vs. Directory Module Declaration

| Kind | Pattern | `#[path]`? | Reason |
|------|---------|------------|--------|
| Directory (e.g., `ConfigMethod/`) | `pub mod ConfigMethod;` | No | Directory name is not a type; no namespace collision |
| `.rs` file with PascalCase type (struct/enum) | `#[path = "{{Type}}.rs"] pub mod {{type}};`<br>`pub use {{type}}::{{Type}};` | **Yes** | Lowercase module `config` and PascalCase type `Config` are distinct identifiers; no collision |

| `.rs` file with snake_case function | `pub mod {{function}};`<br>`pub use {{function}}::{{function}};` | No | Functions live in the value namespace, separate from modules (type namespace) |

**Naming rules:**
- Struct and enum names MUST be PascalCase (e.g., `Config`, `Event`, `PeerState`).
- Function names MUST be snake_case (e.g., `get_game_topic`, `poll_network`).
- Module names MUST be snake_case. For `.rs` files containing PascalCase types, use the snake_case version of the type name as the module alias (e.g., `config` for `Config`, `event` for `Event`). Since Rust is case-sensitive, a lowercase module `config` and a PascalCase type `Config` are distinct identifiers in the type namespace — no collision occurs. For function files, `pub mod get_game_topic; pub use get_game_topic::get_game_topic;` works because functions are in the value namespace, separate from modules.

```rust
// p2p/mod.rs — correct patterns
#[path = "Config.rs"]
pub mod config;
pub use config::Config;

#[path = "Swarm.rs"]
pub mod swarm;
pub use swarm::Swarm;

// Directories — no #[path], PascalCase directly:
pub mod ConfigMethod;
pub mod resource;
pub mod system;
```

### Constants

Constants follow different rules depending on their nature. This section is an addendum to Rule 3's atomic file structure.

#### Associated Constants (belonging to a struct type)

A constant whose value is exclusively meaningful in the context of a **single** struct type MUST be defined as an associated constant inside that struct's `impl TypeName` block in `StructName.rs`:

```rust
// GossipTopic.rs
pub struct GossipTopic(pub libp2p::gossipsub::IdentTopic);

impl GossipTopic {
    pub const GAME_TOPIC_STR: &str = "bevy_p2p_game";
}

impl Default for GossipTopic {
    fn default() -> Self { Self::new() }
}
```

**Layout in `StructName.rs` (in order):**
1. `struct` definition
2. `impl TypeName { pub const ... }` — associated constants, real bodies
3. `impl Default` — real body (existing exception)
4. All other `impl` blocks — thin delegates to `TypeNameMethod/` (existing rule)

**Consumer path:** `TypeName::CONST` (e.g., `GossipTopic::GAME_TOPIC_STR`)

**Criterion — associated vs. module-level:** A constant MUST be an associated constant if **all** of the following hold:
1. Its value is only meaningful in the context of one specific struct type.
2. It is only referenced by that type's own methods (in `StructNameMethod/`) or by the struct's `impl` blocks in `StructName.rs`.
3. No other type, function, or module outside `StructName.rs` and `StructNameMethod/` files reads it.

If any code outside the struct's own files references the constant (e.g., a module-level function, another type's method), it MUST be a module-level constant in `constants.rs` instead.

#### Module-level Constants

A constant whose meaning or usage spans multiple types within the module, or is referenced by module-level functions, MUST be placed in a grouped `constants.rs` file inside the module directory. This is an **explicit exception** to the "one primary logic unit per file" rule — many constants of similar construction belong together in one file:

**Criterion:** A constant is module-level (and goes in `constants.rs`) if **any** of the following hold:
1. It is referenced by two or more distinct types or functions within the module.
2. It is referenced by a module-level function, not by a struct's methods.
3. It represents a well-known value whose scope is the module (e.g., protocol identifiers, channel names, magic numbers used across the module).

```
ability/
  mod.rs                  # pub mod constants; pub use constants::*;
  constants.rs            # grouped pub const definitions
```

```rust
// ability/constants.rs
pub const HASTE: Ability = Ability::Static {
    effect: ContinuousEffect::GiveKeyword {
        affect: THIS,
        keyword: StaticKeyword::Haste,
        until: Until::Forever,
    },
};
pub const VIGILANCE: Ability = Ability::Static { ... };
```

```rust
// ability/mod.rs
pub mod constants;
pub use constants::*;    // glob re-export: all constants exposed at module root
```

**No `#[path]` needed:** Constants live in the value namespace, while `pub mod` lives in the type namespace. There is no collision — `pub use constants::*;` re-exports values while the module `constants` is a type-namespace item. The glob re-export is safe here because `constants.rs` contains only `pub const` definitions.

**Consumer path:** `module::CONST` (e.g., `ability::HASTE`)

**No `test_usage` required:** A `constants.rs` file containing only `pub const` definitions is exempt from testing (pure value declarations, see Rule 8).

## 4. Contextual Naming (Zero Redundancy)

Items (files, functions, structs) inherently inherit the context of their parent directory and module path. **Never repeat parent folder or module names in the child filename, struct name, or function name.** Write names as if they are meant to be read from the root of their path.

The module hierarchy is the "last name," the item name is the "first name." Don't repeat the last name in the first name.

### Core Test

Ask yourself: "If I drop the module name from this item's name, do I lose information that the module path doesn't already give me?"

| ✗ Wrong (redundant) | ✓ Correct | Why |
|---|---|---|
| `auth::logic::auth_user` | `auth::logic::authenticate` | Module says "auth"; function should say *what* (authenticate), not *where* (auth) |
| `inventory::model::InventoryItem` | `inventory::model::Item` | Module says "inventory"; `Item` is unambiguous |
| `auth::AuthError` | `auth::Error` | Module says "auth"; `Error` suffices |
| `network::NetworkState` | `network::PeerState` | `Peer` clarifies *which* state; dropping the echo `Network` is what matters |

### Echo vs. Disambiguator

A qualifier is **redundant (echo)** when it repeats the same lexical root as the module name (the same word, an obvious abbreviation, or a near-synonym) and adds no new information beyond what the module name already conveys. A qualifier is a **disambiguator** when it distinguishes siblings within the same module using information not already present in the module name.

- `network::NetworkState` → `network::` already says "network"; `Network` is an echo. If only one state exists, use `network::State`. If multiple states exist, use a disambiguator: `network::PeerState`, `network::ConnectionState` — `Peer` and `Connection` clarify *which*, `Network` merely echoes.
- `auth::AuthError` → `auth::` already says "auth"; `Auth` is an echo. Use `auth::Error`.
- `p2p::P2pPlugin` → `p2p::` already says "p2p"; `P2p` is an echo. Use `p2p::Plugin`.
- `network::PeerState` → not an echo. `Peer` is a different word from `network`; it distinguishes *which* state within the network module.
- `domain::Event` → not an echo. `Event` is a different word from `domain`; it describes *what kind* of thing, not *where*.

### How It Applies to Files

Filenames follow the same rule.

- `auth/AuthError.rs` → `auth/Error.rs` ✓
- `inventory/InventoryItem.rs` → `inventory/Item.rs` ✓

### Common Misconceptions

1. **"`inventory::Item` is too vague!"** — It isn't. The module `inventory` provides full context. `use inventory::Item;` reads as "an inventory Item." If you later add `crafting::Item`, they coexist through the module path.
2. **"But what about `network::State` — there are multiple states!"** — Then `State` alone is too vague *within the module*. Add a **disambiguator** that distinguishes siblings: `PeerState`, `ConnectionState`. The qualifiers (`Peer`, `Connection`) describe *what kind* — they do NOT echo the module name (`Network`).
3. **"What about the Bevy `Plugin` trait?"** — A struct named `Plugin` does not collide with `bevy::prelude::Plugin`. Rust resolves traits and types independently. `impl bevy::prelude::Plugin for Plugin { ... }` works without conflict.

## 5. Module Exporting & Flattening (CRITICAL)
Because of our Atomic File Structure (e.g., `authenticate.rs` contains `pub fn authenticate`), Rust will naturally create a redundant path: `logic::authenticate::authenticate`. We avoid this by strictly flattening at the `mod.rs` level.

### A. Exporting (Inside `mod.rs`)
You MUST flatten single-function and single-struct files in their parent `mod.rs` using `pub use` to prevent stutter.

**Flat files** (items directly in the module directory, e.g., `Config.rs`, `broadcast.rs`):
```rust
// Inside src/auth/logic/mod.rs
pub mod authenticate;
pub use authenticate::authenticate; // ✓ CORRECT: Flattens the path
```

> **For PascalCase struct/enum files where filename == item name:** See the `#[path]` pattern in Rule 3. You MUST use `#[path]` with `{{type}}` (snake_case of the type name) as the module name. The lowercase module and PascalCase type are distinct identifiers — no collision occurs.

**Exception — items in subdirectories:**
All items inside internal subdirectories MUST NOT be re-exported at the module root. Consumers access them through their full submodule path so the import location matches the filesystem location. Only flat files directly in the module directory are re-exported via `pub use`.

```rust
// ✓ Subdirectory declared — its contents are NOT re-exported
pub mod {{submodule}};   // consumers: {{module}}::{{submodule}}::{{Type}}
                         //            {{module}}::{{submodule}}::{{function}}()
```

```rust
// ✗ WRONG: Re-exporting from subdirectories obscures their file location
pub mod {{submodule}};
pub use {{submodule}}::{{Type}};       // ← Don't do this
pub use {{submodule}}::{{function}};   // ← Don't do this
```

> **Exception — `constants.rs` glob re-export (value namespace, no collision):**
> Constants live in the **value namespace**, separate from the type namespace where `pub mod` resides. Re-exporting with `pub use constants::*;` creates no collision with `pub mod constants;` and makes module-level constants ergonomically accessible as `module::CONST` rather than `module::constants::CONST`.
>
> This exception applies **only** to `constants.rs` files — do not extend it to types, functions, or any other items in subdirectories. The glob `*` is safe here because `constants.rs` contains exclusively `pub const` definitions.

### B. Importing (Inside Consumer Files)
Consumer files must import items based on their type to maintain readability:

| What you're importing | Style | Example |
|---|---|---|
| **Flat types** (directly in module dir) | Import the exact item directly | `use crate::{{module}}::{{Type}};` |
| **Subdirectory items** (in `{{submodule}}/`) | Import through the full submodule path | `use crate::{{module}}::{{submodule}}::{{Type}};` |
| **Flat functions** (directly in module dir) | Import parent module, call through it | `use crate::{{module}};` → `{{module}}::{{function}}()` |
| **Subdirectory functions** (in `{{submodule}}/`) | Import the `{{submodule}}` module, call through it | `use crate::{{module}}::{{submodule}};` → `{{submodule}}::{{function}}()` |

```rust
// ✓ Correct — flat types: direct import
use crate::{{module}}::{{Type}};

// ✓ Correct — subdirectory items: full submodule path
use crate::{{module}}::{{submodule}}::{{Type}};

// ✓ Correct — flat functions: via module prefix
use crate::{{module}};

// ✓ Correct — subdirectory functions: via submodule prefix
use crate::{{module}}::{{submodule}};
```

```rust
// ✗ Wrong — super:: breaks on directory moves
use super::{{Type}};

// ✗ Wrong — subdirectory items imported at root obscures location
use crate::{{module}}::{{Type}};  // when {{Type}} lives in {{submodule}}/

// ✗ Wrong — flat functions imported directly loses module context
use crate::{{module}}::{{function}};

// ✗ Wrong — subdirectory functions imported directly loses submodule context
use crate::{{module}}::{{submodule}}::{{function}};
```

## 6. `mod.rs` — Module Tree Only (No Logic, No Exceptions)

A `mod.rs` file builds the module tree and flattens exports. It must NOT contain any business logic, struct definitions, or data of any kind.

> **Cross-reference:** For decomposed structs (Rule 3), the struct definition belongs in `StructName.rs`, never inside `StructNameMethod/mod.rs`. This rule applies to **every** `mod.rs` in the project.

**Rule:** A `mod.rs` may contain ONLY:
- `pub mod` declarations
- `pub use` re-exports
- `#[path]` attributes (for PascalCase filename resolution)

Everything else is **strictly forbidden**:
- ❌ Struct/enum definitions
- ❌ `impl` blocks (methods, trait impls)
- ❌ Functions (including private helpers)
- ❌ Constants or statics
- ❌ `#[cfg(test)]` modules
- ❌ Trait definitions

✅ **Allowed — pure re-export `mod.rs`:**
```rust
pub mod authenticate;
pub mod register;

pub use authenticate::authenticate;
pub use register::register;
```

✅ **Allowed — PascalCase struct with Method subdirectories:**
```rust
// p2p/mod.rs
#[path = "Config.rs"]
pub mod config;
pub use config::Config;

pub mod ConfigMethod;   // directory module, no #[path] needed (see Rule 3)
```

No `pub use` from `ConfigMethod` — methods are accessed through the `Config` type directly via the thin delegates in `Config.rs`.



## 7. Error Handling (Strict Constraints)
Error handling must be robust, explicit, and typed.
- **Never use `.unwrap()`, `.expect()`, or `panic!()`.** All errors must be gracefully propagated up the call stack.
- **Always use `thiserror`.** You must define strongly typed, domain-specific enums for errors using the `thiserror` crate. Do not use generic string errors or generic `Box<dyn Error>`.

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AuthError {
    #[error("Invalid credentials provided")]
    InvalidCredentials,
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Configuration error: {0}")]
    Config(String),
}
```

## 8. Testing Rules (Inline)
To maintain the atomic nature of the codebase, tests must live in the exact same file as the core item they are testing.
**Rule:** Do not create separate `tests/` directories or `test.rs` files. Append a `#[cfg(test)]` module at the absolute bottom of the atomic file.

Every file whose primary item is a non-trivial function (containing branching, arithmetic, I/O, or allocation) MUST contain a test named `test_usage` that exercises the file's primary item in a way that mirrors real consumption elsewhere in the codebase.

**Exemption — type-only definitions:** Files whose primary item (struct or enum) has **zero `impl` blocks of any kind** (no `impl TypeName`, no `impl Trait for TypeName`) are pure type definitions and do NOT require a `test_usage` test. Examples: a `thiserror` error enum with no methods, a marker struct, a plain data enum.

**Struct files with hand-written impl blocks — test_usage required:** A `StructName.rs` file that contains any hand-written `impl` block (inherent impls, trait impls, or `impl Default`) is a **non-trivial struct** and MUST contain a `test_usage` test. The test must:
1. Construct the struct (via `Default`, `new()`, or direct construction).
2. Exercise it through the **primary integration path** — the trait impl that defines its role, the system or consumer function that uses it.
3. Assert on an observable outcome.

A test that merely calls constructors without exercising consumer logic (e.g., `let _ = Config::default(); let _ = Config::new();`) is insufficient.

**Exemption — trivial methods:** One-liner accessor or delegating methods (getters, setters, thin delegation wrappers) with no branching, arithmetic, or I/O do NOT require a `test_usage` test. Their correctness is trivially verified by callers in the integration flow.

**Exemption — constant-only definitions:** Files whose only items are `pub const` definitions (no functions, no `impl` blocks) are pure value declarations and do NOT require a `test_usage` test. Their correctness is inherently verified by every consumer that reads or uses the constant.

**How to write `test_usage`:**
1. Search the codebase for files that import or call this file's primary item.
2. Identify a representative usage pattern (function call with concrete args, struct construction with real fields, etc.).
3. Replicate that pattern in `test_usage` with assertions on the observable result.

**What `test_usage` is NOT:**
- NOT a constructor smoke test (`let x = Foo::new(); assert!(x.field == default);`)
- NOT a trivial existence check (`let _ = Bar;`)
- NOT a write-only test that calls the item but never asserts anything

**When no real usage exists yet (item is new):**
Write the test as the *first* consumer — construct and exercise the item as if you were calling it from another module. This forces the API to be testable from the start.

Additional tests beyond `test_usage` are permitted when they cover distinct edge cases or scenarios not captured by the primary usage pattern.

```rust
// Inside auth/logic/authenticate.rs

use crate::auth::model::User;
use crate::auth::error::AuthError;

pub fn authenticate(username: &str, password: &str) -> Result<User, AuthError> { ... }

#[cfg(test)]
mod tests {
    use crate::auth::logic::authenticate;
    use crate::auth::error::AuthError;

    #[test]
    fn test_usage() {
        // Must replicate how this item is consumed elsewhere in the codebase.
        let result = authenticate("alice", "correct_password");
        assert!(result.is_ok());
    }

    #[test]
    fn test_invalid_credentials() {
        let result = authenticate("alice", "wrong_password");
        assert!(result.is_err());
    }
}
```

**Context-dependent items (e.g., framework systems):**
If the primary item requires an execution context (e.g., a game `App`, a `tokio` runtime, a network state), you MUST construct a minimal, working version of that context inside the test. See framework-specific skills for framework-specific testing patterns.

```rust
// Plugin.rs — struct with trait impl, test exercises the integration path
pub struct Plugin;

impl bevy::prelude::Plugin for Plugin {
    fn build(&self, app: &mut App) {
        PluginMethod::build(self, app)
    }
}

#[cfg(test)]
mod tests {
    use crate::{{module}}::Plugin;
    use bevy::prelude::*;

    #[test]
    fn test_usage() {
        let plugin = Plugin;
        let mut app = App::new();
        plugin.build(&mut app);
    }
}
```

**Important — imports in tests:** Test modules must follow Rule 11. `super::` is allowed for same-file items; all other imports use `crate::` paths.

## 9. Universal Code Style

- **No Comments:** Do not write comments in the code. The code must be self-documenting through clear naming.
- **Clarity over cleverness:** Write readable, maintainable code.
- **Early returns:** Use `?` or `return` to reduce nesting.
- **Indentation:** 4 spaces.
- **Thin delegates `#[rustfmt::skip]`:** Every thin delegate `impl` block (Rule 3) MUST use `#[rustfmt::skip]` to preserve one-liner format. `impl Default` blocks (real bodies) are NOT skipped.
- **Logging:** Use `tracing!` macros.
  ```rust
  tracing::debug!(target: "module_name", var_name = var.value);
  ```

## 10. Standard Build & Verification Routine

Verify changes with:
```bash
cargo build --all-targets
cargo clippy -- -D warnings
cargo fmt -- --check
cargo test --all-targets
```

## 11. Import Style — Absolute `crate::` Only (Strict)

Every `use` statement MUST start with `crate::` or an extern crate name. Relative paths (`super::`, `self::`) are banned in production code — they break silently when files move during refactoring.

### Import by type (pairing with Rule 5B)

| What you're importing | Style | Example |
|---|---|---|
| **Flat types** (directly in module dir) | Import exact item | `use crate::{{module}}::{{Type}};` |
| **Subdirectory items** (in `{{submodule}}/`) | Import through full submodule path | `use crate::{{module}}::{{submodule}}::{{Type}};` |
| **Flat functions** (directly in module dir) | Import parent module, call through it | `use crate::{{module}};` → `{{module}}::{{function}}()` |
| **Subdirectory functions** (in `{{submodule}}/`) | Import the `{{submodule}}` module, call through it | `use crate::{{module}}::{{submodule}};` → `{{submodule}}::{{function}}()` |
| **External crate types** | Import directly | `use extern_crate::Type;` |

Exception — `impl` blocks define methods directly on the type and use the type bare.

### Examples

```rust
// ✓ Correct — flat types via direct import
use crate::{{module}}::{{Type}};

// ✓ Correct — subdirectory items via full path
use crate::{{module}}::{{submodule}}::{{Type}};

// ✓ Correct — flat functions via module prefix
use crate::{{module}};

// ✓ Correct — subdirectory functions via submodule prefix
use crate::{{module}}::{{submodule}};
```

```rust
// ✗ Wrong — super:: breaks on directory moves
use super::{{Type}};

// ✗ Wrong — subdirectory items imported at root obscures location
use crate::{{module}}::{{Type}};  // when {{Type}} lives in {{submodule}}/

// ✗ Wrong — flat functions imported directly loses module context
use crate::{{module}}::{{function}};

// ✗ Wrong — subdirectory functions imported directly loses submodule context
use crate::{{module}}::{{submodule}}::{{function}};
```

### Test modules — `super::` allowed for same-file access

A `#[cfg(test)]` module may use `super::` to access items (functions, structs) defined in the **same file** it is embedded in. This avoids unnecessary repetition of the full `crate::` path for the file's own contents.

All other imports inside `#[cfg(test)]` modules that reference items outside the current file MUST still use `crate::`.

```rust
// ✓ Correct — super:: for same-file items, crate:: for external items
#[cfg(test)]
mod tests {
    use super::{{function}};           // same-file item ✓
    use crate::{{module}};             // module prefix for crate types ✓

    #[test]
    fn test_usage() {
        let _ = {{function}}("alice", "correct_password");
    }
}

// ✓ Correct — super::* for bulk same-file import
#[cfg(test)]
mod tests {
    use super::*;
    use crate::{{module}};

    #[test]
    fn test_usage() { ... }
}
```

### Exception — `mod.rs` re-exports only

The flattening pattern in `mod.rs` files (Rule 5A) uses `pub use` to re-export from submodules. These are not "consumer imports" and are exempt:

```rust
// ✓ This is fine — it's re-exporting a flat file, not consuming
pub mod {{function}};
pub use {{function}}::{{function}};
```

## 12. No Trivial Accessors (Getters/Setters)

A method that reads or writes a single `pub` field — named (`self.field`) or positional (`self.0`) — without any computation, validation, or side effect MUST be removed. Callers access the field directly.

### Mechanical Test

A method IS a trivial accessor when **all** of these hold:

1. Body is a single expression or assignment statement.
2. It reads or writes exactly one field of `self`:
   - `self.field_name` or `self.0` (read)
   - `self.field_name = expr` or `self.0 = expr` (write)
3. That field is `pub` (or `pub(crate)` — any visibility that allows direct access at the call site).
4. The method is not required by a trait implementation.

### Examples

```
// ✗ WRONG — trivial getter, field is pub
fn tick(&self) -> u64 { self.0 }

// ✗ WRONG — trivial setter, field is pub
fn set_tick(&mut self, val: u64) { self.0 = val }

// ✓ OK — trait impl
impl Deref for Wrapper {
    type Target = Inner;
    fn deref(&self) -> &Inner { &self.0 }
}

// ✓ OK — consuming builder (self → Self)
fn with_timeout(self, ms: u64) -> Self { Self { timeout: ms, ..self } }

// ✓ OK — has logic (comparison, not a naked field read)
fn is_local(&self, state: &PeerState) -> bool { self.0 == state.local_peer_id }

// ✓ OK — field is pub(crate) or private (encapsulation)
fn inner(&self) -> &Inner { &self.inner }   // inner: Inner, not pub
```

### Relationship to Rule 8 (Testing)

Rule 8 exempts trivial accessors from requiring a `test_usage` test. This rule goes further: they must not exist at all. If removing a trivial accessor and its test file would leave a directory with no remaining methods, the directory (and its `mod.rs`) MAY also be removed.

## 13. No Positional Struct Field Access

Never access struct fields by position (`.0`, `.1`, ...) instead of by name. All struct definitions MUST use named fields.

### Banned

- Reading: `foo.0`, `foo.1`
- Writing: `foo.0 = val`, `foo.1 = val`
- Modify: `foo.0 += 1`, `foo.1.saturating_sub(1)`

### Exceptions

- Types from **external crates** (their definition is not under your control, e.g., Bevy's `Text(pub Vec<TextSection>)`).
- **Anonymous tuples** (`pair.0` for `(i32, i32)`) — tuples are inherently positional.

```
// ✗ WRONG — tuple struct forces .0 on callers
pub struct PlayerId(pub u64);
fn check(id: &PlayerId) -> bool { id.0 == 0 }

// ✓ CORRECT — named field is self-documenting
pub struct PlayerId { pub value: u64 }
fn check(id: &PlayerId) -> bool { id.value == 0 }

// ✓ OK — external crate, cannot rename
text.0 = format!("{}", count);

// ✓ OK — anonymous tuple, positional by nature
fn midpoint(pair: (f32, f32)) -> f32 { (pair.0 + pair.1) / 2.0 }
```

### Rationale

`owner.peer_id` tells you what the field is at the call site; `owner.0` forces the reader to look up the struct definition. Named fields are self-documenting and survive refactoring — renaming a field updates all callers, while adding a new positional field silently shifts `.0` to `.1`.

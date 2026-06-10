# Atomic File Structure Examples

These examples demonstrate the atomic file decomposition pattern for a `Config` struct with methods.

## Directory Layout

```
Config.rs               # struct + Default + thin delegate impl blocks
ConfigMethod/
  mod.rs                # pub mod declarations + pub use flattening
  new.rs                # pub fn new() -> Config + tests
  coop.rs               # pub fn coop() -> Config + tests
  with_timeout.rs       # pub fn with_timeout(cfg: Config, ms: u64) -> Config + tests
```

> ⚠️ **Replace `{{module}}` with the actual module name (e.g., `p2p`, `auth`).**

## Struct File (`Config.rs`)

```rust
// Config.rs
use crate::{{module}}::ConfigMethod;

pub struct Config {
    pub timeout_secs: u64,
    ...
}

impl Default for Config {
    fn default() -> Self { ... }
}

#[rustfmt::skip]
impl Config {
    pub fn new() -> Self { ConfigMethod::new() }
    pub fn coop() -> Self { ConfigMethod::coop() }
    pub fn with_timeout(self, ms: u64) -> Self { ConfigMethod::with_timeout(self, ms) }
}

#[rustfmt::skip]
impl fmt::Display for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { ConfigMethod::fmt(self, f) }
}
```

> ⚠️ **Replace `{{module}}` with the actual module name.**

## Method File (`ConfigMethod/new.rs`)

```rust
// ConfigMethod/new.rs
use crate::{{module}}::Config;

pub fn new() -> Config { Config::default() }

#[cfg(test)]
mod tests {
    use crate::{{module}}::Config;
    use super::new;

    #[test]
    fn test_usage() {
        let config = new();
        assert!(config.enable_mdns);
    }
}
```

> ⚠️ **Replace `{{module}}` with the actual module name.**

## Method File (`ConfigMethod/with_timeout.rs`)

```rust
// ConfigMethod/with_timeout.rs
use crate::{{module}}::Config;

pub fn with_timeout(cfg: Config, ms: u64) -> Config {
    Config { connection_timeout_ms: ms, ..cfg }
}

#[cfg(test)]
mod tests {
    use crate::{{module}}::Config;
    use super::with_timeout;

    #[test]
    fn test_usage() {
        let config = with_timeout(Config::default(), 5000);
        assert_eq!(config.connection_timeout_ms, 5000);
    }
}
```

> ⚠️ **Replace `{{module}}` with the actual module name.**

## Trait Method File (`ConfigMethod/fmt.rs`)

```rust
// ConfigMethod/fmt.rs
use crate::{{module}}::Config;
use std::fmt;

pub fn fmt(cfg: &Config, f: &mut fmt::Formatter<'_>) -> fmt::Result {
    write!(f, "Config(timeout: {})", cfg.timeout_secs)
}

#[cfg(test)]
mod tests {
    use crate::{{module}}::Config;

    #[test]
    fn test_usage() {
        let config = Config::default();
        // Display is called through the Config.rs delegate
        let s = format!("{}", config);
        assert!(s.starts_with("Config"));
    }
}
```

> ⚠️ **Replace `{{module}}` with the actual module name.**

## Module Flattening (`ConfigMethod/mod.rs`)

```rust
// ConfigMethod/mod.rs
pub mod new;
pub mod coop;
pub mod with_timeout;
pub mod fmt;

pub use new::new;
pub use coop::coop;
pub use with_timeout::with_timeout;
pub use fmt::fmt;
```

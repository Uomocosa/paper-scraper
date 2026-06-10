---
name: freenet-integration
description: |
  Bevy-Freenet plugin patterns. Use when working with src/ modules that
  integrate the freenet crate (p2p networking, contracts, distributed
  state) into a Bevy ECS application. Covers runtime bridging between
  tokio-based freenet and Bevy's AsyncComputeTaskPool, event translation,
  contract lifecycle, and Plugin configuration.
---

# Freenet + Bevy Integration Patterns

## 1. Freenet API Surface (for Bevy Integration)

### Crate: `freenet` 0.2.68

Key types used by the Bevy plugin:

| Type | Path | Purpose |
|------|------|---------|
| `Config` | `freenet::config::Config` | Peer configuration (serde, clone, `Arc`-wrapped) |
| `OperationMode` | `freenet::local_node::OperationMode` | Local-only vs network mode |
| `NodeConfig` | `freenet::local_node::NodeConfig` | Builder for creating network-connected nodes |
| `Executor` | `freenet::local_node::Executor` | Contract execution engine (local mode) |
| `Node` | `freenet::Node` | Running network node (holds `ShutdownHandle`) |
| `ShutdownHandle` | `freenet::ShutdownHandle` | Triggers graceful node shutdown |
| `run_local_node` | `freenet::run_local_node` | Start a local-only node (async, never returns) |
| `run_network_node` | `freenet::run_network_node` | Start a network node (async, never returns) |

### Crate: `freenet-stdlib` 0.8.1

| Type | Path | Purpose |
|------|------|---------|
| `ClientRequest` | `freenet_stdlib::client_api::client_events::ClientRequest` | Request from app to contract |
| `HostResponse` | `freenet_stdlib::client_api::client_events::HostResponse` | Response from contract to app |
| `ContractRequest` | `freenet_stdlib::client_api::client_events::ContractRequest` | Contract-specific request |
| `ContractContainer` | `freenet_stdlib::versioning::ContractContainer` | Contract WASM blob |
| `WrappedState` | `freenet_stdlib::contract_interface::wrapped::WrappedState` | Contract state |

## 2. Runtime Bridge (tokio ↔ Bevy AsyncComputeTaskPool)

Freenet is built on tokio. Bevy uses its own task system. The bridge pattern:

### Startup: Spawn freenet on AsyncComputeTaskPool

```rust
// In plugin build():
let runtime = tokio::runtime::Runtime::new()?;
let node = /* build NodeConfig → Node */;
let shutdown_handle = node.shutdown_handle();

// Spawn freenet's infinite async loop on a separate thread via Bevy's task pool
let task = async move {
    freenet::run_network_node(node).await
};
// Use std::thread spawn for the tokio runtime, then poll within
std::thread::spawn(move || {
    runtime.block_on(task)
});
```

Note: `freenet::Node` is `!Sync`, so it cannot be shared across threads. The node runs on its own thread; communication happens through channels.

### Shutdown: Use ShutdownHandle

Store `ShutdownHandle` as a Bevy `Resource`. On `Plugin` drop or via a system, call `shutdown_handle.shutdown()`.

## 3. Event Translation (freenet → Bevy Message)

Freenet's `Executor` and `ClientEventsProxy` produce `HostResponse` values. These must be translated to Bevy `Message` types consumed by game systems.

```rust
use bevy::prelude::Message;

#[derive(Message, Debug, Clone)]
pub enum FreenetEvent {
    ContractResponse { contract_id: String, data: Vec<u8> },
    PeerConnected { peer_id: String },
    PeerDisconnected { peer_id: String },
    Error { description: String },
}
```

A poll system runs on `FixedUpdate` schedule, drains freenet's channel, and writes translated events via `MessageWriter<FreenetEvent>`.

## 4. Plugin Configuration

The plugin struct carries an `OperationMode` enum to select local vs network:

```rust
pub enum Mode {
    Local { contracts_dir: PathBuf },
    Network { bind_ip: IpAddr, bind_port: u16, gateways: Vec<InitPeerNode> },
}

pub struct Plugin {
    pub mode: Mode,
    pub data_dir: PathBuf,
}
```

- **Local mode:** Creates an `Executor` via `Executor::from_config_local()`, runs `run_local_node(executor, ws_config)`.
- **Network mode:** Creates a `NodeConfig` via `NodeConfig::new(config)`, optionally calls `add_gateway()`, builds the `Node`, runs `run_network_node(node)`.

## 5. Error Handling

Use `thiserror` for strongly typed plugin errors:

```rust
#[derive(Error, Debug)]
pub enum Error {
    #[error("Freenet configuration error: {0}")]
    Config(String),
    #[error("Freenet runtime error: {0}")]
    Runtime(#[from] anyhow::Error),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}
```

## 6. Testing Patterns

### Testing contract execution without networking

Use `Executor::new_mock()` (disk-backed state) or `Executor::new_mock_in_memory()` (fully in-memory for deterministic simulation).

```rust
let mut executor = Executor::new_mock_in_memory(
    "test",
    MockStateStorage::new(),
    None,
).await?;
```

### Testing with a minimal Bevy App

```rust
let mut app = App::new();
app.add_plugins(bevy_freenet::Plugin::new_local("./test_data"));
app.update();
```

## 7. Thread Safety Notes

- `freenet::Node` is `Send` but `!Sync` — owned by a single thread.
- `freenet::Executor<R, S>` is `Send` + `Sync` when `R: Send + Sync, S: Send + Sync`.
- `freenet::local_node::NodeConfig` is `Send` + `Sync`.
- Communication between the freenet thread and Bevy world MUST use channels (tokio `mpsc` or `crossbeam`).

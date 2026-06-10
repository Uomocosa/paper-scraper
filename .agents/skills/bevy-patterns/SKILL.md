---
name: bevy-patterns
description: Bevy engine patterns for projects using the Bevy game engine. Plugin struct+delegate separation, Component/Resource/Message types, system conventions (Res/ResMut/Query/Commands/MessageWriter), testing with App, plugin composition, internal module layout, and derive macro reference for bevy ≥ 0.18. Only load if Cargo.toml has a bevy dependency.
---

# BEVY-SPECIFIC SYNTAX & PATTERNS

Bevy engine patterns for Rust projects that depend on `bevy`. This skill may override general conventions where Bevy idioms differ.

**Targets bevy ≥ 0.18.** For older versions, adjust `Message`/`MessageWriter`/`MessageReader` to `Event`/`EventWriter`/`EventReader` accordingly.

## 1. Bevy Module & File Patterns

### Plugin Struct + Delegate Separation

Separate the Plugin struct definition from its `impl Plugin for ...` trait implementation. The trait impl in `StructName.rs` is a thin delegate calling a free function in `{Type}Method/` per the atomic file structure rule:

```
P2pPlugin.rs                # struct P2pPlugin { ... } — definition only
                            # + impl Plugin for P2pPlugin { fn build(...) {
                            #     P2pPluginMethod::build(self, app) } }
P2pPluginMethod/
  mod.rs                    # pub mod declarations + pub use flattening
  build.rs                  # pub fn build(plugin: &P2pPlugin, app: &mut App)
```

- The function file inside `{Type}Method/` follows snake_case naming — e.g., `build.rs` for `fn build()`.
- The thin delegate `impl Plugin for ...` block in `StructName.rs` MUST be annotated with `#[rustfmt::skip]` and kept as single-line methods (per the thin delegate convention).

### Component Files

`#[derive(Component)]` structs go in the `component/` subdirectory. Each in its own atomic file:

```rust
// component/ClickCounter.rs
use bevy::prelude::Component;

#[derive(Component)]
pub struct ClickCounter { pub count: u32 }
```

### Resource Files

`#[derive(Resource)]` structs go in the `resource/` subdirectory. Each in its own atomic file:

```rust
// resource/NetworkState.rs
use bevy::prelude::Resource;

#[derive(Resource)]
pub struct NetworkState {
    pub connected_peers: Vec<PeerId>,
}
```

### Event Types

Use `#[derive(Message)]` for event enums:

```rust
// Event.rs
use bevy::prelude::Message;

#[derive(Message, Debug, Clone)]
pub enum Event {
    DiscoveredPlayer(PeerId),
    JoinRequest(PeerId),
    PlayerJoined(PeerId),
    PlayerLeft(PeerId),
}
```

Events are consumed via `MessageWriter<T>` / `MessageReader<T>` (the newer Bevy API replacing `EventWriter`/`EventReader`).

## 2. Bevy System Conventions

Systems are plain functions. File naming follows the function name (snake_case).

### System Parameters

Use `Res<T>` / `ResMut<T>` for resources, `Query<&T, &mut T>` for components, `Commands` for spawning, `MessageWriter<T>` / `MessageReader<T>` for events:

```rust
// poll_network.rs
pub fn poll_network(
    mut session: ResMut<Session>,
    mut input_buffer: ResMut<RemoteInputBuffer>,
    mut network_state: ResMut<NetworkState>,
    mut peer_state: ResMut<PeerState>,
    mut events: MessageWriter<p2p::Event>,
) { ... }
```

### System Registration

Register systems with `app.add_systems()`:

```rust
// P2pPluginMethod/build.rs
pub fn build(plugin: &P2pPlugin, app: &mut App) {
    app.init_resource::<Tick>()
       .init_resource::<NetworkState>()
       .insert_resource(Session::new(...))
       .add_systems(FixedUpdate, (
           poll_network,
           log_peer_count,
           broadcast,
           apply_remote_inputs,
       ));
}
```
```

Use `FixedUpdate` for fixed-timestep game logic, `Update` for per-frame UI/input logic.

## 3. Bevy Testing Patterns

When a system requires a Bevy `App` context, construct a minimal working `App` inside the test:

```rust
// detect_click.rs
pub fn detect_click(
    mut query: Query<(&Owner, &mut ClickCounter, &GlobalTransform)>,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    windows: Query<&Window>,
) {
    if !mouse_button_input.just_pressed(MouseButton::Left) { return; }
    for (_owner, mut counter, _transform) in &mut query {
        counter.count += 1;
    }
}

#[cfg(test)]
mod tests {
    use bevy::prelude::*;

    #[test]
    fn test_usage() {
        let mut app = App::new();
        app.world_mut().spawn((
            Owner(PeerId::random()),
            ClickCounter { count: 0 },
            GlobalTransform::default(),
        ));

        let mut mouse_input = ButtonInput::<MouseButton>::default();
        mouse_input.press(MouseButton::Left);
        app.insert_resource(mouse_input);

        app.add_systems(Update, detect_click);
        app.update();

        let mut query = app.world_mut().query::<&ClickCounter>();
        let counter = query.single(app.world());
        assert_eq!(counter.count, 1);
    }
}
```

**Key patterns:**
- `App::new()` — fresh app instance
- `app.world_mut().spawn(...)` — spawn entities with component tuples
- `app.insert_resource(...)` — inject resources
- `app.add_systems(ScheduleName, system_fn)` — register the system under test
- `app.update()` — run one frame
- `app.world_mut().query::<&T>()` — read back component data for assertions

### Testing Resource Initialization

```rust
// For systems that need `Res<T>` or `ResMut<T>`:
let mut app = App::new();
app.insert_resource(MyResource { ... });
app.insert_resource(OtherResource::default());
app.add_systems(Update, my_system);
app.update();
```

### Testing Events (Message)

For systems that read events via `MessageReader<T>`, emit events manually before `app.update()`:

```rust
let mut app = App::new();
app.add_message::<MyEvent>();
app.add_systems(Update, handle_event);
// Manually write an event (simulates what a sending system would do):
app.world_mut()
    .resource_mut::<Messages<MyEvent>>()
    .write(MyEvent::Variant(value));
app.update();
```

## 4. Bevy Plugin Composition

When composing multiple plugins, add them as a tuple. Order matters — `p2p::Plugin` must come before `sync::Plugin` since sync depends on networking resources:

```rust
// main.rs or plugin builder
app.add_plugins((
    p2p::Plugin::new(config),  // networking: swarm, connections
    sync::Plugin,               // sync: tick, input buffer, broadcast
));

// Game-mode plugins are added independently:
app.add_plugins((
    p2p::Plugin::new(config),
    sync::Plugin,
    boxes::GamePlugin,          // or clicker::GamePlugin, etc.
));
```

## 5. Common Bevy Derive Macros

| Derive | Used On | Purpose |
|--------|---------|---------|
| `#[derive(Component)]` | struct | Marks struct as an ECS component |
| `#[derive(Resource)]` | struct | Marks struct as a global singleton resource |
| `#[derive(Message)]` | struct/enum | Marks type as a Bevy event message |
| `#[derive(Bundle)]` | struct (optional) | Groups multiple components (use raw tuples instead by convention) |

## 6. Internal Subfolder Convention

Every top-level module MUST follow this internal structure when its corresponding types exist:

```
{module}/
  component/         — #[derive(Component)] types (omit if module has none)
  resource/          — #[derive(Resource)] types (omit if module has none)
  system/            — Bevy system functions
  {Type}Method/      — free functions for methods and trait impls (per atomic file structure rule)
  (flat files)       — plain structs, enums, free functions, error types
```

Only create `component/` or `resource/` directories when they contain at least one type. Empty directories clutter the tree and serve no purpose. If a module has no component or resource types, do not declare the submodule in `mod.rs`.

`{Type}Method/` directories live alongside their type file, whether that file is in `component/`, `resource/`, or the module root.

```
// Example: p2p module layout
p2p/
  mod.rs
  Config.rs              # struct + Default + thin delegate impl blocks
  ConfigMethod/          # method free functions (new, coop, with_*, etc.)
  Event.rs               # plain event enum
  component/
    mod.rs
    (Component types only)
  resource/
    mod.rs
    PeerState.rs         # #[derive(Resource)] + thin delegate impl blocks
    PeerStateMethod/     # accept_peer, add_connected_peer, ...
  system/
    mod.rs
    poll_network.rs          # Bevy system
    log_peer_count.rs        # Bevy system
```
Note — items in `component/`, `resource/`, and `system/` are NOT re-exported at the module root. Consumers import them through their full submodule path (e.g., `use crate::{{module}}::resource::{{Type}};`). This follows the general rule — the `{{submodule}}` template variable maps to one of these concrete names (`component`, `resource`, `system`, or a `{Type}Method/` directory).

## 7. System Placement

### Definition
A **system function** is any function registered with `app.add_systems()` (or any other schedule) inside a `{Type}Method/build.rs` file.

### Placement Rules

| Function type | Location | Example |
|---|---|---|
| Registered in `add_systems()` | `{module}/system/` | `p2p/system/poll_network.rs` |
| Plain helper (no SystemParams) | Module root, or inline in the calling system file as a private helper | `p2p/handle_incoming_message.rs` |
| Internal builder/spawn helper used only by one system | Same file as the calling system (private helper function) | `spawn_remote_player` inside `handle_player_join.rs` |

A function that takes a Bevy type as a plain reference (e.g., `&ButtonInput<KeyCode>`) is NOT a system — it is a helper and follows the same rule as any other plain function.

Consumers call system functions through the `system` submodule:
```
use crate::{{module}}::system;
system::{{function}}(...);
```

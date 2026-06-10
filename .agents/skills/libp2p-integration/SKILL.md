---
name: libp2p-integration
description: |
  libp2p networking patterns for Rust peer-to-peer applications. Use when
  working with src/ modules that establish direct p2p connections for
  real-time communication (position sync, messaging, streaming). Covers
  SwarmBuilder, transport stacks, stream protocols, identity management,
  and hybrid integration with freenet.
---

# libp2p Integration Patterns

**Target: libp2p 0.56.0** (latest). Key sub-crate versions: `libp2p-swarm` 0.47.0, `libp2p-identity` 0.2.12, `libp2p-core` 0.43.1.

## 1. Canonical SwarmBuilder Pattern

The `SwarmBuilder` uses a type-state builder pattern with distinct phases:

```rust
use libp2p::{noise, tcp, yamux, StreamProtocol};

let mut swarm = libp2p::SwarmBuilder::with_new_identity()  // IdentityPhase
    .with_tokio()                                            // ProviderPhase → TcpPhase
    .with_tcp(                                               // TcpPhase → DnsPhase
        tcp::Config::default(),
        noise::Config::new,
        yamux::Config::default,
    )?
    .with_dns()?                                             // DnsPhase → WebsocketPhase
    // .with_quic()?                                         // optional: QUIC transport
    // .with_websocket(...)?                                  // optional: WebSocket
    .with_behaviour(|key| MyBehaviour::new())?               // BehaviourPhase → SwarmPhase
    .with_swarm_config(|cfg| cfg)
    .build();
```

### Phase chain

| Phase | Method | Purpose |
|-------|--------|---------|
| `IdentityPhase` | `with_new_identity()` | Generate a random ed25519 keypair |
| `IdentityPhase` | `with_existing_identity(kp)` | Use a pre-existing keypair (for identity bridge) |
| `ProviderPhase` | `with_tokio()` | Use tokio async runtime |
| `TcpPhase` | `with_tcp(config, noise, yamux)` | TCP + Noise encryption + Yamux multiplexing |
| `DnsPhase` | `with_dns()` / `with_dns_config()` | DNS resolution for multiaddrs |
| `WebsocketPhase` | `.with_websocket(...)` | WebSocket transport |
| `QuicPhase` | `.with_quic()` | QUIC transport (optional) |
| `OtherTransportPhase` | `.with_other_transport(...)` | Custom transport |
| `BehaviourPhase` | `.with_behaviour(...)` | Define the network protocol |
| `SwarmPhase` / `BuildPhase` | `.build()` | Finalize and build the `Swarm` |

### Minimal setup (ping example)

```rust
use std::error::Error;
use libp2p::{noise, ping, tcp, yamux, Multiaddr, StreamProtocol, Stream};
use futures::prelude::*;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let mut swarm = libp2p::SwarmBuilder::with_new_identity()
        .with_tokio()
        .with_tcp(tcp::Config::default(), noise::Config::new, yamux::Config::default)?
        .with_behaviour(|_| ping::Behaviour::default())?
        .with_swarm_config(|cfg| cfg.with_idle_connection_timeout(std::time::Duration::from_secs(u64::MAX)))
        .build();

    swarm.listen_on("/ip4/0.0.0.0/tcp/0".parse()?)?;

    loop {
        match swarm.select_next_some().await {
            libp2p::swarm::SwarmEvent::NewListenAddr { address, .. } => {
                println!("Listening on {address:?}");
            }
            libp2p::swarm::SwarmEvent::Behaviour(event) => {
                println!("{event:?}");
            }
            _ => {}
        }
    }
}
```

## 2. Key Types

| Type | Path | Purpose |
|------|------|---------|
| `Swarm<B>` | `libp2p::Swarm` | Main network manager. Must be polled via `Stream` trait. |
| `PeerId` | `libp2p::PeerId` | Unique peer identifier (derived from public key) |
| `Multiaddr` | `libp2p::Multiaddr` | Self-describing network address (e.g. `/ip4/1.2.3.4/tcp/9000`) |
| `Stream` | `libp2p::Stream` | Bidirectional byte stream over yamux (implements `AsyncRead` + `AsyncWrite`) |
| `StreamProtocol` | `libp2p::StreamProtocol` | Protocol identifier string (must start with `/`) |
| `Keypair` | `libp2p::identity::Keypair` | Network identity keypair (ed25519, secp256k1, ecdsa, rsa) |
| `Transport` | `libp2p::Transport` | Trait defining *how* bytes are sent |
| `NetworkBehaviour` | `libp2p::swarm::NetworkBehaviour` | Trait defining *what* bytes and to *whom* |

## 3. Transport Options

### TCP + Noise + Yamux (standard, recommended)

```rust
.with_tcp(tcp::Config::default(), noise::Config::new, yamux::Config::default)?
```

- TCP for reliable transport
- Noise for encryption and authentication (XX handshake)
- Yamux for stream multiplexing over one connection

### QUIC (lower latency)

```rust
.with_quic()?
```

- Built-in encryption (TLS 1.3)
- No separate multiplexer needed
- 0-RTT connection establishment
- Available on non-WASM targets with `quic` feature

### Feature flags for `Cargo.toml`

```toml
libp2p = { version = "0.56", features = [
    "tcp", "noise", "yamux", "tokio", "dns",  # standard TCP stack
    "quic",                                     # optional: QUIC
    "ping",                                     # optional: keep-alive/diagnostics
    "request-response",                         # optional: req/res protocol
    "gossipsub",                                # optional: pub/sub
    "identify",                                 # optional: peer identification
] }
```

## 4. Identity Bridge (freenet ↔ libp2p)

Both freenet and libp2p support ed25519 keypairs. The same seed can derive both identities:

```rust
use libp2p::identity::Keypair;

/// Derive a libp2p Keypair from freenet's TransportKeypair.
/// Freenet uses ed25519 internally. libp2p can import the same key.
fn bridge_identity(secret_bytes: &[u8; 32]) -> Option<Keypair> {
    Keypair::ed25519_from_bytes(secret_bytes).ok()
}
```

This ensures `PeerId` (libp2p) and freenet's node identity are cryptographically bound — other peers can verify both layers come from the same entity.

### `with_existing_identity`

```rust
let libp2p_kp = bridge_identity(&freenet_secret).unwrap();
let mut swarm = libp2p::SwarmBuilder::with_existing_identity(libp2p_kp)
    .with_tokio()
    // ... rest of builder
```

## 5. Stream Protocol (for real-time data)

For game position sync, open a bidirectional stream over an established connection:

```rust
const POSITIONS_PROTO: StreamProtocol = StreamProtocol::new("/positions/1.0.0");

// On connection established, open a stream and send position updates:
// (This requires a custom NetworkBehaviour - see section 6)
```

The `Stream` type implements `AsyncRead` + `AsyncWrite`. Use `futures::io::AsyncReadExt` and `AsyncWriteExt` for `read_exact`, `write_all`, etc.

Binary protocol: use `bincode` for length-prefixed serialization:

```rust
use bincode::{serialize, deserialize};

#[derive(Serialize, Deserialize)]
struct Position {
    x: f32, y: f32, vx: f32, vy: f32, seq: u32, timestamp: f64,
}

async fn send_position(stream: &mut libp2p::Stream, pos: &Position) {
    let bytes = bincode::serialize(pos).unwrap();
    let len = (bytes.len() as u32).to_be_bytes();
    stream.write_all(&len).await.unwrap();
    stream.write_all(&bytes).await.unwrap();
}

async fn recv_position(stream: &mut libp2p::Stream) -> Position {
    let mut len_buf = [0u8; 4];
    stream.read_exact(&mut len_buf).await.unwrap();
    let len = u32::from_be_bytes(len_buf) as usize;
    let mut buf = vec![0u8; len];
    stream.read_exact(&mut buf).await.unwrap();
    bincode::deserialize(&buf).unwrap()
}
```

## 6. Custom NetworkBehaviour (for stream-based protocols)

For position sync, implement a simple behaviour that handles inbound/outbound streams:

```rust
use libp2p::stream::Stream;
use libp2p::swarm::{
    NetworkBehaviour, THandler, THandlerInEvent, THandlerOutEvent,
    ConnectionHandler, ConnectionHandlerEvent,
    keep_alive::Behaviour as KeepAlive,
};

// Simple behaviour that just opens a /positions/1.0.0 stream
// and sends/receives raw bytes.
// 
// For a full implementation, see libp2p's connection handler patterns.
// Alternatively, use `request_response` for simpler req/res.
```

For simpler cases, prefer `request_response` protocol which handles stream lifecycle:

```toml
libp2p = { version = "0.56", features = ["request-response"] }
```

```rust
use libp2p::request_response::{self, ProtocolSupport, ResponseChannel};

// Define a codec:
#[derive(Serialize, Deserialize)]
struct PositionRequest(Position);

impl request_response::Codec for PositionCodec { ... }

// In with_behaviour:
.with_behaviour(|key| {
    request_response::Behaviour::new(
        [(POSITIONS_PROTO, ProtocolSupport::Full)],
        PositionCodec,
    )
})?
```

## 7. Swarm Event Loop (async)

The `Swarm` implements `futures::stream::Stream`. Poll it in an async loop:

```rust
use futures::prelude::*;

loop {
    match swarm.select_next_some().await {
        SwarmEvent::Behaviour(request_response::Event::Message { peer, message, .. }) => {
            // Handle received position
        }
        SwarmEvent::ConnectionEstablished { peer_id, connection_id, .. } => {
            println!("Connected to {peer_id}");
        }
        SwarmEvent::ConnectionClosed { peer_id, .. } => {
            println!("Disconnected from {peer_id}");
        }
        _ => {}
    }
}
```

## 8. Integration with Bevy (polling the swarm)

libp2p's `Swarm` is `!Sync`, so it must be polled on a single thread. Integration patterns:

### A. Separate thread with channel
Spawn the tokio runtime on a background thread. The swarm loop sends events over an `mpsc` channel to Bevy.

```rust
let (tx, rx) = tokio::sync::mpsc::unbounded_channel();

std::thread::spawn(move || {
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async move {
        let mut swarm = build_swarm().await;
        loop {
            let event = swarm.select_next_some().await;
            tx.send(event).ok();
        }
    });
});
```

### B. Bevy system drains the channel

```rust
fn poll_swarm_events(events: Res<EventChannel<SwarmEvent>>) {
    while let Ok(event) = events.rx.try_recv() {
        // Translate to Bevy Messages
    }
}
```

## 9. Feature Requirements

| Feature | Adds | Use for |
|---------|------|---------|
| `tcp` | TCP transport | Reliable connections (required) |
| `noise` | Noise encryption | Encrypted authenticated streams (required) |
| `yamux` | Stream multiplexing | Multiple streams per connection (required) |
| `tokio` | Tokio async runtime | Async event loop (required for std) |
| `dns` | DNS resolution | Dial peers by hostname |
| `quic` | QUIC transport | Lower latency, 0-RTT |
| `request-response` | Req/res protocol | Simple request/response patterns |
| `gossipsub` | Pub/sub messaging | Broadcast messages |
| `ping` | Keep-alive | Connection health checking |
| `identify` | Peer identification | Learn peer's listening addresses |
| `kad` | Kademlia DHT | Distributed peer discovery |

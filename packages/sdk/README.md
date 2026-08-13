# @jiuwenswarm/sdk

TypeScript / JavaScript SDK for [JiuwenSwarm](../../README.md).

Works in **browser**, **Node.js**, and **React Native** without any extra
configuration. The `ws` npm package is an optional peer dependency needed
only for Node.js.

---

## Installation

```bash
npm install @jiuwenswarm/sdk        # browser / React Native
npm install @jiuwenswarm/sdk ws     # Node.js
```

---

## Quick start

```typescript
import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  onToken: (text) => process.stdout.write(text),
  onDone: (sessionId) => console.log("\nDone:", sessionId),
});

await client.connect();
client.send("Explain quantum entanglement in one paragraph.");
```

---

## Session management

```typescript
import { JiuwenSwarmClient, SessionManager } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({ url: "ws://localhost:19000/v1/ws" });
const sessions = new SessionManager(client);

await client.connect();
const session = await sessions.create("Research session");

client.send("What is the CAP theorem?", { sessionId: session.session_id });
```

---

## Reconnect configuration

The client reconnects automatically using exponential back-off:
1 s → 2 s → 5 s → 10 s → 30 s (capped).

```typescript
const client = new JiuwenSwarmClient({
  url: "wss://prod.example.com:19000/v1/ws",
  authToken: process.env.JIUWENSWARM_TOKEN,
  reconnect: {
    maxAttempts: 5,
    initialDelayMs: 1000,
    maxDelayMs: 30_000,
    factor: 2,
  },
});

client.on("reconnecting", (attempt, delayMs) => {
  console.log(`Reconnect attempt ${attempt} in ${delayMs} ms`);
});
```

Disable reconnect entirely:

```typescript
const client = new JiuwenSwarmClient({ url: "...", reconnect: false });
```

---

## Client-side tool handling

By default any `tool_call` envelope from the server is rejected with
`{ error: "not supported" }`. Supply `onToolCall` to handle it locally:

```typescript
const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  onToolCall: async (call) => {
    if (call.name === "get_location") {
      const pos = await navigator.geolocation.getCurrentPosition(/* … */);
      return JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude });
    }
    throw new Error(`Tool not implemented: ${call.name}`);
  },
});
```

---

## Events

```typescript
client.on("connected",    ()                          => console.log("connected"));
client.on("disconnected", (reason)                    => console.log("disconnected:", reason));
client.on("token",        (text, sessionId)           => process.stdout.write(text));
client.on("done",         (sessionId)                 => console.log("done:", sessionId));
client.on("error",        (message)                   => console.error("error:", message));
client.on("reconnecting", (attempt, delayMs)          => console.log(`retry ${attempt}`));
```

---

## Configuration reference

```typescript
interface ClientConfig {
  url: string;                          // "ws://host:19000/v1/ws"
  authToken?: string;
  onToken?: (text: string) => void;
  onDone?: (sessionId: string) => void;
  onError?: (message: string) => void;
  onToolCall?: (call: ToolCallEnvelope) => Promise<string>;
  reconnect?: ReconnectConfig | false;  // false = disable auto-reconnect
}

interface ReconnectConfig {
  maxAttempts?: number;      // default: Infinity
  initialDelayMs?: number;   // default: 1000
  maxDelayMs?: number;       // default: 30_000
  factor?: number;           // default: 2
}
```

---

## Building and testing

```bash
npm install
npm run build      # tsup → dist/index.cjs + dist/index.mjs + dist/index.d.ts
npm test           # vitest
npm run docs       # TypeDoc → docs/
npm run typecheck  # tsc --noEmit
```

---

## WebSocket protocol

The SDK speaks the JiuwenSwarm WebSocket envelope protocol v1 at
`ws://host:19000/v1/ws`. All existing envelope types are unchanged.
Two additive extensions apply when using this SDK:

- `ack` payload includes `"protocol_version": "1"`
- `connect` envelope includes `"client_type": "sdk"`

New fields may be added to any envelope. Fields are never removed or
renamed without a version bump to `"2"`.

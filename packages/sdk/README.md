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
const session = await client.sessions.create("My session");
client.sessions.setActive(session.id);
await client.send("Explain quantum entanglement in one paragraph.");
client.disconnect();
```

---

## Session management

Sessions are managed through `client.sessions` (`SessionManager`):

```typescript
// Create a session
const session = await client.sessions.create("Research");

// List sessions
const all = await client.sessions.list();

// Switch active session (local pointer only)
client.sessions.setActive(session.id);

// Delete a session
await client.sessions.delete(session.id);

// Switch active session on the server and update local state
const switched = await client.switchSession("sess_abc123");

// Rename a session
await client.renameSession(session.id, "My research project");
```

Create with an agent mode:

```typescript
import { AgentModeConstants } from "@jiuwenswarm/sdk";

const session = await client.sessions.create(
  "Team task",
  undefined,
  AgentModeConstants.TEAM,
);
```

---

## Sending messages

### `send()` — callback-based

Resolves when the server sends `done`.  Tokens are delivered via `onToken`.

```typescript
await client.send("What is the CAP theorem?");
```

Per-call options:

```typescript
import { ChannelIdConstants } from "@jiuwenswarm/sdk";
import { readFileSync } from "fs";

await client.send("Describe this diagram", {
  mode: "code",
  channelId: ChannelIdConstants.IDE,
  contextPrefix: "File: src/app.ts\n\n" + readFileSync("src/app.ts", "utf8"),
  sessionId: "sess_abc123",        // override active session
  modelName: "gpt-4o",             // per-request model override
  mediaItems: [
    {
      mime_type: "image/png",
      data: readFileSync("diagram.png").toString("base64"),
      name: "diagram.png",
    },
  ],
});
```

### `streamEvents()` — async generator

Yields strongly-typed `StreamEvent` objects:

```typescript
for await (const event of client.streamEvents("Summarise this", {
  mode: "agent",
  modelName: "claude-3-5-sonnet",
})) {
  switch (event.kind) {
    case "delta":     process.stdout.write(event.text); break;
    case "reasoning": console.log("[thinking]", event.text); break;
    case "tool_call": console.log("[tool]", event.name, event.arguments); break;
    case "tool_result": console.log("[tool_result]", event.content); break;
    case "status":    console.log("[status]", event.text); break;
    case "usage":     console.log("[usage] tokens:", event.inputTokens, "+", event.outputTokens); break;
    case "done":      console.log("\n[done]", event.sessionId); break;
    case "error":     console.error("[error]", event.message); break;
  }
}
```

### `interrupt()` — cancel current turn

Fire-and-forget. The running agent turn is cancelled; the next event from
the generator will be `done` or `error`.

```typescript
client.interrupt();
```

---

## Rewind (conversation undo)

```typescript
// Subscribe to server push events before connecting
client.on("rewindable", (messageId) => {
  console.log("Message rewindable:", messageId);
});
client.on("rewind_done", (messageId) => {
  console.log("Rewound to:", messageId);
});

// Rewind to the last user turn (omit messageId)
client.rewind();

// Rewind to a specific message
client.rewind("msg_abc123");
```

---

## Session export

```typescript
const result = await client.exportSession(session.id, "markdown"); // or "json", "html"

if (result.url) {
  console.log("Download URL:", result.url);
} else if (result.data) {
  // Inline base-64-encoded export
  const text = Buffer.from(result.data, "base64").toString("utf8");
  console.log(text.slice(0, 400));
}
```

---

## Session history

```typescript
const page1 = await client.getHistory(session.id, 1);
console.log(`Page 1/${page1.total_pages}`);
page1.messages.forEach((m) => console.log(m.role, m.content));

// Fetch subsequent pages
for (let p = 2; p <= page1.total_pages; p++) {
  const page = await client.getHistory(session.id, p);
  page.messages.forEach((m) => console.log(m.role, m.content));
}
```

---

## Memory and metrics

```typescript
// Gateway process / system memory
const stats = await client.getMemoryUsage();
console.log(`RSS: ${stats.process_rss_mb} MB, context: ${stats.context_tokens} tokens`);

// Periodic metrics push from the server
client.on("metrics", (info) => {
  console.log(
    `requests=${info.requests_total}  tokens=${info.tokens_total}` +
    `  sessions=${info.active_sessions}  uptime=${info.uptime_s}s`,
  );
});
```

---

## Models

```typescript
// List available models
const models = await client.listModels();
models.forEach((m) => console.log(m.id, m.active ? "(active)" : ""));

// Switch the session model
const newModelId = await client.switchModel("gpt-4o");
console.log("Switched to:", newModelId);

// Per-request model override (does not change the session default)
await client.send("Quick answer", { modelName: "gpt-4o-mini" });
```

---

## Skills / plugins

```typescript
// List installed skills
const skills = await client.listSkills();
skills.forEach((s) => console.log(s.name, s.enabled ? "on" : "off"));

// Enable a skill
await client.toggleSkill("web-search", true);

// Disable a skill
await client.toggleSkill("web-search", false);
```

---

## Human-in-the-loop (HITL)

When the agent needs confirmation it emits a `confirm_interrupt` stream event:

```typescript
for await (const event of client.streamEvents("Analyse this")) {
  if (event.kind === "confirm_interrupt") {
    // event.requestId, event.prompt, event.fields are available
    const answers: Record<string, string> = {};
    for (const field of event.fields ?? []) {
      answers[field.key] = "yes"; // or prompt the user interactively
    }
    client.sendAnswer(event.requestId, answers);
  }
}
```

---

## Tool handling

By default any `tool_call` from the server is rejected automatically.
Supply `onToolCall` to handle it:

```typescript
const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  onToolCall: async (call) => {
    if (call.name === "get_location") {
      return JSON.stringify({ lat: 51.5074, lng: -0.1278 });
    }
    throw new Error(`Tool not implemented: ${call.name}`);
  },
});
```

---

## Reconnect configuration

Auto-reconnect is enabled by default with exponential back-off
(1 s → 2 s → 4 s → … → 30 s, unlimited attempts):

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

client.on("reconnecting", (attempt, delayMs) =>
  console.log(`Reconnect attempt ${attempt} in ${delayMs} ms`),
);
```

Disable reconnect entirely:

```typescript
const client = new JiuwenSwarmClient({ url: "...", reconnect: false });
```

---

## RPC mode (IDE wire protocol)

The jiuwenswarm-ide plugin uses a correlated-RPC envelope format instead of
the flat protocol.  Enable `rpcMode` so the SDK can replace the IDE's
transport layer directly:

```typescript
const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  rpcMode: true,       // wrap outbound in {type:"req", method, params, id, ...}
  rpcChannelId: "ide", // inserted into every outbound envelope (default: "ide")
});
```

When enabled:

- Every outbound message is sent as:
  ```json
  {
    "id": "<uuid-v4>",
    "type": "req",
    "method": "chat.send",
    "params": { "content": "Hello", "session_id": "sess_..." },
    "channel_id": "ide",
    "timestamp": 1723744234.512
  }
  ```
- Inbound `{ "type": "res", "id": "...", "data": {...} }` envelopes are
  automatically unwrapped and dispatched as regular flat envelopes.
- Streaming events (`token`, `done`, `error`, `metrics`, `rewindable`, etc.)
  are delivered unchanged and handled normally.

---

## Events

```typescript
client.on("connected",    ()                   => console.log("connected"));
client.on("disconnected", (reason)             => console.log("disconnected:", reason));
client.on("reconnecting", (attempt, delayMs)   => console.log(`retry #${attempt} in ${delayMs}ms`));
client.on("metrics",      (info)               => console.log("tokens:", info.tokens_total));
client.on("rewindable",   (messageId)          => console.log("rewindable:", messageId));
client.on("rewind_done",  (messageId)          => console.log("rewind done:", messageId));
```

---

## Configuration reference

```typescript
interface ClientConfig {
  // Required
  url: string;                         // "ws://host:19000/v1/ws"

  // Authentication
  authToken?: string;                  // bearer token (optional in dev)

  // Callbacks
  onToken?: (text: string) => void;
  onDone?: (sessionId?: string) => void;
  onError?: (message: string) => void;
  onToolCall?: (call: ToolCallEnvelope) => Promise<string>;

  // Defaults for every send() / streamEvents() call
  mode?: AgentMode;                    // "agent" | "code" | "team" | "code.team"
  channelId?: ChannelId;              // "api"|"ide"|"browser"|"cli"|"jupyter"|"mobile"

  // Reconnect
  reconnect?: false | ReconnectConfig; // false = disable; omit = use defaults

  // RPC wire protocol (jiuwenswarm-ide compatibility)
  rpcMode?: boolean;                   // default: false
  rpcChannelId?: string;              // default: "ide"
}

interface ReconnectConfig {
  maxAttempts?: number;    // default: Infinity
  initialDelayMs?: number; // default: 1000
  maxDelayMs?: number;     // default: 30_000
  factor?: number;         // default: 2
}
```

### `StreamEventsOptions`

All fields are optional and override the client-level defaults for a single call:

```typescript
interface StreamEventsOptions {
  mode?: AgentMode;
  channelId?: ChannelId;
  contextPrefix?: string;    // prepended to prompt with "\n\n---\n\n"
  sessionId?: string;        // override active session
  mediaItems?: MediaItem[];  // images, audio, files
  modelName?: string;        // per-request model override
}
```

---

## Named constants

```typescript
import { AgentModeConstants, ChannelIdConstants } from "@jiuwenswarm/sdk";

AgentModeConstants.AGENT     // "agent"
AgentModeConstants.CODE      // "code"
AgentModeConstants.TEAM      // "team"
AgentModeConstants.CODE_TEAM // "code.team"
AgentModeConstants.DEFAULT   // "agent"

ChannelIdConstants.API      // "api"
ChannelIdConstants.IDE      // "ide"
ChannelIdConstants.BROWSER  // "browser"
ChannelIdConstants.CLI      // "cli"
ChannelIdConstants.JUPYTER  // "jupyter"
ChannelIdConstants.MOBILE   // "mobile"
```

---

## `sessionId` getter

After `connect()` resolves, `client.sessionId` returns the session ID assigned
by the server in the connection acknowledgement (available when the server
auto-creates a default session on connect):

```typescript
await client.connect();
console.log("Server session:", client.sessionId);
```

---

## Building and testing

```bash
npm install
npm run build      # tsup → dist/index.cjs + dist/index.mjs + dist/index.d.ts
npm test           # vitest
npm run typecheck  # tsc --noEmit
npm run docs       # TypeDoc → docs/
```

---

## WebSocket protocol

The SDK implements the JiuwenSwarm WebSocket envelope protocol v1 at
`ws://host:19000/v1/ws`.

Two additive fields are always present:
- `ack` envelope includes `"protocol_version": "1"`
- `connect` envelope includes `"client_type": "typescript-sdk"`

New envelope fields may be added at any time; fields are never removed or
renamed without a protocol version bump.

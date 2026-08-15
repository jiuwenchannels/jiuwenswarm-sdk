/**
 * rewind_export.ts — rewind a conversation, monitor live metrics, and export
 * a session as Markdown.
 *
 * Demonstrates:
 *   - client.on("rewindable", ...)     → server push when a message is rewindable
 *   - client.on("rewind_done", ...)    → server push when rewind completes
 *   - client.rewind(messageId?)        → fire-and-forget rewind to a message
 *   - client.on("metrics", ...)        → periodic gateway metrics push
 *   - client.exportSession(id, format) → download or inline session export
 *   - options.modelName                → per-request model override
 *
 * Requires: npm install @jiuwenswarm/sdk
 * Gateway:  ws://localhost:19000/v1/ws  (start with `jiuwenswarm serve`)
 */

import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  onToken: (text) => process.stdout.write(text),
  onDone: () => console.log("\n"),
});

// ---------------------------------------------------------------------------
// 1. Subscribe to server-push events before connecting
// ---------------------------------------------------------------------------

// Gateway metrics — emitted periodically (every ~30 s by default).
client.on("metrics", (info) => {
  console.log(
    `[metrics] requests=${info.requests_total}  tokens=${info.tokens_total}` +
    `  sessions=${info.active_sessions}  uptime=${info.uptime_s}s`,
  );
});

// Server tells us which messages are eligible for rewind.
const rewindableIds: string[] = [];
client.on("rewindable", (messageId) => {
  rewindableIds.push(messageId);
  console.log(`[rewindable] message ${messageId} can be rewound`);
});

// Server confirms a rewind completed.
client.on("rewind_done", (messageId) => {
  console.log(`[rewind_done] rewound to message ${messageId}`);
});

await client.connect();

// ---------------------------------------------------------------------------
// 2. Create a session and exchange a couple of turns to build history
// ---------------------------------------------------------------------------
const session = await client.sessions.create("Rewind demo");
client.sessions.setActive(session.id);

console.log("=== Turn 1 ===");
await client.send("What is the capital of France?");

console.log("=== Turn 2 (with model override) ===");
// Per-request model override — the IDE sends this as `model_name` in chat.send.
await client.send("What is the capital of Germany?", {
  modelName: "gpt-4o-mini",   // override just for this message
});

console.log("=== Turn 3 ===");
await client.send("And the capital of Japan?");

// ---------------------------------------------------------------------------
// 3. Rewind the conversation
//    Rewind to the last user turn (omit messageId), or to a specific message.
// ---------------------------------------------------------------------------
console.log("\n=== Rewind to last user turn ===");
client.rewind();   // fire-and-forget; rewind_done event arrives asynchronously

// If the server sent rewindable hints, rewind to a specific message instead:
if (rewindableIds.length > 0) {
  console.log(`\n=== Rewind to specific message: ${rewindableIds[0]} ===`);
  client.rewind(rewindableIds[0]);
}

// Give the server a moment to process the rewind before exporting.
await new Promise((r) => setTimeout(r, 1500));

// ---------------------------------------------------------------------------
// 4. Export the session
// ---------------------------------------------------------------------------
console.log("\n=== Export session as Markdown ===");
try {
  const exported = await client.exportSession(session.id, "markdown");

  if (exported.url) {
    console.log(`  Download URL: ${exported.url}`);
  } else if (exported.data) {
    // Inline base-64 data — decode and show first 400 chars.
    const text = Buffer.from(exported.data, "base64").toString("utf8");
    console.log("  Inline export (first 400 chars):");
    console.log(text.slice(0, 400));
  } else {
    console.log("  (no export data returned)");
  }
} catch (err) {
  console.warn("  exportSession not supported by this gateway version:", err);
}

// ---------------------------------------------------------------------------
// 5. JSON export
// ---------------------------------------------------------------------------
console.log("\n=== Export session as JSON ===");
try {
  const json = await client.exportSession(session.id, "json");
  if (json.data) {
    const parsed = JSON.parse(Buffer.from(json.data, "base64").toString("utf8"));
    console.log(`  messages in export: ${(parsed.messages ?? []).length}`);
  } else if (json.url) {
    console.log(`  JSON download URL: ${json.url}`);
  }
} catch (err) {
  console.warn("  JSON export not supported:", err);
}

client.disconnect();

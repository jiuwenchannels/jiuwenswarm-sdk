/**
 * session_detail.ts — rename, switch, and load history for a session.
 *
 * Demonstrates:
 *   - client.sessionId          → session ID from the connection ack
 *   - client.renameSession()    → update a session's human-readable title
 *   - client.switchSession()    → make an existing session the active one
 *   - client.getHistory()       → load paginated message history
 *   - client.getMemoryUsage()   → gateway process and system memory stats
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

await client.connect();

// ---------------------------------------------------------------------------
// 1. Session ID from the connection ack
//    The server may assign a default session on connect and return its ID in
//    the ack envelope.  Access it via client.sessionId.
// ---------------------------------------------------------------------------
console.log("=== Connection ack session ID ===");
console.log(`  client.sessionId = ${client.sessionId ?? "(none)"}`);

// ---------------------------------------------------------------------------
// 2. Create or resume a session with some history
// ---------------------------------------------------------------------------
const sessions = await client.sessions.list();
let workSession = sessions.find((s) => s.title === "History demo");

if (!workSession) {
  console.log("\n=== Creating 'History demo' session ===");
  workSession = await client.sessions.create("History demo");
  client.sessions.setActive(workSession.id);

  // Populate with a couple of turns so getHistory() has something to return.
  await client.send("What is the capital of France?");
  await client.send("And of Germany?");
} else {
  client.sessions.setActive(workSession.id);
}

console.log(`\nWorking session: ${workSession.id}  "${workSession.title}"`);

// ---------------------------------------------------------------------------
// 3. Rename the session
// ---------------------------------------------------------------------------
console.log("\n=== Rename session ===");
const timestamp = new Date().toISOString().slice(11, 19); // HH:MM:SS
const renamed = await client.renameSession(workSession.id, `History demo (${timestamp})`);
console.log(`  renamed → "${renamed.title}"`);

// ---------------------------------------------------------------------------
// 4. Switch to the session via switchSession()
//    This lets the gateway know which session is "active" for this connection.
// ---------------------------------------------------------------------------
console.log("\n=== Switch session ===");
const switched = await client.switchSession(workSession.id);
console.log(`  active session: ${switched.id}  "${switched.title}"`);
// SessionManager is updated automatically by _onSessionSwitched.
console.log(`  client.sessions.activeId = ${client.sessions.activeId}`);

// ---------------------------------------------------------------------------
// 5. Load history — page 1
// ---------------------------------------------------------------------------
console.log("\n=== History (page 1) ===");
const page1 = await client.getHistory(workSession.id, 1);
console.log(`  page ${page1.page} / ${page1.total_pages}  (${page1.messages.length} messages)`);
for (const msg of page1.messages) {
  const preview = msg.content.slice(0, 80).replace(/\n/g, " ");
  console.log(`  [${msg.role.padEnd(9)}] ${preview}${msg.content.length > 80 ? "…" : ""}`);
}

// Load subsequent pages if available.
for (let p = 2; p <= Math.min(page1.total_pages, 3); p++) {
  const page = await client.getHistory(workSession.id, p);
  console.log(`\n=== History (page ${p}) ===`);
  for (const msg of page.messages) {
    const preview = msg.content.slice(0, 80).replace(/\n/g, " ");
    console.log(`  [${msg.role.padEnd(9)}] ${preview}${msg.content.length > 80 ? "…" : ""}`);
  }
}

// ---------------------------------------------------------------------------
// 6. Memory usage
// ---------------------------------------------------------------------------
console.log("\n=== Gateway memory usage ===");
const mem = await client.getMemoryUsage();
const usedMb = mem.system_total_mb - mem.system_free_mb;
const usedPct = ((usedMb / mem.system_total_mb) * 100).toFixed(1);
console.log(`  Gateway RSS    : ${mem.process_rss_mb.toFixed(1)} MB`);
console.log(`  System RAM     : ${usedMb.toFixed(0)} / ${mem.system_total_mb.toFixed(0)} MB  (${usedPct}%)`);
if (mem.context_tokens !== undefined) {
  console.log(`  Context tokens : ${mem.context_tokens.toLocaleString()}`);
}

client.disconnect();

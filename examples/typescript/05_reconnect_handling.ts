/**
 * 05_reconnect_handling.ts — automatic and manual reconnect strategies.
 *
 * The client reconnects automatically after an unexpected disconnection using
 * exponential back-off (1 s → 2 s → 5 s → 10 s → 30 s, capped).
 *
 * Requires: npm install @jiuwenswarm/sdk
 * Gateway:  ws://localhost:19000/v1/ws  (start with `jiuwenswarm serve`)
 */

import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

// --- Automatic reconnect (default) ----------------------------------------

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  reconnect: {
    maxAttempts: 10,       // stop after 10 failed attempts (default: Infinity)
    initialDelayMs: 1000,
    maxDelayMs: 30_000,
    factor: 2,             // multiply delay by 2 each attempt
  },
  onToken: (text) => process.stdout.write(text),
});

// Observe reconnect lifecycle
client.on("disconnected", (reason) => {
  console.warn(`[ws] disconnected: ${reason}`);
});

client.on("reconnecting", (attempt, delayMs) => {
  console.log(`[ws] reconnecting in ${delayMs}ms (attempt ${attempt})`);
});

client.on("connected", () => {
  console.log("[ws] connected");
  // Re-activate the session after reconnect — sessions survive on the server
  client.sessions.refresh().then(() => {
    const active = client.sessions.active;
    if (active) client.sessions.setActive(active.id);
  });
});

await client.connect();

// --- Manual reconnect (opt-out of auto-reconnect) --------------------------

const manualClient = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  reconnect: false,
});

manualClient.on("disconnected", async () => {
  console.warn("Disconnected — attempting manual reconnect in 5 s");
  await new Promise((r) => setTimeout(r, 5000));
  await manualClient.connect();
});

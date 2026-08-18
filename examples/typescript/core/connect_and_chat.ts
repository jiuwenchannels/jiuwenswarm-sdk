/**
 * 01_connect_and_chat.ts — connect to the JiuwenSwarm WebSocket gateway
 * and send a single chat message.
 *
 * Requires: npm install @jiuwenswarm/sdk
 * Gateway:  ws://localhost:19000/ws  (start with `jiuwenswarm serve`)
 */

import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/ws",
  authToken: process.env.JIUWENSWARM_TOKEN,
  onToken: (text) => process.stdout.write(text),
  onDone: (sessionId) => console.log(`\n[done] session=${sessionId}`),
  onError: (msg) => console.error(`[error] ${msg}`),
});

await client.connect();

const session = await client.sessions.create("My first session");
client.sessions.setActive(session.id);

await client.send("Explain the event loop in JavaScript.");

// Disconnect when done
client.disconnect();

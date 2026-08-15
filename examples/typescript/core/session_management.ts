/**
 * 02_session_management.ts — list, resume, and create sessions.
 *
 * Requires: npm install @jiuwenswarm/sdk
 * Gateway:  ws://localhost:19000/v1/ws  (start with `jiuwenswarm serve`)
 */

import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({ url: "ws://localhost:19000/v1/ws" });
await client.connect();

// List existing sessions
const sessions = await client.sessions.list();
console.log(`${sessions.length} sessions found`);
sessions.forEach((s) => console.log(`  ${s.id}  ${s.title}`));

// Resume an existing session
const target = sessions.find((s) => s.title === "Research notes");
if (target) {
  client.sessions.setActive(target.id);
  await client.send("Continue where we left off.");
}

// Create a fresh session
const fresh = await client.sessions.create("New topic", "default");
client.sessions.setActive(fresh.id);
await client.send("Tell me about quantum entanglement.");

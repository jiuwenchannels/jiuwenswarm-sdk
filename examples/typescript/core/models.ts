/**
 * models.ts — discover available LLM models and switch the active backend.
 *
 * Demonstrates:
 *   - client.listModels()   → fetch all configured model backends
 *   - client.switchModel()  → hot-swap the active model mid-session
 *   - Sending a chat after switching to verify the new model responds
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
// 1. List available models
// ---------------------------------------------------------------------------
console.log("=== Available models ===");
const models = await client.listModels();

if (models.length === 0) {
  console.log("  (no models returned by gateway)");
} else {
  for (const m of models) {
    const active = m.active ? " <-- ACTIVE" : "";
    const ctx = m.context_length ? `  ctx: ${m.context_length.toLocaleString()}` : "";
    console.log(`  ${m.id.padEnd(30)} [${m.provider}]${ctx}${active}`);
  }
}

// ---------------------------------------------------------------------------
// 2. Switch to a different model
// ---------------------------------------------------------------------------
const activeModel = models.find((m) => m.active) ?? models[0];
const targetModel = models.find((m) => !m.active) ?? activeModel;

if (targetModel && targetModel.id !== activeModel?.id) {
  console.log(`\n=== Switching from "${activeModel?.id}" to "${targetModel.id}" ===`);
  const switched = await client.switchModel(targetModel.id);
  console.log(`  switched → ${switched}`);
} else {
  console.log("\n(only one model available — skipping switch)");
}

// ---------------------------------------------------------------------------
// 3. Create a session and send a chat with the new model
// ---------------------------------------------------------------------------
const session = await client.sessions.create("Model demo");
client.sessions.setActive(session.id);

console.log("\n=== Chat with active model ===");
process.stdout.write("Reply: ");
await client.send("Reply with the word PONG only.");

// ---------------------------------------------------------------------------
// 4. Switch back to the original model
// ---------------------------------------------------------------------------
if (activeModel && targetModel?.id !== activeModel.id) {
  console.log(`\n=== Restoring original model "${activeModel.id}" ===`);
  await client.switchModel(activeModel.id);
  console.log("  restored");
}

// ---------------------------------------------------------------------------
// 5. Multimodal — sending a chat with an image attachment
//    (Only works when the active model supports vision.)
// ---------------------------------------------------------------------------
/*
import { readFileSync } from "fs";

console.log("\n=== Multimodal: image + text ===");
const imageData = readFileSync("screenshot.png").toString("base64");

for await (const event of client.streamEvents("What is in this image?", {
  mediaItems: [{
    mime_type: "image/png",
    data: imageData,
    name: "screenshot.png",
  }],
})) {
  if (event.kind === "delta") process.stdout.write(event.text);
  if (event.kind === "done") console.log("\n[done]");
}
*/

client.disconnect();

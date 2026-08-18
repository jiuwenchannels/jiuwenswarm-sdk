/**
 * 04_knowledge_base_rest.ts — query the knowledge base via the REST API
 * from TypeScript, then inject the retrieved context into a chat message.
 *
 * The TypeScript SDK does not wrap the knowledge base directly — use the
 * REST API with fetch.
 *
 * Requires: npm install @jiuwenswarm/sdk
 * Gateway:  http://localhost:19001  (HTTP REST, start with `jiuwenswarm serve`)
 */

import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

async function queryKnowledgeBase(query: string): Promise<string[]> {
  const res = await fetch("http://localhost:19001/v1/knowledge/company-docs/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.JIUWENSWARM_TOKEN}`,
    },
    body: JSON.stringify({ query, top_k: 3 }),
  });
  const data = await res.json();
  return data.results.map((r: { text: string }) => r.text);
}

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/ws",
  authToken: process.env.JIUWENSWARM_TOKEN,
  onToken: (text) => process.stdout.write(text),
  onDone: () => console.log("\n[done]"),
});

await client.connect();
const session = await client.sessions.create("KB demo");
client.sessions.setActive(session.id);

// Retrieve context then inject into chat
const context = await queryKnowledgeBase("refund policy");
await client.send(
  `Using this context: ${context.join(" ")}. Answer: Can I return my order?`
);

client.disconnect();

/**
 * 07_stream_events.ts — Typed stream events via client.streamEvents()
 *
 * Demonstrates Phase 11 features:
 * - client.streamEvents() returning AsyncIterable<StreamEvent>
 * - Discriminated union switch on event.kind
 * - context_prefix injection
 * - AgentModeConstants and ChannelIdConstants
 * - client.interrupt() mid-stream
 *
 * Prerequisites:
 *   npm install @jiuwenswarm/sdk
 *   jiuwenswarm serve   # starts ws://localhost:19000
 */

import {
  JiuwenSwarmClient,
  AgentModeConstants,
  ChannelIdConstants,
  type StreamEvent,
} from "@jiuwenswarm/sdk";

// ---------------------------------------------------------------------------
// 1. Basic streaming with typed events
// ---------------------------------------------------------------------------

async function basicStreamEvents(): Promise<void> {
  console.log("=== 1. Basic stream events ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Stream events demo");
  client.sessions.setActive(session.id);

  let fullText = "";

  for await (const event of client.streamEvents("Explain async generators in TypeScript in 3 sentences.")) {
    switch (event.kind) {
      case "delta":
        process.stdout.write(event.text);
        fullText += event.text;
        break;

      case "reasoning":
        // Chain-of-thought step (only for models with visible reasoning)
        process.stdout.write(`\x1b[90m[think] ${event.text}\x1b[0m`);
        break;

      case "status":
        console.log(`\n\x1b[34m[status] ${event.status}\x1b[0m`);
        break;

      case "tool_call":
        console.log(`\n\x1b[33m[tool →] ${event.name}(${JSON.stringify(event.arguments)})\x1b[0m`);
        break;

      case "tool_result":
        console.log(`\n\x1b[32m[tool ←] ${event.callId}: ${event.result ?? event.error}\x1b[0m`);
        break;

      case "usage":
        console.log(
          `\n\x1b[90m[usage] in=${event.inputTokens} out=${event.outputTokens}` +
          (event.costUsd !== undefined ? ` cost=$${event.costUsd.toFixed(4)}` : "") +
          "\x1b[0m",
        );
        break;

      case "done":
        console.log(`\n\n[done] session=${event.sessionId ?? session.id}`);
        break;

      case "error":
        console.error(`\n[error] ${event.message}`);
        break;
    }
  }

  console.log("\nFull response length:", fullText.length);
  client.disconnect();
}

// ---------------------------------------------------------------------------
// 2. AgentMode and ChannelId constants
// ---------------------------------------------------------------------------

async function modeAndChannelExample(): Promise<void> {
  console.log("\n=== 2. AgentMode + ChannelId ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    // Set defaults at the client level.
    mode: AgentModeConstants.CODE,
    channelId: ChannelIdConstants.IDE,
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Code mode demo");
  client.sessions.setActive(session.id);

  console.log("Sending in CODE mode, IDE channel...");

  for await (const event of client.streamEvents(
    "Write a TypeScript function that computes the nth Fibonacci number.",
    {
      // Override mode per-call (CODE_TEAM uses a code-focused multi-agent team)
      mode: AgentModeConstants.CODE_TEAM,
      channelId: ChannelIdConstants.IDE,
    },
  )) {
    if (event.kind === "delta") process.stdout.write(event.text);
    if (event.kind === "done") console.log("\n[done]");
    if (event.kind === "error") console.error("[error]", event.message);
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 3. context_prefix — inject IDE context
// ---------------------------------------------------------------------------

async function contextPrefixExample(): Promise<void> {
  console.log("\n=== 3. context_prefix injection ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Context prefix demo");
  client.sessions.setActive(session.id);

  // Simulate IDE context: current open file content + git status
  const ideContext = `
# Currently open: src/auth/login.ts
\`\`\`typescript
export async function login(email: string, password: string): Promise<User> {
  const user = await db.users.findOne({ email });
  if (!user || !await bcrypt.compare(password, user.hash)) {
    throw new Error("Invalid credentials");
  }
  return user;
}
\`\`\`

# Git status: 1 unstaged change in login.ts
`.trim();

  console.log("Injecting IDE context...\n");

  for await (const event of client.streamEvents(
    "What security issues do you see in this login function?",
    {
      contextPrefix: ideContext,
      mode: AgentModeConstants.CODE,
      channelId: ChannelIdConstants.IDE,
    },
  )) {
    if (event.kind === "delta") process.stdout.write(event.text);
    if (event.kind === "done") console.log("\n[done]");
    if (event.kind === "error") console.error("[error]", event.message);
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 4. interrupt() — stop mid-stream
// ---------------------------------------------------------------------------

async function interruptExample(): Promise<void> {
  console.log("\n=== 4. interrupt() mid-stream ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Interrupt demo");
  client.sessions.setActive(session.id);

  let tokenCount = 0;

  console.log("Streaming... will interrupt after 10 tokens\n");

  for await (const event of client.streamEvents(
    "Write a very long essay about the history of computing.",
  )) {
    if (event.kind === "delta") {
      process.stdout.write(event.text);
      tokenCount++;
      if (tokenCount >= 10) {
        console.log("\n\n[interrupting after", tokenCount, "tokens]");
        client.interrupt();
        // The generator will finish once the server acknowledges the interrupt.
      }
    }
    if (event.kind === "done") console.log("[done — interrupted]");
    if (event.kind === "error") console.log("[stream ended after interrupt]");
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 5. Collect all events for post-processing
// ---------------------------------------------------------------------------

async function collectAllEvents(): Promise<void> {
  console.log("\n=== 5. Collect all events ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Collect demo");
  client.sessions.setActive(session.id);

  // Collect all events into an array for post-processing or logging.
  const allEvents: StreamEvent[] = [];

  for await (const event of client.streamEvents("What is the capital of France?")) {
    allEvents.push(event);
  }

  // Post-process
  const deltas = allEvents.filter((e) => e.kind === "delta");
  const toolCalls = allEvents.filter((e) => e.kind === "tool_call");
  const usage = allEvents.find((e) => e.kind === "usage");

  console.log("Total events:", allEvents.length);
  console.log("Delta count:", deltas.length);
  console.log("Tool calls:", toolCalls.length);

  if (usage && usage.kind === "usage") {
    console.log(`Usage: ${usage.inputTokens} in / ${usage.outputTokens} out`);
  }

  const fullText = deltas
    .filter((e): e is typeof e & { kind: "delta" } => e.kind === "delta")
    .map((e) => e.text)
    .join("");
  console.log("Full answer:", fullText);

  client.disconnect();
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  try {
    await basicStreamEvents();
    await modeAndChannelExample();
    await contextPrefixExample();
    await interruptExample();
    await collectAllEvents();
  } catch (err) {
    console.error("Fatal:", err instanceof Error ? err.message : err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

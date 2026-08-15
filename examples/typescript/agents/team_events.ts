/**
 * 08_team_events.ts — Team events and SwarmStateManager
 *
 * Demonstrates Phase 12 team coordination features:
 * - client.streamEvents() with mode:"team"
 * - TeamEvent subtypes flowing through the stream
 * - SwarmStateManager tracking live agent + task state
 * - snapshot(), activeAgents(), pendingTasks()
 *
 * Prerequisites:
 *   npm install @jiuwenswarm/sdk
 *   jiuwenswarm serve   # starts ws://localhost:19000
 */

import {
  JiuwenSwarmClient,
  SwarmStateManager,
  AgentModeConstants,
  type StreamEvent,
  type AgentState,
  type TaskState,
} from "@jiuwenswarm/sdk";

// ---------------------------------------------------------------------------
// Terminal color helpers
// ---------------------------------------------------------------------------

const C = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  cyan: "\x1b[36m",
  yellow: "\x1b[33m",
  green: "\x1b[32m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  red: "\x1b[31m",
};

function colorize(color: string, text: string): string {
  return `${color}${text}${C.reset}`;
}

// ---------------------------------------------------------------------------
// 1. Basic team stream with manual event handling
// ---------------------------------------------------------------------------

async function basicTeamStream(): Promise<void> {
  console.log("=== 1. Basic team stream ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Team research demo");
  client.sessions.setActive(session.id);

  console.log("Starting multi-agent research task...\n");

  for await (const event of client.streamEvents(
    "Research the impact of large language models on software engineering. " +
    "Use a researcher, analyst, and writer.",
    { mode: AgentModeConstants.TEAM },
  )) {
    switch (event.kind) {
      case "delta":
        process.stdout.write(event.text);
        break;

      case "team.member.spawned":
        console.log(
          colorize(C.cyan, `\n[team] Agent spawned: ${event.agentId}`) +
          (event.role ? colorize(C.dim, ` (${event.role})`) : ""),
        );
        break;

      case "team.member.status_changed":
        console.log(
          colorize(C.blue, `[team] ${event.agentId} → ${event.status}`),
        );
        break;

      case "team.task.created":
        console.log(
          colorize(C.yellow, `[team] Task ${event.taskId} created`) +
          colorize(C.dim, ` → ${event.assignedTo}: "${event.description}"`),
        );
        break;

      case "team.task.completed":
        console.log(
          colorize(C.green, `[team] Task ${event.taskId} completed`) +
          colorize(C.dim, ` by ${event.agentId}`),
        );
        break;

      case "team.handoff":
        console.log(
          colorize(C.magenta, `[team] Handoff: ${event.fromAgentId} → ${event.toAgentId}`) +
          (event.summary ? colorize(C.dim, `: "${event.summary}"`) : ""),
        );
        break;

      case "status":
        console.log(colorize(C.dim, `\n[status] ${event.status}`));
        break;

      case "usage":
        console.log(
          colorize(
            C.dim,
            `\n[usage] in=${event.inputTokens} out=${event.outputTokens}` +
            (event.costUsd !== undefined ? ` cost=$${event.costUsd.toFixed(5)}` : ""),
          ),
        );
        break;

      case "done":
        console.log(colorize(C.green, "\n\n[done]"));
        break;

      case "error":
        console.error(colorize(C.red, `\n[error] ${event.message}`));
        break;
    }
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 2. SwarmStateManager — automatic state tracking
// ---------------------------------------------------------------------------

async function swarmStateManagerDemo(): Promise<void> {
  console.log("\n=== 2. SwarmStateManager ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Swarm state demo");
  client.sessions.setActive(session.id);

  const swarm = new SwarmStateManager();

  console.log("Running team task with live swarm tracking...\n");

  for await (const event of client.streamEvents(
    "Write a technical blog post about WebSockets. Use a planner, researcher, and writer.",
    { mode: AgentModeConstants.TEAM },
  )) {
    // Feed every event into the state manager.
    swarm.feed(event);

    if (event.kind === "delta") {
      process.stdout.write(event.text);
    }

    // Print live swarm state on significant team events.
    if (
      event.kind === "team.member.spawned" ||
      event.kind === "team.task.created" ||
      event.kind === "team.task.completed" ||
      event.kind === "team.handoff"
    ) {
      printSwarmState(swarm);
    }

    if (event.kind === "done") {
      console.log(colorize(C.green, "\n\n[done] — final swarm state:"));
      printSwarmState(swarm);
    }
  }

  // Inspect specific helpers
  const activeAgents = swarm.activeAgents();
  const pendingTasks = swarm.pendingTasks();
  const { handoffs } = swarm.snapshot();

  console.log("\n--- Post-session summary ---");
  console.log(`Active agents:  ${activeAgents.length}`);
  console.log(`Pending tasks:  ${pendingTasks.length}`);
  console.log(`Total handoffs: ${handoffs.length}`);
  if (handoffs.length > 0) {
    console.log("Handoff chain:", handoffs.map((h) => `${h.fromAgentId}→${h.toAgentId}`).join(", "));
  }

  client.disconnect();
}

function printSwarmState(swarm: SwarmStateManager): void {
  const { agents, tasks } = swarm.snapshot();
  const agentList = [...agents.values()];
  const taskList = [...tasks.values()];

  if (agentList.length === 0 && taskList.length === 0) return;

  console.log("\n" + colorize(C.dim, "--- swarm state ---"));

  if (agentList.length > 0) {
    console.log(colorize(C.dim, "Agents:"));
    for (const a of agentList) {
      const statusColor = a.status === "working" ? C.yellow : a.status === "done" ? C.green : C.dim;
      console.log(
        `  ${colorize(statusColor, a.status.padEnd(8))} ${a.id}` +
        (a.role ? colorize(C.dim, ` (${a.role})`) : ""),
      );
    }
  }

  if (taskList.length > 0) {
    console.log(colorize(C.dim, "Tasks:"));
    for (const t of taskList) {
      const mark = t.completed ? colorize(C.green, "✓") : colorize(C.yellow, "·");
      console.log(`  ${mark} [${t.id}] ${t.description.slice(0, 60)}...`);
    }
  }

  console.log(colorize(C.dim, "-------------------\n"));
}

// ---------------------------------------------------------------------------
// 3. Reset and reuse between sessions
// ---------------------------------------------------------------------------

async function resetAndReuseDemo(): Promise<void> {
  console.log("\n=== 3. Reset and reuse SwarmStateManager ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });

  await client.connect();
  const swarm = new SwarmStateManager();

  // First session
  const session1 = await client.sessions.create("Session 1");
  client.sessions.setActive(session1.id);

  console.log("Running session 1...");
  for await (const event of client.streamEvents(
    "Research TypeScript decorators.",
    { mode: AgentModeConstants.TEAM },
  )) {
    swarm.feed(event);
    if (event.kind === "delta") process.stdout.write(event.text);
    if (event.kind === "done") console.log("\n[session 1 done]");
  }

  const snap1 = swarm.snapshot();
  console.log(`Session 1: ${snap1.agents.size} agents, ${snap1.tasks.size} tasks`);

  // Reset between sessions
  swarm.reset();
  console.log("Swarm state reset.");

  // Second session
  const session2 = await client.sessions.create("Session 2");
  client.sessions.setActive(session2.id);

  console.log("\nRunning session 2...");
  for await (const event of client.streamEvents(
    "Write a comparison of React and Vue.",
    { mode: AgentModeConstants.TEAM },
  )) {
    swarm.feed(event);
    if (event.kind === "delta") process.stdout.write(event.text);
    if (event.kind === "done") console.log("\n[session 2 done]");
  }

  const snap2 = swarm.snapshot();
  console.log(`Session 2: ${snap2.agents.size} agents, ${snap2.tasks.size} tasks`);

  client.disconnect();
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  try {
    await basicTeamStream();
    await swarmStateManagerDemo();
    await resetAndReuseDemo();
  } catch (err) {
    console.error("Fatal:", err instanceof Error ? err.message : err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

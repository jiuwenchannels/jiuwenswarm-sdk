/**
 * 09_skills_and_hitl.ts — Skills management and Human-in-the-Loop (HITL)
 *
 * Demonstrates Phase 12 features:
 * - client.listSkills() — fetch installed skills
 * - client.toggleSkill(id, enabled) — enable/disable skills
 * - client.sendAnswer(requestId, answers) — reply to confirm_interrupt events
 * - Full HITL workflow: stream → confirm_interrupt → answer → resume
 *
 * Prerequisites:
 *   npm install @jiuwenswarm/sdk
 *   jiuwenswarm serve   # starts ws://localhost:19000
 */

import * as readline from "readline";
import {
  JiuwenSwarmClient,
  type SkillInfo,
} from "@jiuwenswarm/sdk";

// ---------------------------------------------------------------------------
// 1. List and display installed skills
// ---------------------------------------------------------------------------

async function listSkillsDemo(): Promise<void> {
  console.log("=== 1. List installed skills ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/ws",
    reconnect: false,
  });

  await client.connect();

  const skills = await client.listSkills();

  if (skills.length === 0) {
    console.log("No skills installed.");
  } else {
    console.log(`${skills.length} skill(s) installed:\n`);
    for (const skill of skills) {
      const status = skill.enabled ? "\x1b[32m● enabled\x1b[0m" : "\x1b[31m○ disabled\x1b[0m";
      console.log(`  ${status}  \x1b[1m${skill.name}\x1b[0m (${skill.id})`);
      console.log(`         ${skill.description}`);
      if (skill.version) console.log(`         version: ${skill.version}`);
      console.log();
    }
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 2. Toggle a skill
// ---------------------------------------------------------------------------

async function toggleSkillDemo(): Promise<void> {
  console.log("=== 2. Toggle a skill ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/ws",
    reconnect: false,
  });

  await client.connect();

  // First, list skills to find the first disabled one (or use a specific ID).
  const skills = await client.listSkills();
  const webSearch = skills.find((s) => s.id === "web-search");

  if (!webSearch) {
    console.log('Skill "web-search" not found. Available IDs:');
    skills.forEach((s) => console.log(`  ${s.id}`));
    client.disconnect();
    return;
  }

  const newState = !webSearch.enabled;
  console.log(`web-search is currently ${webSearch.enabled ? "enabled" : "disabled"}.`);
  console.log(`Toggling to ${newState ? "enabled" : "disabled"}...`);

  const result = await client.toggleSkill("web-search", newState);
  console.log(`Done. web-search is now: ${result.enabled ? "enabled" : "disabled"}`);

  // Toggle back
  console.log("Restoring original state...");
  const restored = await client.toggleSkill("web-search", webSearch.enabled);
  console.log(`Restored. web-search is now: ${restored.enabled ? "enabled" : "disabled"}`);

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 3. Enable a skill before a chat turn, disable after
// ---------------------------------------------------------------------------

async function skillGatedChatDemo(): Promise<void> {
  console.log("\n=== 3. Skill-gated chat (enable → chat → disable) ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("Skill-gated demo");
  client.sessions.setActive(session.id);

  // Enable web search for this turn.
  console.log("Enabling web-search skill...");
  await client.toggleSkill("web-search", true);
  console.log("Enabled.\n");

  // Run the task that benefits from web search.
  console.log("Q: What are the most popular TypeScript frameworks in 2025?\n");

  for await (const event of client.streamEvents(
    "What are the most popular TypeScript frameworks in 2025? Search the web for current data.",
  )) {
    if (event.kind === "delta") process.stdout.write(event.text);
    if (event.kind === "status") console.log(`\n\x1b[34m[status] ${event.status}\x1b[0m`);
    if (event.kind === "tool_call") console.log(`\n\x1b[33m[tool] ${event.name}\x1b[0m`);
    if (event.kind === "done") console.log("\n");
    if (event.kind === "error") console.error("\n[error]", event.message);
  }

  // Disable web search after the turn.
  console.log("Disabling web-search skill...");
  await client.toggleSkill("web-search", false);
  console.log("Disabled.");

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 4. Human-in-the-Loop (HITL) — automated answers
// ---------------------------------------------------------------------------

async function hitlAutomatedDemo(): Promise<void> {
  console.log("\n=== 4. HITL — automated answers ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("HITL automated demo");
  client.sessions.setActive(session.id);

  // A map of automated responses to expected questions.
  // In production this could be your application's business logic.
  const automatedAnswers: Record<string, Record<string, string>> = {
    default: { confirm: "yes", proceed: "true" },
  };

  let interruptCount = 0;

  for await (const event of client.streamEvents(
    "Analyse this sensitive document and extract key financial figures. " +
    "Ask for confirmation before proceeding.",
  )) {
    switch (event.kind) {
      case "delta":
        process.stdout.write(event.text);
        break;

      case "confirm_interrupt":
        interruptCount++;
        console.log(`\n\n\x1b[33m[HITL interrupt #${interruptCount}]\x1b[0m`);
        console.log(`Question: "${event.question}"`);

        // Auto-respond
        const answers = automatedAnswers[event.requestId] ?? automatedAnswers["default"];
        console.log(`Auto-answering with: ${JSON.stringify(answers)}`);
        client.sendAnswer(event.requestId, answers);
        console.log("Answer sent. Resuming...\n");
        break;

      case "done":
        console.log(`\n\n\x1b[32m[done]\x1b[0m Total interrupts handled: ${interruptCount}`);
        break;

      case "error":
        console.error("\n\x1b[31m[error]\x1b[0m", event.message);
        break;
    }
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 5. Human-in-the-Loop — interactive terminal input
// ---------------------------------------------------------------------------

async function hitlInteractiveDemo(): Promise<void> {
  console.log("\n=== 5. HITL — interactive terminal ===\n");
  console.log("(This demo pauses and waits for your input when the agent asks a question.)\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/ws",
    reconnect: false,
  });

  await client.connect();
  const session = await client.sessions.create("HITL interactive demo");
  client.sessions.setActive(session.id);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const ask = (question: string): Promise<string> =>
    new Promise((resolve) => rl.question(question, resolve));

  for await (const event of client.streamEvents(
    "Help me refactor this codebase. Ask me before making any breaking changes.",
  )) {
    switch (event.kind) {
      case "delta":
        process.stdout.write(event.text);
        break;

      case "confirm_interrupt":
        console.log("\n\n\x1b[33m━━━ Agent needs your input ━━━\x1b[0m");
        console.log(`\x1b[1m${event.question}\x1b[0m\n`);

        const userInput = await ask("Your answer (press Enter to confirm with 'yes'): ");
        const answers: Record<string, string> = {
          response: userInput.trim() || "yes",
        };

        client.sendAnswer(event.requestId, answers);
        console.log("→ Sent. Continuing...\n");
        break;

      case "status":
        console.log(`\n\x1b[34m[${event.status}]\x1b[0m`);
        break;

      case "done":
        console.log("\n\n\x1b[32m[session complete]\x1b[0m");
        rl.close();
        break;

      case "error":
        console.error("\n\x1b[31m[error]\x1b[0m", event.message);
        rl.close();
        break;
    }
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// 6. Batch skill configuration utility
// ---------------------------------------------------------------------------

async function batchSkillConfig(
  desiredState: { [skillId: string]: boolean },
): Promise<void> {
  console.log("\n=== 6. Batch skill configuration ===\n");

  const client = new JiuwenSwarmClient({
    url: "ws://localhost:19000/ws",
    reconnect: false,
  });

  await client.connect();

  const skills = await client.listSkills();
  const skillMap = new Map<string, SkillInfo>(skills.map((s) => [s.id, s]));

  let changed = 0;
  const errors: string[] = [];

  for (const [id, enabled] of Object.entries(desiredState)) {
    const current = skillMap.get(id);
    if (!current) {
      errors.push(`Skill not found: ${id}`);
      continue;
    }
    if (current.enabled === enabled) {
      console.log(`  \x1b[2m${id}: already ${enabled ? "enabled" : "disabled"}, skipping\x1b[0m`);
      continue;
    }
    try {
      await client.toggleSkill(id, enabled);
      console.log(`  ✓ ${id}: ${current.enabled ? "enabled" : "disabled"} → ${enabled ? "enabled" : "disabled"}`);
      changed++;
    } catch (err) {
      errors.push(`Failed to toggle ${id}: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  console.log(`\nDone. ${changed} skill(s) changed.`);
  if (errors.length > 0) {
    console.error("Errors:");
    errors.forEach((e) => console.error(`  ✗ ${e}`));
  }

  client.disconnect();
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  try {
    await listSkillsDemo();
    await toggleSkillDemo();
    await skillGatedChatDemo();
    await hitlAutomatedDemo();
    // Skip interactive demo by default (requires terminal input):
    // await hitlInteractiveDemo();

    // Example: enable web-search + code-exec, disable image-gen
    await batchSkillConfig({
      "web-search": true,
      "code-exec": true,
      "image-gen": false,
    });
  } catch (err) {
    console.error("Fatal:", err instanceof Error ? err.message : err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

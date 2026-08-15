/**
 * Tests for Phase 12 — team events and SwarmStateManager.
 *
 * Covers:
 * - SwarmStateManager.feed() processes all TeamEvent subtypes
 * - snapshot() returns copies of internal Maps
 * - activeAgents() and pendingTasks() filters
 * - reset() clears all state
 * - Out-of-order events (status_changed before spawn)
 * - Team events flowing through client.streamEvents()
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SwarmStateManager } from "../src/swarm/SwarmStateManager";
import { JiuwenSwarmClient } from "../src/client/JiuwenSwarmClient";
import type { StreamEvent } from "../src/protocol/events";

// ---------------------------------------------------------------------------
// MockWebSocket (same pattern as other test files)
// ---------------------------------------------------------------------------

class MockWebSocket {
  readyState: number = 0;
  send = vi.fn<[string], void>();
  close = vi.fn<[number?, string?], void>();
  onopen: ((event: object) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: { code: number; reason: string }) => void) | null = null;

  simulateOpen(): void { this.readyState = 1; this.onopen?.({}); }
  simulateMessage(data: string): void { this.onmessage?.({ data }); }
  simulateClose(code = 1000, reason = ""): void {
    this.readyState = 3; this.onclose?.({ code, reason });
  }
  lastSent(): Record<string, unknown> {
    const calls = this.send.mock.calls;
    if (!calls.length) throw new Error("send() not called");
    return JSON.parse(calls.at(-1)![0]) as Record<string, unknown>;
  }
}

let currentMock: MockWebSocket;

function MockWSConstructor(_url: string): MockWebSocket {
  currentMock = new MockWebSocket();
  return currentMock;
}

function makeClient() {
  return new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
  });
}

function completeHandshake(mock: MockWebSocket): void {
  mock.simulateOpen();
  mock.simulateMessage(JSON.stringify({ type: "ack", protocol_version: "1.0" }));
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWSConstructor as unknown as typeof WebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// SwarmStateManager — feed() for member events
// ---------------------------------------------------------------------------

describe("SwarmStateManager — member events", () => {
  it("tracks a spawned agent with default idle status", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1", role: "researcher" });

    const snap = mgr.snapshot();
    expect(snap.agents.size).toBe(1);
    const agent = snap.agents.get("a1");
    expect(agent).toBeDefined();
    expect(agent!.id).toBe("a1");
    expect(agent!.role).toBe("researcher");
    expect(agent!.status).toBe("idle");
  });

  it("tracks a spawned agent without a role", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a2" });
    const agent = mgr.snapshot().agents.get("a2");
    expect(agent!.role).toBeUndefined();
  });

  it("updates agent status on status_changed", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });
    mgr.feed({ kind: "team.member.status_changed", agentId: "a1", status: "working" });

    const agent = mgr.snapshot().agents.get("a1");
    expect(agent!.status).toBe("working");
  });

  it("creates an agent on status_changed even without a prior spawn event", () => {
    const mgr = new SwarmStateManager();
    // No spawn — status_changed arrives out of order
    mgr.feed({ kind: "team.member.status_changed", agentId: "a99", status: "working" });

    const agent = mgr.snapshot().agents.get("a99");
    expect(agent).toBeDefined();
    expect(agent!.status).toBe("working");
  });

  it("tracks multiple agents independently", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1", role: "researcher" });
    mgr.feed({ kind: "team.member.spawned", agentId: "a2", role: "writer" });
    mgr.feed({ kind: "team.member.status_changed", agentId: "a1", status: "working" });

    const snap = mgr.snapshot();
    expect(snap.agents.size).toBe(2);
    expect(snap.agents.get("a1")!.status).toBe("working");
    expect(snap.agents.get("a2")!.status).toBe("idle");
  });
});

// ---------------------------------------------------------------------------
// SwarmStateManager — task events
// ---------------------------------------------------------------------------

describe("SwarmStateManager — task events", () => {
  it("tracks a created task", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({
      kind: "team.task.created",
      taskId: "t1",
      assignedTo: "a1",
      description: "Search for papers",
    });

    const snap = mgr.snapshot();
    expect(snap.tasks.size).toBe(1);
    const task = snap.tasks.get("t1");
    expect(task).toBeDefined();
    expect(task!.assignedTo).toBe("a1");
    expect(task!.description).toBe("Search for papers");
    expect(task!.completed).toBe(false);
    expect(task!.completedAt).toBeUndefined();
  });

  it("marks a task as completed", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.task.created", taskId: "t1", assignedTo: "a1", description: "Write" });
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });
    mgr.feed({ kind: "team.member.status_changed", agentId: "a1", status: "working" });
    mgr.feed({ kind: "team.task.completed", taskId: "t1", agentId: "a1" });

    const task = mgr.snapshot().tasks.get("t1");
    expect(task!.completed).toBe(true);
    expect(task!.completedAt).toBeDefined();
  });

  it("sets agent status to idle after task completion", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });
    mgr.feed({ kind: "team.member.status_changed", agentId: "a1", status: "working" });
    mgr.feed({ kind: "team.task.created", taskId: "t1", assignedTo: "a1", description: "X" });
    mgr.feed({ kind: "team.task.completed", taskId: "t1", agentId: "a1" });

    const agent = mgr.snapshot().agents.get("a1");
    expect(agent!.status).toBe("idle");
  });
});

// ---------------------------------------------------------------------------
// SwarmStateManager — handoff events
// ---------------------------------------------------------------------------

describe("SwarmStateManager — handoff events", () => {
  it("records a handoff", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({
      kind: "team.handoff",
      fromAgentId: "a1",
      toAgentId: "a2",
      summary: "Done with research",
    });

    const snap = mgr.snapshot();
    expect(snap.handoffs.length).toBe(1);
    expect(snap.handoffs[0].fromAgentId).toBe("a1");
    expect(snap.handoffs[0].toAgentId).toBe("a2");
    expect(snap.handoffs[0].summary).toBe("Done with research");
    expect(snap.handoffs[0].at).toBeGreaterThan(0);
  });

  it("records multiple handoffs in order", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.handoff", fromAgentId: "a1", toAgentId: "a2" });
    mgr.feed({ kind: "team.handoff", fromAgentId: "a2", toAgentId: "a3" });

    const snap = mgr.snapshot();
    expect(snap.handoffs.length).toBe(2);
    expect(snap.handoffs[0].fromAgentId).toBe("a1");
    expect(snap.handoffs[1].fromAgentId).toBe("a2");
  });
});

// ---------------------------------------------------------------------------
// SwarmStateManager — query helpers
// ---------------------------------------------------------------------------

describe("SwarmStateManager — query helpers", () => {
  it("agent() returns the agent state or undefined", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });
    expect(mgr.agent("a1")).toBeDefined();
    expect(mgr.agent("missing")).toBeUndefined();
  });

  it("task() returns the task state or undefined", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.task.created", taskId: "t1", assignedTo: "a1", description: "X" });
    expect(mgr.task("t1")).toBeDefined();
    expect(mgr.task("missing")).toBeUndefined();
  });

  it("activeAgents() returns only working agents", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });
    mgr.feed({ kind: "team.member.spawned", agentId: "a2" });
    mgr.feed({ kind: "team.member.status_changed", agentId: "a1", status: "working" });

    const active = mgr.activeAgents();
    expect(active.length).toBe(1);
    expect(active[0].id).toBe("a1");
  });

  it("pendingTasks() returns only incomplete tasks", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.task.created", taskId: "t1", assignedTo: "a1", description: "A" });
    mgr.feed({ kind: "team.task.created", taskId: "t2", assignedTo: "a2", description: "B" });
    mgr.feed({ kind: "team.task.completed", taskId: "t1", agentId: "a1" });

    const pending = mgr.pendingTasks();
    expect(pending.length).toBe(1);
    expect(pending[0].id).toBe("t2");
  });
});

// ---------------------------------------------------------------------------
// SwarmStateManager — snapshot isolation + reset
// ---------------------------------------------------------------------------

describe("SwarmStateManager — snapshot isolation + reset", () => {
  it("snapshot() returns a copy — mutation does not affect internal state", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });

    const snap = mgr.snapshot();
    snap.agents.delete("a1"); // mutate the copy

    // Internal state should be unchanged
    expect(mgr.agent("a1")).toBeDefined();
  });

  it("reset() clears all state", () => {
    const mgr = new SwarmStateManager();
    mgr.feed({ kind: "team.member.spawned", agentId: "a1" });
    mgr.feed({ kind: "team.task.created", taskId: "t1", assignedTo: "a1", description: "X" });
    mgr.feed({ kind: "team.handoff", fromAgentId: "a1", toAgentId: "a2" });

    mgr.reset();

    const snap = mgr.snapshot();
    expect(snap.agents.size).toBe(0);
    expect(snap.tasks.size).toBe(0);
    expect(snap.handoffs.length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// SwarmStateManager — ignores non-team events
// ---------------------------------------------------------------------------

describe("SwarmStateManager — ignores non-team events", () => {
  it("does not throw or change state for delta events", () => {
    const mgr = new SwarmStateManager();
    expect(() => mgr.feed({ kind: "delta", text: "hello" })).not.toThrow();
    expect(mgr.snapshot().agents.size).toBe(0);
  });

  it("does not throw for done events", () => {
    const mgr = new SwarmStateManager();
    expect(() => mgr.feed({ kind: "done", sessionId: "s1" } as StreamEvent)).not.toThrow();
  });

  it("does not throw for error events", () => {
    const mgr = new SwarmStateManager();
    expect(() => mgr.feed({ kind: "error", message: "oops" })).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Team events flowing through client.streamEvents()
// ---------------------------------------------------------------------------

describe("team events through client.streamEvents()", () => {
  it("yields TeamMemberSpawnedEvent from the server", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const events: StreamEvent[] = [];
    const gen = client.streamEvents("Do team work", { mode: "team" });

    const iterPromise = (async () => {
      for await (const event of gen) {
        events.push(event);
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(
      JSON.stringify({ type: "team.member.spawned", agent_id: "a1", role: "researcher" }),
    );
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));

    await iterPromise;

    const spawned = events.find((e) => e.kind === "team.member.spawned");
    expect(spawned).toBeDefined();
    if (spawned && spawned.kind === "team.member.spawned") {
      expect(spawned.agentId).toBe("a1");
      expect(spawned.role).toBe("researcher");
    }
  });

  it("SwarmStateManager.feed() integrates with streamEvents()", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const swarm = new SwarmStateManager();
    const gen = client.streamEvents("Coordinate");

    const iterPromise = (async () => {
      for await (const event of gen) {
        swarm.feed(event);
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(
      JSON.stringify({ type: "team.member.spawned", agent_id: "a1", role: "writer" }),
    );
    currentMock.simulateMessage(
      JSON.stringify({
        type: "team.task.created",
        task_id: "t1",
        assigned_to: "a1",
        description: "Write summary",
      }),
    );
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));

    await iterPromise;

    expect(swarm.agent("a1")).toBeDefined();
    expect(swarm.task("t1")).toBeDefined();
    expect(swarm.task("t1")!.description).toBe("Write summary");
  });
});

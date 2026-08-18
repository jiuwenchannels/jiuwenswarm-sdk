/**
 * Tests for Phase 11 — typed stream events.
 *
 * Covers:
 * - parseStreamEvent() for all event kinds (legacy + E2A format)
 * - AgentModeConstants and ChannelIdConstants constant values
 * - JiuwenSwarmClient._applyContextPrefix() static helper
 * - client.streamEvents() — async generator lifecycle (delta, done, error)
 * - client.interrupt() — sends the correct envelope
 * - contextPrefix + mode + channelId forwarded through streamEvents()
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { parseStreamEvent } from "../src/protocol/events";
import { AgentModeConstants, ChannelIdConstants } from "../src/protocol/types";
import { JiuwenSwarmClient } from "../src/client/JiuwenSwarmClient";

// ---------------------------------------------------------------------------
// MockWebSocket (shared with client.test.ts pattern)
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
    this.readyState = 3;
    this.onclose?.({ code, reason });
  }
  lastSent(): Record<string, unknown> {
    const calls = this.send.mock.calls;
    if (!calls.length) throw new Error("send() not called");
    return JSON.parse(calls.at(-1)![0]) as Record<string, unknown>;
  }
  sentAt(i: number): Record<string, unknown> {
    return JSON.parse(this.send.mock.calls[i][0]) as Record<string, unknown>;
  }
}

let currentMock: MockWebSocket;

function MockWSConstructor(_url: string): MockWebSocket {
  currentMock = new MockWebSocket();
  return currentMock;
}

function makeClient(overrides: Partial<Parameters<typeof JiuwenSwarmClient>[0]> = {}) {
  return new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false,
    ...overrides,
  });
}

function completeHandshake(mock: MockWebSocket): void {
  mock.simulateOpen();
  mock.simulateMessage(
    JSON.stringify({
      type: "event",
      event: "connection.ack",
      payload: { protocol_version: "1.0" },
    }),
  );
}

/** Shorthand for a gateway event frame. */
function eventFrame(event: string, payload: Record<string, unknown> = {}): string {
  return JSON.stringify({ type: "event", event, payload });
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWSConstructor as unknown as typeof WebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// parseStreamEvent — legacy format
// ---------------------------------------------------------------------------

describe("parseStreamEvent — legacy format", () => {
  it("maps type:token → DeltaEvent", () => {
    const event = parseStreamEvent({ type: "token", text: "Hello" });
    expect(event).toEqual({ kind: "delta", text: "Hello" });
  });

  it("maps type:reasoning → ReasoningEvent", () => {
    const event = parseStreamEvent({ type: "reasoning", text: "Let me think..." });
    expect(event).toEqual({ kind: "reasoning", text: "Let me think..." });
  });

  it("maps type:status → StatusEvent (no agentId)", () => {
    const event = parseStreamEvent({ type: "status", status: "Searching..." });
    expect(event).toEqual({ kind: "status", status: "Searching...", agentId: undefined });
  });

  it("maps type:status → StatusEvent (with agentId)", () => {
    const event = parseStreamEvent({ type: "status", status: "Working", agent_id: "agent-1" });
    expect(event).toEqual({ kind: "status", status: "Working", agentId: "agent-1" });
  });

  it("maps type:tool_call → ToolCallEvent", () => {
    const event = parseStreamEvent({
      type: "tool_call",
      name: "search",
      arguments: { query: "typescript" },
      callId: "call-99",
    });
    expect(event).toEqual({
      kind: "tool_call",
      name: "search",
      arguments: { query: "typescript" },
      callId: "call-99",
    });
  });

  it("maps type:tool_result_server → ToolResultEvent (success)", () => {
    const event = parseStreamEvent({
      type: "tool_result_server",
      callId: "call-99",
      result: "42 results found",
    });
    expect(event).toEqual({
      kind: "tool_result",
      callId: "call-99",
      result: "42 results found",
      error: undefined,
    });
  });

  it("maps type:tool_result_server → ToolResultEvent (error)", () => {
    const event = parseStreamEvent({
      type: "tool_result_server",
      callId: "call-99",
      error: "timeout",
    });
    expect(event).toEqual({
      kind: "tool_result",
      callId: "call-99",
      result: undefined,
      error: "timeout",
    });
  });

  it("maps type:usage → UsageEvent", () => {
    const event = parseStreamEvent({
      type: "usage",
      input_tokens: 100,
      output_tokens: 200,
      cost_usd: 0.003,
    });
    expect(event).toEqual({
      kind: "usage",
      inputTokens: 100,
      outputTokens: 200,
      costUsd: 0.003,
    });
  });

  it("maps type:usage without cost_usd → costUsd undefined", () => {
    const event = parseStreamEvent({ type: "usage", input_tokens: 50, output_tokens: 75 });
    expect(event).toEqual({ kind: "usage", inputTokens: 50, outputTokens: 75, costUsd: undefined });
  });

  it("maps type:confirm_interrupt → ConfirmInterruptEvent", () => {
    const event = parseStreamEvent({
      type: "confirm_interrupt",
      request_id: "req-1",
      question: "Should I continue?",
    });
    expect(event).toEqual({
      kind: "confirm_interrupt",
      requestId: "req-1",
      question: "Should I continue?",
    });
  });

  it("maps type:done → DoneEvent (with session_id)", () => {
    const event = parseStreamEvent({ type: "done", session_id: "sess-abc" });
    expect(event).toEqual({ kind: "done", sessionId: "sess-abc" });
  });

  it("maps type:done → DoneEvent (no session_id)", () => {
    const event = parseStreamEvent({ type: "done" });
    expect(event).toEqual({ kind: "done", sessionId: undefined });
  });

  it("maps type:error → ErrorEvent", () => {
    const event = parseStreamEvent({ type: "error", message: "Something went wrong" });
    expect(event).toEqual({ kind: "error", message: "Something went wrong" });
  });

  it("returns null for type:ack", () => {
    expect(parseStreamEvent({ type: "ack", protocol_version: "1.0" })).toBeNull();
  });

  it("returns null for type:sessions", () => {
    expect(parseStreamEvent({ type: "sessions", sessions: [] })).toBeNull();
  });

  it("returns null for type:session_created", () => {
    expect(parseStreamEvent({ type: "session_created", session: {} })).toBeNull();
  });

  it("returns null for unknown types", () => {
    expect(parseStreamEvent({ type: "__unknown__" })).toBeNull();
  });

  it("returns null for envelope with no type field", () => {
    expect(parseStreamEvent({})).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// parseStreamEvent — E2A format
// ---------------------------------------------------------------------------

describe("parseStreamEvent — E2A format (response_kind)", () => {
  it("maps response_kind:e2a.chunk → DeltaEvent", () => {
    const event = parseStreamEvent({ response_kind: "e2a.chunk", type: "e2a", text: "chunk" });
    expect(event).toEqual({ kind: "delta", text: "chunk" });
  });

  it("maps response_kind:e2a.complete → DoneEvent", () => {
    const event = parseStreamEvent({ response_kind: "e2a.complete", type: "e2a", session_id: "s1" });
    expect(event).toEqual({ kind: "done", sessionId: "s1" });
  });

  it("maps response_kind:e2a.error → ErrorEvent", () => {
    const event = parseStreamEvent({ response_kind: "e2a.error", type: "e2a", message: "oops" });
    expect(event).toEqual({ kind: "error", message: "oops" });
  });

  it("response_kind takes priority over type when both present", () => {
    // An E2A envelope has type:"e2a" but response_kind carries the real kind.
    const event = parseStreamEvent({ response_kind: "e2a.chunk", type: "done", text: "x" });
    expect(event?.kind).toBe("delta");
  });
});

// ---------------------------------------------------------------------------
// parseStreamEvent — team events
// ---------------------------------------------------------------------------

describe("parseStreamEvent — team events", () => {
  it("maps team.member.spawned", () => {
    const event = parseStreamEvent({
      type: "team.member.spawned",
      agent_id: "agent-1",
      role: "researcher",
    });
    expect(event).toEqual({ kind: "team.member.spawned", agentId: "agent-1", role: "researcher" });
  });

  it("maps team.member.spawned without role", () => {
    const event = parseStreamEvent({ type: "team.member.spawned", agent_id: "agent-2" });
    expect(event).toEqual({ kind: "team.member.spawned", agentId: "agent-2", role: undefined });
  });

  it("maps team.member.status_changed", () => {
    const event = parseStreamEvent({
      type: "team.member.status_changed",
      agent_id: "agent-1",
      status: "working",
    });
    expect(event).toEqual({
      kind: "team.member.status_changed",
      agentId: "agent-1",
      status: "working",
    });
  });

  it("maps team.task.created", () => {
    const event = parseStreamEvent({
      type: "team.task.created",
      task_id: "task-1",
      assigned_to: "agent-1",
      description: "Search the web",
    });
    expect(event).toEqual({
      kind: "team.task.created",
      taskId: "task-1",
      assignedTo: "agent-1",
      description: "Search the web",
    });
  });

  it("maps team.task.completed", () => {
    const event = parseStreamEvent({
      type: "team.task.completed",
      task_id: "task-1",
      agent_id: "agent-1",
    });
    expect(event).toEqual({
      kind: "team.task.completed",
      taskId: "task-1",
      agentId: "agent-1",
    });
  });

  it("maps team.handoff with summary", () => {
    const event = parseStreamEvent({
      type: "team.handoff",
      from_agent_id: "agent-1",
      to_agent_id: "agent-2",
      summary: "Handing off research results",
    });
    expect(event).toEqual({
      kind: "team.handoff",
      fromAgentId: "agent-1",
      toAgentId: "agent-2",
      summary: "Handing off research results",
    });
  });

  it("maps team.handoff without summary", () => {
    const event = parseStreamEvent({
      type: "team.handoff",
      from_agent_id: "a",
      to_agent_id: "b",
    });
    expect(event).toEqual({
      kind: "team.handoff",
      fromAgentId: "a",
      toAgentId: "b",
      summary: undefined,
    });
  });
});

// ---------------------------------------------------------------------------
// AgentModeConstants + ChannelIdConstants
// ---------------------------------------------------------------------------

describe("AgentModeConstants", () => {
  it("has the expected string values", () => {
    expect(AgentModeConstants.AGENT).toBe("agent");
    expect(AgentModeConstants.CODE).toBe("code");
    expect(AgentModeConstants.TEAM).toBe("team");
    expect(AgentModeConstants.CODE_TEAM).toBe("code.team");
    expect(AgentModeConstants.DEFAULT).toBe("agent");
  });

  it("DEFAULT equals AGENT", () => {
    expect(AgentModeConstants.DEFAULT).toBe(AgentModeConstants.AGENT);
  });

  it("all values are strings", () => {
    for (const v of Object.values(AgentModeConstants)) {
      expect(typeof v).toBe("string");
    }
  });
});

describe("ChannelIdConstants", () => {
  it("has the expected string values", () => {
    expect(ChannelIdConstants.API).toBe("api");
    expect(ChannelIdConstants.JUPYTER).toBe("jupyter");
    expect(ChannelIdConstants.IDE).toBe("ide");
    expect(ChannelIdConstants.BROWSER).toBe("browser");
    expect(ChannelIdConstants.CLI).toBe("cli");
    expect(ChannelIdConstants.MOBILE).toBe("mobile");
  });

  it("all values are strings", () => {
    for (const v of Object.values(ChannelIdConstants)) {
      expect(typeof v).toBe("string");
    }
  });
});

// ---------------------------------------------------------------------------
// JiuwenSwarmClient._applyContextPrefix()
// ---------------------------------------------------------------------------

describe("JiuwenSwarmClient._applyContextPrefix()", () => {
  it("returns prompt unchanged when contextPrefix is undefined", () => {
    expect(JiuwenSwarmClient._applyContextPrefix("Hello")).toBe("Hello");
  });

  it("returns prompt unchanged when contextPrefix is empty string", () => {
    expect(JiuwenSwarmClient._applyContextPrefix("Hello", "")).toBe("Hello");
  });

  it("returns prompt unchanged when contextPrefix is whitespace only", () => {
    expect(JiuwenSwarmClient._applyContextPrefix("Hello", "   ")).toBe("Hello");
  });

  it("prepends context with separator", () => {
    const result = JiuwenSwarmClient._applyContextPrefix("Question?", "# Context\nsome info");
    expect(result).toBe("# Context\nsome info\n\n---\n\nQuestion?");
  });

  it("strips trailing whitespace from contextPrefix", () => {
    const result = JiuwenSwarmClient._applyContextPrefix("Q", "ctx  \n  ");
    expect(result).toBe("ctx\n\n---\n\nQ");
  });

  it("prompt is preserved exactly (including leading spaces)", () => {
    const prompt = "   indented\nquestion";
    const result = JiuwenSwarmClient._applyContextPrefix(prompt, "ctx");
    expect(result.endsWith(prompt)).toBe(true);
  });

  it("separator appears exactly once", () => {
    const result = JiuwenSwarmClient._applyContextPrefix("p", "ctx");
    expect(result.split("---").length - 1).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// client.streamEvents() — async generator
// ---------------------------------------------------------------------------

describe("client.streamEvents()", () => {
  it("yields DeltaEvents for incoming token envelopes", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const received: string[] = [];
    const gen = client.streamEvents("Tell me a story");

    const iterPromise = (async () => {
      for await (const event of gen) {
        if (event.kind === "delta") received.push(event.text);
      }
    })();

    // Flush microtasks so the generator sends the CHAT req.
    await Promise.resolve();

    currentMock.simulateMessage(eventFrame("chat.delta", { content: "Once" }));
    currentMock.simulateMessage(eventFrame("chat.delta", { content: " upon" }));
    currentMock.simulateMessage(eventFrame("chat.final"));

    await iterPromise;

    expect(received).toEqual(["Once", " upon"]);
  });

  it("terminates the generator when done arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const events: string[] = [];
    const gen = client.streamEvents("Hello");

    const iterPromise = (async () => {
      for await (const event of gen) {
        events.push(event.kind);
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(eventFrame("chat.delta", { content: "Hi" }));
    currentMock.simulateMessage(eventFrame("chat.final", { session_id: "s1" }));

    await iterPromise;

    expect(events).toContain("delta");
    expect(events).toContain("done");
  });

  it("yields a DoneEvent with sessionId", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    let doneEvent: { kind: string; sessionId?: string } | null = null;
    const gen = client.streamEvents("Q");

    const iterPromise = (async () => {
      for await (const event of gen) {
        if (event.kind === "done") doneEvent = event;
      }
    })();

    await Promise.resolve();
    currentMock.simulateMessage(eventFrame("chat.final", { session_id: "my-session" }));
    await iterPromise;

    expect(doneEvent).not.toBeNull();
    expect(doneEvent!.sessionId).toBe("my-session");
  });

  it("yields ErrorEvent then rejects when an error envelope arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("Q");

    const collectedKinds: string[] = [];
    const iterPromise = (async () => {
      for await (const event of gen) {
        collectedKinds.push(event.kind);
      }
    })();

    await Promise.resolve();

    // A chat.error event is pushed as an ErrorEvent to the generator buffer,
    // then finish(err) is called. The generator yields the ErrorEvent then
    // throws when it sees error is set after the buffer drains.
    currentMock.simulateMessage(eventFrame("chat.error", { error: "Server overload" }));

    await expect(iterPromise).rejects.toThrow("Server overload");
    // The ErrorEvent was yielded before the throw.
    expect(collectedKinds).toContain("error");
  });

  it("throws ConnectionError when not connected", async () => {
    const client = makeClient();
    // NOT calling connect()

    const gen = client.streamEvents("Q");
    await expect(gen.next()).rejects.toThrow("Not connected");
  });

  it("sends a chat.send req with the prompt", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("What is TypeScript?");
    // Start the generator
    const nextPromise = gen.next();
    await Promise.resolve();

    const chatEnvelope = currentMock.lastSent();
    expect(chatEnvelope.type).toBe("req");
    expect(chatEnvelope.method).toBe("chat.send");
    expect(chatEnvelope.params).toMatchObject({ content: "What is TypeScript?" });

    // Finish the generator to avoid hanging
    currentMock.simulateMessage(eventFrame("chat.final"));
    await nextPromise;
    await gen.return(undefined);
  });

  it("applies contextPrefix to the prompt in the chat.send params", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("Question?", { contextPrefix: "# File\nsome code" });
    const nextPromise = gen.next();
    await Promise.resolve();

    const chatEnvelope = currentMock.lastSent();
    const params = chatEnvelope.params as Record<string, unknown>;
    expect(typeof params.content).toBe("string");
    const msg = params.content as string;
    expect(msg).toContain("# File\nsome code");
    expect(msg).toContain("Question?");
    expect(msg).toContain("---");

    currentMock.simulateMessage(eventFrame("chat.final"));
    await nextPromise;
    await gen.return(undefined);
  });

  it("forwards mode to the chat.send params", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("Code this", { mode: "code" });
    const nextPromise = gen.next();
    await Promise.resolve();

    const chatEnvelope = currentMock.lastSent();
    expect(chatEnvelope.params).toMatchObject({ mode: "code" });

    currentMock.simulateMessage(eventFrame("chat.final"));
    await nextPromise;
    await gen.return(undefined);
  });

  it("forwards channelId to the chat.send params", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("Notebook task", { channelId: "jupyter" });
    const nextPromise = gen.next();
    await Promise.resolve();

    const chatEnvelope = currentMock.lastSent();
    expect(chatEnvelope.params).toMatchObject({ channel_id: "jupyter" });

    currentMock.simulateMessage(eventFrame("chat.final"));
    await nextPromise;
    await gen.return(undefined);
  });

  it("picks up mode and channelId from ClientConfig when not overridden", async () => {
    const client = makeClient({ mode: "team", channelId: "ide" });
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("Coordinate");
    const nextPromise = gen.next();
    await Promise.resolve();

    const chatEnvelope = currentMock.lastSent();
    expect(chatEnvelope.params).toMatchObject({ mode: "team", channel_id: "ide" });

    currentMock.simulateMessage(eventFrame("chat.final"));
    await nextPromise;
    await gen.return(undefined);
  });
});

// ---------------------------------------------------------------------------
// client.interrupt()
// ---------------------------------------------------------------------------

describe("client.interrupt()", () => {
  it("sends a chat.interrupt req", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    client.interrupt();
    const envelope = currentMock.lastSent();
    expect(envelope.method).toBe("chat.interrupt");
  });

  it("is fire-and-forget — does not return a promise", () => {
    const client = makeClient();
    // Not connected — interrupt() should not throw
    expect(() => client.interrupt()).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// streamEvents — reasoning + status + tool events
// ---------------------------------------------------------------------------

describe("client.streamEvents() — rich event types", () => {
  it("yields ReasoningEvents", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const received: Array<{ kind: string; text?: string }> = [];
    const gen = client.streamEvents("Think step by step");

    const iterPromise = (async () => {
      for await (const event of gen) {
        received.push({ kind: event.kind, text: "text" in event ? event.text : undefined });
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(eventFrame("chat.reasoning", { content: "First, I consider..." }));
    currentMock.simulateMessage(eventFrame("chat.final"));

    await iterPromise;

    const reasoning = received.find((e) => e.kind === "reasoning");
    expect(reasoning).toBeDefined();
    expect(reasoning!.text).toBe("First, I consider...");
  });

  it("yields StatusEvents", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const received: Array<{ kind: string }> = [];
    const gen = client.streamEvents("Search something");

    const iterPromise = (async () => {
      for await (const event of gen) {
        received.push({ kind: event.kind });
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(
      eventFrame("chat.processing_status", { is_processing: true, agent_id: "a1" }),
    );
    currentMock.simulateMessage(eventFrame("chat.final"));

    await iterPromise;

    expect(received.some((e) => e.kind === "status")).toBe(true);
  });

  it("yields UsageEvents", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    let usageEvent: Record<string, unknown> | null = null;
    const gen = client.streamEvents("Q");

    const iterPromise = (async () => {
      for await (const event of gen) {
        if (event.kind === "usage") usageEvent = event as unknown as Record<string, unknown>;
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(
      eventFrame("chat.usage_metadata", { input_tokens: 100, output_tokens: 200, cost_usd: 0.005 }),
    );
    currentMock.simulateMessage(eventFrame("chat.final"));

    await iterPromise;

    expect(usageEvent).not.toBeNull();
    expect(usageEvent!.inputTokens).toBe(100);
    expect(usageEvent!.outputTokens).toBe(200);
    expect(usageEvent!.costUsd).toBe(0.005);
  });
});

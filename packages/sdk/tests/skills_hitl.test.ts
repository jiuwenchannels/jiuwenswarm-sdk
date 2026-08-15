/**
 * Tests for Phase 12 — skills and HITL.
 *
 * Covers:
 * - client.listSkills() sends {type:"skills"} and resolves with SkillInfo[]
 * - client.toggleSkill(id, enabled) sends {type:"skill_toggle"} and resolves
 * - client.sendAnswer(requestId, answers) sends {type:"hitl_answer"}
 * - ConfirmInterruptEvent flows through streamEvents()
 * - listSkills/toggleSkill reject when not connected
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { JiuwenSwarmClient } from "../src/client/JiuwenSwarmClient";
import { MSG } from "../src/protocol/constants";
import type { SkillInfo } from "../src/protocol/types";

// ---------------------------------------------------------------------------
// MockWebSocket
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
  sentAt(i: number): Record<string, unknown> {
    return JSON.parse(this.send.mock.calls[i][0]) as Record<string, unknown>;
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
// listSkills()
// ---------------------------------------------------------------------------

describe("client.listSkills()", () => {
  it("sends {type:'skills'} envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    void client.listSkills(); // fire without await, just to inspect the sent envelope
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe(MSG.SKILLS);
  });

  it("resolves with the skills array from skills_list envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const listPromise = client.listSkills();

    const fakeSkills: SkillInfo[] = [
      { id: "web-search", name: "Web Search", description: "Search the web", enabled: true },
      { id: "code-exec", name: "Code Executor", description: "Run code", enabled: false },
    ];

    currentMock.simulateMessage(
      JSON.stringify({ type: "skills_list", skills: fakeSkills }),
    );

    const result = await listPromise;
    expect(result).toHaveLength(2);
    expect(result[0].id).toBe("web-search");
    expect(result[0].name).toBe("Web Search");
    expect(result[0].enabled).toBe(true);
    expect(result[1].id).toBe("code-exec");
    expect(result[1].enabled).toBe(false);
  });

  it("resolves with an empty array when no skills are installed", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const listPromise = client.listSkills();
    currentMock.simulateMessage(JSON.stringify({ type: "skills_list", skills: [] }));

    const result = await listPromise;
    expect(result).toEqual([]);
  });

  it("resolves with optional version field when present", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const listPromise = client.listSkills();
    const skills: SkillInfo[] = [
      {
        id: "web-search",
        name: "Web Search",
        description: "Search",
        enabled: true,
        version: "2.1.0",
      },
    ];
    currentMock.simulateMessage(JSON.stringify({ type: "skills_list", skills }));

    const result = await listPromise;
    expect(result[0].version).toBe("2.1.0");
  });

  it("rejects when not connected", async () => {
    const client = makeClient();
    await expect(client.listSkills()).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// toggleSkill()
// ---------------------------------------------------------------------------

describe("client.toggleSkill()", () => {
  it("sends {type:'skill_toggle', id, enabled:true} envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    void client.toggleSkill("web-search", true);
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe(MSG.SKILL_TOGGLE);
    expect(envelope.id).toBe("web-search");
    expect(envelope.enabled).toBe(true);
  });

  it("sends {type:'skill_toggle', id, enabled:false} envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    void client.toggleSkill("code-exec", false);
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe(MSG.SKILL_TOGGLE);
    expect(envelope.id).toBe("code-exec");
    expect(envelope.enabled).toBe(false);
  });

  it("resolves with {id, enabled} from the skill_toggled envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const togglePromise = client.toggleSkill("web-search", true);
    currentMock.simulateMessage(
      JSON.stringify({ type: "skill_toggled", id: "web-search", enabled: true }),
    );

    const result = await togglePromise;
    expect(result).toEqual({ id: "web-search", enabled: true });
  });

  it("resolves correctly when disabling a skill", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const togglePromise = client.toggleSkill("code-exec", false);
    currentMock.simulateMessage(
      JSON.stringify({ type: "skill_toggled", id: "code-exec", enabled: false }),
    );

    const result = await togglePromise;
    expect(result.id).toBe("code-exec");
    expect(result.enabled).toBe(false);
  });

  it("rejects when not connected", async () => {
    const client = makeClient();
    await expect(client.toggleSkill("web-search", true)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// sendAnswer() — HITL
// ---------------------------------------------------------------------------

describe("client.sendAnswer()", () => {
  it("sends {type:'hitl_answer', request_id, answers} envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    client.sendAnswer("req-42", { confirm: "yes", reason: "looks correct" });
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe(MSG.HITL_ANSWER);
    expect(envelope.request_id).toBe("req-42");
    expect(envelope.answers).toEqual({ confirm: "yes", reason: "looks correct" });
  });

  it("sends an empty answers map", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    client.sendAnswer("req-1", {});
    const envelope = currentMock.lastSent();
    expect(envelope.answers).toEqual({});
  });

  it("is fire-and-forget — does not throw when not connected", () => {
    const client = makeClient();
    expect(() => client.sendAnswer("req-1", { a: "b" })).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// ConfirmInterruptEvent through streamEvents()
// ---------------------------------------------------------------------------

describe("ConfirmInterruptEvent through client.streamEvents()", () => {
  it("yields a confirm_interrupt event", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    let hitlEvent: { kind: string; requestId?: string; question?: string } | null = null;
    const gen = client.streamEvents("Sensitive analysis");

    const iterPromise = (async () => {
      for await (const event of gen) {
        if (event.kind === "confirm_interrupt") {
          hitlEvent = event;
          // Simulate the user answering and the stream continuing.
          client.sendAnswer(event.requestId, { confirm: "proceed" });
        }
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(
      JSON.stringify({
        type: "confirm_interrupt",
        request_id: "req-99",
        question: "This may be sensitive. Continue?",
      }),
    );
    // After the user answers, the server sends more content and finishes.
    currentMock.simulateMessage(JSON.stringify({ type: "token", text: "Analysis..." }));
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));

    await iterPromise;

    expect(hitlEvent).not.toBeNull();
    expect(hitlEvent!.requestId).toBe("req-99");
    expect(hitlEvent!.question).toBe("This may be sensitive. Continue?");
  });

  it("sendAnswer() is called with the correct requestId after confirm_interrupt", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const gen = client.streamEvents("Q");

    const iterPromise = (async () => {
      for await (const event of gen) {
        if (event.kind === "confirm_interrupt") {
          client.sendAnswer(event.requestId, { choice: "yes" });
        }
      }
    })();

    await Promise.resolve();

    currentMock.simulateMessage(
      JSON.stringify({ type: "confirm_interrupt", request_id: "rq-1", question: "Proceed?" }),
    );
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));

    await iterPromise;

    // Find the hitl_answer envelope in sent messages
    const sentMessages = currentMock.send.mock.calls
      .map((call) => JSON.parse(call[0]) as Record<string, unknown>)
      .filter((m) => m.type === "hitl_answer");

    expect(sentMessages.length).toBeGreaterThanOrEqual(1);
    expect(sentMessages[0].request_id).toBe("rq-1");
    expect(sentMessages[0].answers).toEqual({ choice: "yes" });
  });
});

// ---------------------------------------------------------------------------
// Skills list + toggle — lifecycle with connection close
// ---------------------------------------------------------------------------

describe("skills — rejected when connection closes", () => {
  it("listSkills() rejects when the WebSocket closes before skills_list arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const listPromise = client.listSkills();
    currentMock.simulateClose(1001, "going away");
    await expect(listPromise).rejects.toThrow();
  });

  it("toggleSkill() rejects when the WebSocket closes before skill_toggled arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const togglePromise = client.toggleSkill("web-search", true);
    currentMock.simulateClose(1001, "going away");
    await expect(togglePromise).rejects.toThrow();
  });
});

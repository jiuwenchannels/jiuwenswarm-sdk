import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { JiuwenSwarmClient } from "../src/client/JiuwenSwarmClient";

// ---------------------------------------------------------------------------
// MockWebSocket
// ---------------------------------------------------------------------------

class MockWebSocket {
  readyState: number = 0; // CONNECTING

  send = vi.fn<[string], void>();
  close = vi.fn<[number?, string?], void>();

  onopen: ((event: object) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: { code: number; reason: string }) => void) | null = null;

  simulateOpen(): void {
    this.readyState = 1; // OPEN
    this.onopen?.({});
  }

  simulateMessage(data: string): void {
    this.onmessage?.({ data });
  }

  simulateClose(code = 1000, reason = ""): void {
    this.readyState = 3; // CLOSED
    this.onclose?.({ code, reason });
  }

  simulateError(): void {
    this.onerror?.(new Event("error"));
  }

  /** Returns the last object sent via send(), parsed from JSON. */
  lastSent(): Record<string, unknown> {
    const calls = this.send.mock.calls;
    if (calls.length === 0) throw new Error("send() has not been called yet");
    return JSON.parse(calls.at(-1)![0]) as Record<string, unknown>;
  }

  /** Returns the nth sent object (0-based), parsed from JSON. */
  sentAt(index: number): Record<string, unknown> {
    const calls = this.send.mock.calls;
    return JSON.parse(calls[index][0]) as Record<string, unknown>;
  }
}

// ---------------------------------------------------------------------------
// Constructor stub
// ---------------------------------------------------------------------------

let currentMock: MockWebSocket;

/**
 * A constructor function that always returns the same MockWebSocket instance
 * so tests can inspect it after the client creates it.
 */
function MockWSConstructor(_url: string): MockWebSocket {
  currentMock = new MockWebSocket();
  return currentMock;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeClient(overrides: Partial<Parameters<typeof JiuwenSwarmClient>[0]> = {}) {
  return new JiuwenSwarmClient({
    url: "ws://localhost:19000/v1/ws",
    reconnect: false, // disable by default to keep tests simple
    ...overrides,
  });
}

/**
 * Complete the WebSocket handshake:
 *   1. Simulate the socket opening.
 *   2. Return an ack envelope with protocol_version so connect() resolves.
 */
function completeHandshake(mock: MockWebSocket): void {
  mock.simulateOpen();
  mock.simulateMessage(
    JSON.stringify({ type: "ack", protocol_version: "1.0" }),
  );
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.stubGlobal(
    "WebSocket",
    MockWSConstructor as unknown as typeof WebSocket,
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// connect()
// ---------------------------------------------------------------------------

describe("connect()", () => {
  it("resolves when an ack envelope with protocol_version is received", async () => {
    const client = makeClient();
    const promise = client.connect();
    completeHandshake(currentMock);
    await expect(promise).resolves.toBeUndefined();
  });

  it("sends a connect envelope immediately on WebSocket open", async () => {
    const client = makeClient();
    const promise = client.connect();
    currentMock.simulateOpen();
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe("connect");
    // Finish handshake so the promise settles
    currentMock.simulateMessage(
      JSON.stringify({ type: "ack", protocol_version: "1.0" }),
    );
    await promise;
  });

  it("the connect envelope includes client_type", async () => {
    const client = makeClient();
    const promise = client.connect();
    currentMock.simulateOpen();
    const envelope = currentMock.lastSent();
    expect(envelope.client_type).toBe("typescript-sdk");
    currentMock.simulateMessage(
      JSON.stringify({ type: "ack", protocol_version: "1.0" }),
    );
    await promise;
  });

  it("the connect envelope includes authToken when provided", async () => {
    const client = makeClient({ authToken: "my-secret-token" });
    const promise = client.connect();
    currentMock.simulateOpen();
    const envelope = currentMock.lastSent();
    expect(envelope.token).toBe("my-secret-token");
    currentMock.simulateMessage(
      JSON.stringify({ type: "ack", protocol_version: "1.0" }),
    );
    await promise;
  });

  it("emits connected event on successful connect", async () => {
    const client = makeClient();
    const connectedHandler = vi.fn();
    client.on("connected", connectedHandler);
    const promise = client.connect();
    completeHandshake(currentMock);
    await promise;
    expect(connectedHandler).toHaveBeenCalledOnce();
  });

  it("rejects if the WebSocket fires an error before ack", async () => {
    const client = makeClient();
    const promise = client.connect();
    currentMock.simulateOpen();
    currentMock.simulateError();
    await expect(promise).rejects.toThrow();
  });

  it("resolves immediately if already connected", async () => {
    const client = makeClient();
    const p1 = client.connect();
    completeHandshake(currentMock);
    await p1;
    // Second call should resolve without opening a new socket.
    await expect(client.connect()).resolves.toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// send()
// ---------------------------------------------------------------------------

describe("send()", () => {
  it("sends a {type:'chat', message} envelope", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("Hello, agent!");
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe("chat");
    expect(envelope.message).toBe("Hello, agent!");

    // Settle the send promise.
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));
    await sendPromise;
  });

  it("resolves when a done envelope arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("test");
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));
    await expect(sendPromise).resolves.toBeUndefined();
  });

  it("onToken callback is called for each token envelope", async () => {
    const onToken = vi.fn();
    const client = makeClient({ onToken });
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("stream me");
    currentMock.simulateMessage(JSON.stringify({ type: "token", text: "Hello" }));
    currentMock.simulateMessage(JSON.stringify({ type: "token", text: " world" }));
    currentMock.simulateMessage(JSON.stringify({ type: "done" }));
    await sendPromise;

    expect(onToken).toHaveBeenCalledTimes(2);
    expect(onToken).toHaveBeenNthCalledWith(1, "Hello");
    expect(onToken).toHaveBeenNthCalledWith(2, " world");
  });

  it("onDone callback is called with session_id from the done envelope", async () => {
    const onDone = vi.fn();
    const client = makeClient({ onDone });
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("hello");
    currentMock.simulateMessage(
      JSON.stringify({ type: "done", session_id: "sess-abc" }),
    );
    await sendPromise;

    expect(onDone).toHaveBeenCalledOnce();
    expect(onDone).toHaveBeenCalledWith("sess-abc");
  });

  it("rejects when an error envelope arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("bad message");
    currentMock.simulateMessage(
      JSON.stringify({ type: "error", message: "Something went wrong" }),
    );
    await expect(sendPromise).rejects.toThrow("Something went wrong");
  });

  it("rejects if not connected when send() is called", async () => {
    const client = makeClient();
    await expect(client.send("no connection yet")).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// sessions
// ---------------------------------------------------------------------------

describe("sessions", () => {
  it("sessions.list() sends {type:'sessions'} and resolves with the sessions array", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const listPromise = client.sessions.list();
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe("sessions");

    const fakeSessions = [
      { id: "s1", title: "First", agent_id: "a1", mode: "default", created_at: "" },
    ];
    currentMock.simulateMessage(
      JSON.stringify({ type: "sessions", sessions: fakeSessions }),
    );

    const result = await listPromise;
    expect(result).toEqual(fakeSessions);
  });

  it("sessions.create(title) sends {type:'create_session', title} and resolves with the new session", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const createPromise = client.sessions.create("My Chat");
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe("create_session");
    expect(envelope.title).toBe("My Chat");

    const newSession = {
      id: "new-s",
      title: "My Chat",
      agent_id: "agent-1",
      mode: "default",
      created_at: "",
    };
    currentMock.simulateMessage(
      JSON.stringify({ type: "session_created", session: newSession }),
    );

    const result = await createPromise;
    expect(result).toEqual(newSession);
  });

  it("sessions.setActive(id) makes the chat envelope include session_id", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    // Populate cache so setActive works end-to-end
    const listPromise = client.sessions.list();
    const fakeSession = {
      id: "active-session",
      title: "Active",
      agent_id: "a",
      mode: "default",
      created_at: "",
    };
    currentMock.simulateMessage(
      JSON.stringify({ type: "sessions", sessions: [fakeSession] }),
    );
    await listPromise;

    client.sessions.setActive("active-session");

    const sendPromise = client.send("hello");
    const chatEnvelope = currentMock.lastSent();
    expect(chatEnvelope.session_id).toBe("active-session");

    currentMock.simulateMessage(JSON.stringify({ type: "done" }));
    await sendPromise;
  });
});

// ---------------------------------------------------------------------------
// tool_call handling
// ---------------------------------------------------------------------------

describe("tool_call handling", () => {
  it("when onToolCall is not provided, sends tool_result with error", async () => {
    const client = makeClient(); // no onToolCall
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    currentMock.simulateMessage(
      JSON.stringify({
        type: "tool_call",
        name: "search",
        arguments: { query: "cats" },
        callId: "call-1",
      }),
    );

    // Give the microtask queue a chance to process the async handler.
    await Promise.resolve();

    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe("tool_result");
    expect(envelope.callId).toBe("call-1");
    expect(typeof envelope.error).toBe("string");
    expect(envelope.result).toBeUndefined();
  });

  it("when onToolCall is provided, its return value is sent as tool_result.result", async () => {
    const onToolCall = vi.fn().mockResolvedValue("search results here");
    const client = makeClient({ onToolCall });
    const connectPromise = client.connect();
    // Capture the mock AFTER connect() opens the socket.
    const mock = currentMock;
    completeHandshake(mock);
    await connectPromise;

    mock.simulateMessage(
      JSON.stringify({
        type: "tool_call",
        name: "search",
        arguments: { query: "dogs" },
        callId: "call-2",
      }),
    );

    // Flush microtask queue: _onToolCall is async and awaits onToolCall().
    // One tick to enter _onToolCall, one to resolve the mock promise, one to
    // resume after the await and call _sendRaw.
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    const envelope = mock.lastSent();
    expect(envelope.type).toBe("tool_result");
    expect(envelope.callId).toBe("call-2");
    expect(envelope.result).toBe("search results here");
    expect(envelope.error).toBeUndefined();
  });

  it("when onToolCall throws, the error message is sent as tool_result.error", async () => {
    const onToolCall = vi.fn().mockRejectedValue(new Error("tool failed"));
    const client = makeClient({ onToolCall });
    const connectPromise = client.connect();
    // Capture the mock AFTER connect() opens the socket.
    const mock = currentMock;
    completeHandshake(mock);
    await connectPromise;

    mock.simulateMessage(
      JSON.stringify({
        type: "tool_call",
        name: "risky_tool",
        arguments: {},
        callId: "call-3",
      }),
    );

    // Same flush: rejection path also needs ~3 microtask ticks.
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    const envelope = mock.lastSent();
    expect(envelope.type).toBe("tool_result");
    expect(envelope.callId).toBe("call-3");
    expect(envelope.error).toBe("tool failed");
    expect(envelope.result).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// disconnect()
// ---------------------------------------------------------------------------

describe("disconnect()", () => {
  it("closes the WebSocket", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    client.disconnect();
    expect(currentMock.close).toHaveBeenCalled();
  });

  it("emits disconnected event after disconnect()", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const disconnectedHandler = vi.fn();
    client.on("disconnected", disconnectedHandler);
    client.disconnect();
    expect(disconnectedHandler).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// reconnect
// ---------------------------------------------------------------------------

describe("reconnect", () => {
  it("emits reconnecting event when the WebSocket closes unexpectedly and reconnect is enabled", async () => {
    vi.useFakeTimers();

    const client = makeClient({ reconnect: {} }); // default reconnect config
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const reconnectingHandler = vi.fn();
    client.on("reconnecting", reconnectingHandler);

    // Simulate unexpected close (not a clean code 1000 initiated by us)
    currentMock.simulateClose(1006, "Connection lost");

    // The reconnecting event should have fired synchronously or in the same tick.
    expect(reconnectingHandler).toHaveBeenCalled();
    const [attempt, delayMs] = reconnectingHandler.mock.calls[0] as [number, number];
    expect(attempt).toBeGreaterThan(0);
    expect(delayMs).toBeGreaterThan(0);
  });

  it("does not emit reconnecting when reconnect is false", async () => {
    const client = makeClient({ reconnect: false });
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const reconnectingHandler = vi.fn();
    client.on("reconnecting", reconnectingHandler);

    currentMock.simulateClose(1006, "Connection lost");

    expect(reconnectingHandler).not.toHaveBeenCalled();
  });
});

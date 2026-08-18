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
    url: "ws://localhost:19000/ws",
    reconnect: false, // disable by default to keep tests simple
    ...overrides,
  });
}

/**
 * Complete the WebSocket handshake:
 *   1. Simulate the socket opening.
 *   2. Return the gateway's `connection.ack` event so connect() resolves.
 */
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

/**
 * Simulate a gateway `res` frame in response to the last sent `req` frame.
 */
function respondRes(
  mock: MockWebSocket,
  payload: Record<string, unknown> = {},
  ok = true,
): void {
  const id = mock.lastSent().id as string;
  mock.simulateMessage(
    JSON.stringify(
      ok ? { type: "res", id, ok: true, payload } : { type: "res", id, ok: false, error: "fail" },
    ),
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
  it("resolves when the gateway connection.ack event is received", async () => {
    const client = makeClient();
    const promise = client.connect();
    completeHandshake(currentMock);
    await expect(promise).resolves.toBeUndefined();
  });

  it("does not send a request before connection.ack (gateway acks automatically)", async () => {
    const client = makeClient();
    const promise = client.connect();
    currentMock.simulateOpen();
    // The gateway sends connection.ack on its own; the client must not send
    // anything before that.
    expect(currentMock.send.mock.calls.length).toBe(0);
    currentMock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "connection.ack",
        payload: { protocol_version: "1.0" },
      }),
    );
    await promise;
  });

  it("records the server session_id from connection.ack", async () => {
    const client = makeClient();
    const promise = client.connect();
    currentMock.simulateOpen();
    currentMock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "connection.ack",
        payload: { protocol_version: "1.0", session_id: "srv-sess-1" },
      }),
    );
    await promise;
    expect(client.sessionId).toBe("srv-sess-1");
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
  it("sends a chat.send req with content and query params", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("Hello, agent!");
    const envelope = currentMock.lastSent();
    expect(envelope.type).toBe("req");
    expect(envelope.method).toBe("chat.send");
    expect(envelope.params).toMatchObject({
      content: "Hello, agent!",
      query: "Hello, agent!",
      mode: "agent",
    });

    // Settle the send promise.
    currentMock.simulateMessage(
      JSON.stringify({ type: "event", event: "chat.final", payload: {} }),
    );
    await sendPromise;
  });

  it("resolves when a chat.final event arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("test");
    currentMock.simulateMessage(
      JSON.stringify({ type: "event", event: "chat.final", payload: {} }),
    );
    await expect(sendPromise).resolves.toBeUndefined();
  });

  it("onToken callback is called for each chat.delta event", async () => {
    const onToken = vi.fn();
    const client = makeClient({ onToken });
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("stream me");
    currentMock.simulateMessage(
      JSON.stringify({ type: "event", event: "chat.delta", payload: { content: "Hello" } }),
    );
    currentMock.simulateMessage(
      JSON.stringify({ type: "event", event: "chat.delta", payload: { content: " world" } }),
    );
    currentMock.simulateMessage(
      JSON.stringify({ type: "event", event: "chat.final", payload: {} }),
    );
    await sendPromise;

    expect(onToken).toHaveBeenCalledTimes(2);
    expect(onToken).toHaveBeenNthCalledWith(1, "Hello");
    expect(onToken).toHaveBeenNthCalledWith(2, " world");
  });

  it("onDone callback is called with session_id from the chat.final event", async () => {
    const onDone = vi.fn();
    const client = makeClient({ onDone });
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("hello");
    currentMock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "chat.final",
        payload: { session_id: "sess-abc" },
      }),
    );
    await sendPromise;

    expect(onDone).toHaveBeenCalledOnce();
    expect(onDone).toHaveBeenCalledWith("sess-abc");
  });

  it("rejects when a chat.error event arrives", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const sendPromise = client.send("bad message");
    currentMock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "chat.error",
        payload: { error: "Something went wrong" },
      }),
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
  it("sessions.list() sends session.list and resolves with mapped sessions", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const listPromise = client.sessions.list();
    const envelope = currentMock.lastSent();
    expect(envelope.method).toBe("session.list");

    respondRes(currentMock, {
      sessions: [{ session_id: "s1", title: "First", mode: "agent" }],
    });

    const result = await listPromise;
    expect(result).toEqual([
      { id: "s1", title: "First", agent_id: "", mode: "agent", created_at: "" },
    ]);
  });

  it("sessions.create(title) sends session.create with create_token and resolves with the new session", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    const createPromise = client.sessions.create("My Chat");
    const envelope = currentMock.lastSent();
    expect(envelope.method).toBe("session.create");
    expect(envelope.params).toMatchObject({ title: "My Chat", mode: "agent" });
    expect(typeof envelope.params.create_token).toBe("string");

    respondRes(currentMock, { session_id: "new-s", title: "My Chat" });

    const result = await createPromise;
    expect(result.id).toBe("new-s");
    expect(result.title).toBe("My Chat");
  });

  it("sessions.setActive(id) makes the chat.send params include session_id", async () => {
    const client = makeClient();
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    // Populate cache so setActive works end-to-end
    const listPromise = client.sessions.list();
    respondRes(currentMock, {
      sessions: [{ session_id: "active-session", title: "Active", mode: "agent" }],
    });
    await listPromise;

    client.sessions.setActive("active-session");

    const sendPromise = client.send("hello");
    const chatEnvelope = currentMock.lastSent();
    expect(chatEnvelope.params).toMatchObject({ session_id: "active-session" });

    currentMock.simulateMessage(
      JSON.stringify({ type: "event", event: "chat.final", payload: {} }),
    );
    await sendPromise;
  });
});

// ---------------------------------------------------------------------------
// tool_call handling
// ---------------------------------------------------------------------------

describe("tool_call handling", () => {
  it("when onToolCall is not provided, sends tool.result with error", async () => {
    const client = makeClient(); // no onToolCall
    const connectPromise = client.connect();
    completeHandshake(currentMock);
    await connectPromise;

    currentMock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "chat.tool_call",
        payload: { tool_name: "search", arguments: { query: "cats" }, call_id: "call-1" },
      }),
    );

    // Give the microtask queue a chance to process the async handler.
    await Promise.resolve();

    const envelope = currentMock.lastSent();
    expect(envelope.method).toBe("tool.result");
    expect(envelope.params).toMatchObject({ call_id: "call-1" });
    expect(typeof envelope.params.error).toBe("string");
    expect(envelope.params.result).toBeUndefined();
  });

  it("when onToolCall is provided, its return value is sent as tool.result.result", async () => {
    const onToolCall = vi.fn().mockResolvedValue("search results here");
    const client = makeClient({ onToolCall });
    const connectPromise = client.connect();
    // Capture the mock AFTER connect() opens the socket.
    const mock = currentMock;
    completeHandshake(mock);
    await connectPromise;

    mock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "chat.tool_call",
        payload: { tool_name: "search", arguments: { query: "dogs" }, call_id: "call-2" },
      }),
    );

    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    const envelope = mock.lastSent();
    expect(envelope.method).toBe("tool.result");
    expect(envelope.params).toMatchObject({ call_id: "call-2", result: "search results here" });
    expect(envelope.params.error).toBeUndefined();
  });

  it("when onToolCall throws, the error message is sent as tool.result.error", async () => {
    const onToolCall = vi.fn().mockRejectedValue(new Error("tool failed"));
    const client = makeClient({ onToolCall });
    const connectPromise = client.connect();
    // Capture the mock AFTER connect() opens the socket.
    const mock = currentMock;
    completeHandshake(mock);
    await connectPromise;

    mock.simulateMessage(
      JSON.stringify({
        type: "event",
        event: "chat.tool_call",
        payload: { tool_name: "risky_tool", arguments: {}, call_id: "call-3" },
      }),
    );

    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    const envelope = mock.lastSent();
    expect(envelope.method).toBe("tool.result");
    expect(envelope.params).toMatchObject({ call_id: "call-3", error: "tool failed" });
    expect(envelope.params.result).toBeUndefined();
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

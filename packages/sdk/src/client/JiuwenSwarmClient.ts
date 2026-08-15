/**
 * JiuwenSwarmClient — WebSocket client for the JiuwenSwarm gateway.
 *
 * ```typescript
 * const client = new JiuwenSwarmClient({
 *   url: "ws://localhost:19000/v1/ws",
 *   onToken: (text) => process.stdout.write(text),
 *   onDone:  (sessionId) => console.log("\n[done]", sessionId),
 * });
 *
 * await client.connect();
 * const session = await client.sessions.create("My session");
 * client.sessions.setActive(session.id);
 * await client.send("Explain the event loop.");
 * client.disconnect();
 * ```
 */
import { EventEmitter } from "../events/EventEmitter";
import { MSG } from "../protocol/constants";
import { parseStreamEvent, type StreamEvent } from "../protocol/events";
import type {
  AckEnvelope,
  ClientConfig,
  DoneEnvelope,
  ErrorEnvelope,
  InboundEnvelope,
  OutboundEnvelope,
  SessionInfo,
  SessionsEnvelope,
  SessionCreatedEnvelope,
  SkillInfo,
  SkillsListEnvelope,
  SkillToggledEnvelope,
  StreamEventsOptions,
  TokenEnvelope,
  ToolCallEnvelope,
  AgentMode,
} from "../protocol/types";
import { parseEnvelope, ConnectionError } from "../protocol/validate";
import { ReconnectScheduler } from "./reconnect";
import { SessionManager, type SessionDelegate } from "../session/SessionManager";

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

type ClientEvents = {
  /** Fired when the WebSocket connection is established and the ack received. */
  connected: [];
  /** Fired when the connection drops for any reason. */
  disconnected: [reason: string];
  /** Fired before each reconnect attempt. */
  reconnecting: [attempt: number, delayMs: number];
};

type Resolver<T> = { resolve: (v: T) => void; reject: (e: unknown) => void };

/** Internal handle for an active `streamEvents()` generator. */
type StreamEventsHandle = {
  push: (event: StreamEvent) => void;
  finish: (err?: Error) => void;
};

// ---------------------------------------------------------------------------
// WebSocket adapter
// ---------------------------------------------------------------------------

/** Retrieve a WebSocket constructor that works in the current environment. */
function getWebSocket(): typeof WebSocket {
  if (typeof globalThis !== "undefined" && typeof (globalThis as { WebSocket?: unknown }).WebSocket === "function") {
    return (globalThis as { WebSocket: typeof WebSocket }).WebSocket;
  }
  // Node.js: attempt to load the optional "ws" peer dependency.
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const ws = require("ws") as { default?: typeof WebSocket } | typeof WebSocket;
    // Handle both `module.exports = WebSocket` and ESM-interop default
    return ("default" in ws ? ws.default : ws) as typeof WebSocket;
  } catch {
    throw new ConnectionError(
      "No WebSocket implementation found. " +
      "In Node.js, install the optional peer dependency: npm install ws",
    );
  }
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export class JiuwenSwarmClient
  extends EventEmitter<ClientEvents>
  implements SessionDelegate
{
  private readonly _config: ClientConfig;
  private _ws: WebSocket | null = null;
  private _scheduler: ReconnectScheduler | null = null;

  /** Pending promise for connect() */
  private _pendingConnect: Resolver<void> | null = null;
  /** Pending promise for _listSessions() */
  private _pendingSessions: Resolver<SessionInfo[]> | null = null;
  /** Pending promise for _createSession() */
  private _pendingCreate: Resolver<SessionInfo> | null = null;
  /** Pending promise for send() */
  private _pendingChat: Resolver<void> | null = null;
  /** Pending promise for listSkills() */
  private _pendingSkills: Resolver<SkillInfo[]> | null = null;
  /** Pending promise for toggleSkill() */
  private _pendingSkillToggle: Resolver<{ id: string; enabled: boolean }> | null = null;
  /** Active streamEvents() generator handle, if any. */
  private _pendingStreamEvents: StreamEventsHandle | null = null;

  /** Set to true once the connect ack is received. */
  private _connected = false;

  /** Exposed session manager. */
  readonly sessions: SessionManager;

  constructor(config: ClientConfig) {
    super();
    this._config = config;
    this.sessions = new SessionManager(this);

    if (config.reconnect !== false) {
      this._scheduler = new ReconnectScheduler(
        typeof config.reconnect === "object" ? config.reconnect : {},
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Public API — connection
  // ---------------------------------------------------------------------------

  /**
   * Open the WebSocket connection and complete the `connect` handshake.
   *
   * Resolves when the server sends an `ack` envelope.
   * Rejects on connection errors or timeout.
   */
  connect(): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      if (this._connected) {
        resolve();
        return;
      }
      this._pendingConnect = { resolve, reject };
      this._openSocket();
    });
  }

  /**
   * Close the WebSocket connection and cancel any pending reconnect.
   * All pending promises are rejected.
   */
  disconnect(): void {
    this._scheduler?.cancel();
    this._scheduler?.reset();
    this._closeSocket("client disconnect", false /* no reconnect */);
  }

  // ---------------------------------------------------------------------------
  // Public API — messaging
  // ---------------------------------------------------------------------------

  /**
   * Send a chat message and stream the response.
   *
   * Resolves when the server sends the `done` envelope.
   * Individual tokens are delivered via the `onToken` callback.
   *
   * @param message  The user message to send.
   */
  send(message: string): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected. Call connect() first."));
        return;
      }
      this._pendingChat = { resolve, reject };
      this._sendRaw({
        type: MSG.CHAT,
        message,
        session_id: this.sessions.activeId ?? undefined,
        mode: this._config.mode,
        channel_id: this._config.channelId,
      });
    });
  }

  /**
   * Send a chat message and iterate over typed `StreamEvent` objects as they
   * arrive from the server.
   *
   * This is the richer alternative to `send()`.  Instead of delivering tokens
   * through an `onToken` callback, every protocol event — token deltas,
   * reasoning steps, tool calls, team events, usage, and done — is exposed as
   * a strongly-typed `StreamEvent` via an async generator.
   *
   * ```typescript
   * for await (const event of client.streamEvents("Summarise this article")) {
   *   switch (event.kind) {
   *     case "delta":     process.stdout.write(event.text); break;
   *     case "tool_call": console.log("[tool]", event.name); break;
   *     case "done":      console.log("\n[done]"); break;
   *   }
   * }
   * ```
   *
   * @param prompt   The user message to send.
   * @param options  Optional mode, channelId, contextPrefix, sessionId.
   */
  async *streamEvents(
    prompt: string,
    options?: StreamEventsOptions,
  ): AsyncIterable<StreamEvent> {
    if (!this._connected || !this._ws) {
      throw new ConnectionError("Not connected. Call connect() first.");
    }

    const buffer: StreamEvent[] = [];
    let done = false;
    let error: Error | null = null;
    let notify: (() => void) | null = null;

    const push = (event: StreamEvent): void => {
      buffer.push(event);
      const fn = notify;
      notify = null;
      fn?.();
    };

    const finish = (err?: Error): void => {
      done = true;
      error = err ?? null;
      const fn = notify;
      notify = null;
      fn?.();
    };

    this._pendingStreamEvents = { push, finish };

    const message = JiuwenSwarmClient._applyContextPrefix(
      prompt,
      options?.contextPrefix,
    );

    this._sendRaw({
      type: MSG.CHAT,
      message,
      session_id: options?.sessionId ?? this.sessions.activeId ?? undefined,
      mode: options?.mode ?? this._config.mode,
      channel_id: options?.channelId ?? this._config.channelId,
    });

    try {
      while (true) {
        // Drain buffered events.
        while (buffer.length > 0) {
          yield buffer.shift()!;
        }
        if (done) {
          if (error) throw error;
          break;
        }
        // Wait for the next push() or finish() call.
        await new Promise<void>((resolve) => {
          notify = resolve;
        });
      }
      // Drain any events that arrived between the final push and the yield.
      while (buffer.length > 0) {
        yield buffer.shift()!;
      }
    } finally {
      // Clean up only if this generator is still the active one.
      if (this._pendingStreamEvents?.finish === finish) {
        this._pendingStreamEvents = null;
      }
    }
  }

  /**
   * Fire-and-forget interrupt: ask the server to cancel or pause the current
   * agent turn.  No response is expected — the next stream event will be an
   * `ErrorEvent` or `DoneEvent` confirming the cancellation.
   */
  interrupt(): void {
    this._sendRaw({ type: MSG.INTERRUPT });
  }

  /**
   * Low-level envelope send.
   * Serialises `envelope` to JSON and writes it to the WebSocket.
   */
  sendEnvelope(envelope: OutboundEnvelope): void {
    this._sendRaw(envelope);
  }

  // ---------------------------------------------------------------------------
  // Public API — skills (Phase 12)
  // ---------------------------------------------------------------------------

  /**
   * Fetch the list of installed skills/plugins from the server.
   *
   * ```typescript
   * const skills = await client.listSkills();
   * skills.forEach(s => console.log(s.name, s.enabled));
   * ```
   */
  listSkills(): Promise<SkillInfo[]> {
    return new Promise<SkillInfo[]>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingSkills = { resolve, reject };
      this._sendRaw({ type: MSG.SKILLS });
    });
  }

  /**
   * Enable or disable a skill by its ID.
   *
   * ```typescript
   * await client.toggleSkill("web-search", true);
   * ```
   *
   * @param id       Skill identifier (from `SkillInfo.id`).
   * @param enabled  `true` to enable, `false` to disable.
   */
  toggleSkill(id: string, enabled: boolean): Promise<{ id: string; enabled: boolean }> {
    return new Promise((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingSkillToggle = { resolve, reject };
      this._sendRaw({ type: MSG.SKILL_TOGGLE, id, enabled });
    });
  }

  // ---------------------------------------------------------------------------
  // Public API — HITL (Phase 12)
  // ---------------------------------------------------------------------------

  /**
   * Reply to a `confirm_interrupt` event.
   *
   * When a `streamEvents()` loop yields a `ConfirmInterruptEvent`, call this
   * method with the `requestId` from that event and a map of answers.  The
   * server resumes the agent with the provided answers as additional context.
   *
   * ```typescript
   * for await (const event of client.streamEvents("Analyse this")) {
   *   if (event.kind === "confirm_interrupt") {
   *     await client.sendAnswer(event.requestId, { confirm: "yes" });
   *   }
   * }
   * ```
   *
   * @param requestId  The `requestId` from the `ConfirmInterruptEvent`.
   * @param answers    Key/value map of answers to send to the agent.
   */
  sendAnswer(requestId: string, answers: Record<string, string>): void {
    this._sendRaw({ type: MSG.HITL_ANSWER, request_id: requestId, answers });
  }

  // ---------------------------------------------------------------------------
  // SessionDelegate implementation (called by SessionManager)
  // ---------------------------------------------------------------------------

  _listSessions(): Promise<SessionInfo[]> {
    return new Promise<SessionInfo[]>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingSessions = { resolve, reject };
      this._sendRaw({ type: MSG.SESSIONS });
    });
  }

  _createSession(params: {
    title?: string;
    agent_id?: string;
    mode?: AgentMode;
  }): Promise<SessionInfo> {
    return new Promise<SessionInfo>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingCreate = { resolve, reject };
      this._sendRaw({
        type: MSG.CREATE_SESSION,
        title: params.title,
        agent_id: params.agent_id,
        mode: params.mode,
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Static helpers
  // ---------------------------------------------------------------------------

  /**
   * Prepend `contextPrefix` to `prompt` with a `\n\n---\n\n` separator.
   * Returns `prompt` unchanged when `contextPrefix` is absent or empty.
   *
   * Mirrors Python SDK's `Agent._apply_context()`.
   */
  static _applyContextPrefix(prompt: string, contextPrefix?: string): string {
    if (!contextPrefix || contextPrefix.trim() === "") {
      return prompt;
    }
    return `${contextPrefix.trimEnd()}\n\n---\n\n${prompt}`;
  }

  // ---------------------------------------------------------------------------
  // Internal — socket lifecycle
  // ---------------------------------------------------------------------------

  private _openSocket(): void {
    const WS = getWebSocket();
    const ws = new WS(this._config.url);
    this._ws = ws;

    ws.onopen = () => {
      // Send the connect envelope immediately on open.
      this._sendRaw({
        type: MSG.CONNECT,
        client_type: "typescript-sdk",
        token: this._config.authToken,
      });
    };

    ws.onmessage = (event: MessageEvent) => {
      this._handleMessage(
        typeof event.data === "string" ? event.data : String(event.data),
      );
    };

    ws.onerror = () => {
      const err = new ConnectionError(`WebSocket error on ${this._config.url}`);
      this._rejectAllPending(err);
    };

    ws.onclose = (event: CloseEvent) => {
      const reason = event.reason || `code ${event.code}`;
      this._connected = false;
      this._ws = null;
      this._rejectAllPending(new ConnectionError(`WebSocket closed: ${reason}`));
      this.emit("disconnected", reason);
      this._maybeReconnect();
    };
  }

  private _closeSocket(reason: string, shouldReconnect: boolean): void {
    this._connected = false;
    if (this._ws) {
      // Remove handlers before closing to avoid triggering reconnect.
      this._ws.onclose = null as unknown as typeof this._ws.onclose;
      this._ws.onerror = null as unknown as typeof this._ws.onerror;
      this._ws.onmessage = null as unknown as typeof this._ws.onmessage;
      this._ws.close(1000, reason);
      this._ws = null;
    }
    this._rejectAllPending(new ConnectionError(reason));
    this.emit("disconnected", reason);
    if (shouldReconnect) this._maybeReconnect();
  }

  private _maybeReconnect(): void {
    if (!this._scheduler) return;
    const attempt = this._scheduler.attempt;
    const delayMs = this._scheduler.delayFor(attempt);

    const scheduled = this._scheduler.schedule(() => {
      this.emit("reconnecting", attempt + 1, delayMs);
      this.connect().catch(() => {
        // connect() failure triggers onclose → _maybeReconnect recursion.
      });
    });

    if (scheduled) {
      this.emit("reconnecting", attempt + 1, delayMs);
    }
  }

  // ---------------------------------------------------------------------------
  // Internal — message dispatch
  // ---------------------------------------------------------------------------

  private _handleMessage(raw: string): void {
    let envelope: InboundEnvelope;
    try {
      envelope = parseEnvelope(raw);
    } catch {
      // Malformed message — ignore silently in production.
      return;
    }

    // Raw envelope view (untyped) used for parseStreamEvent and E2A handling.
    const rawEnv = envelope as unknown as Record<string, unknown>;

    // Push to the active streamEvents() generator before lifecycle side-effects.
    if (this._pendingStreamEvents) {
      const event = parseStreamEvent(rawEnv);
      if (event !== null) {
        this._pendingStreamEvents.push(event);
      }
    }

    // Typed dispatch for known inbound envelope types.
    switch (envelope.type) {
      case MSG.ACK:
        this._onAck(envelope as AckEnvelope);
        break;
      case MSG.SESSIONS:
        this._onSessions(envelope as SessionsEnvelope);
        break;
      case MSG.SESSION_CREATED:
        this._onSessionCreated(envelope as SessionCreatedEnvelope);
        break;
      case MSG.TOKEN:
        this._onToken(envelope as TokenEnvelope);
        break;
      case MSG.DONE:
        this._onDone(envelope as DoneEnvelope);
        break;
      case MSG.ERROR:
        this._onError(envelope as ErrorEnvelope);
        break;
      case MSG.TOOL_CALL:
        void this._onToolCall(envelope as ToolCallEnvelope);
        break;
      case MSG.SKILLS_LIST:
        this._onSkillsList(envelope as SkillsListEnvelope);
        break;
      case MSG.SKILL_TOGGLED:
        this._onSkillToggled(envelope as SkillToggledEnvelope);
        break;
    }

    // E2A lifecycle: "e2a.complete" / "e2a.error" are not part of InboundEnvelope
    // but must trigger the same done/error lifecycle as their typed equivalents.
    const rawType = rawEnv["type"] as string;
    if (rawType === MSG.E2A_COMPLETE) {
      this._onDone({ type: "done", session_id: rawEnv["session_id"] as string | undefined });
    } else if (rawType === MSG.E2A_ERROR) {
      this._onError({ type: "error", message: (rawEnv["message"] as string) ?? "Unknown error" });
    }
  }

  private _onAck(env: AckEnvelope): void {
    if (env.protocol_version !== undefined) {
      // This is the connection handshake ack.
      this._connected = true;
      this._scheduler?.reset();
      const pending = this._pendingConnect;
      this._pendingConnect = null;
      pending?.resolve();
      this.emit("connected");
    }
    // Acks sent in response to chat (containing session_id) are intentionally
    // ignored; the chat operation resolves on "done".
  }

  private _onSessions(env: SessionsEnvelope): void {
    this.sessions._updateCache(env.sessions);
    const pending = this._pendingSessions;
    this._pendingSessions = null;
    pending?.resolve(env.sessions);
  }

  private _onSessionCreated(env: SessionCreatedEnvelope): void {
    const pending = this._pendingCreate;
    this._pendingCreate = null;
    pending?.resolve(env.session);
  }

  private _onToken(env: TokenEnvelope): void {
    this._config.onToken?.(env.text);
    // Token is already forwarded to _pendingStreamEvents via _handleMessage.
  }

  private _onDone(env: DoneEnvelope): void {
    this._config.onDone?.(env.session_id);
    // Resolve the send() promise (if active).
    const pending = this._pendingChat;
    this._pendingChat = null;
    pending?.resolve();
    // Signal the streamEvents() generator (if active).
    const se = this._pendingStreamEvents;
    if (se) {
      this._pendingStreamEvents = null;
      se.finish();
    }
  }

  private _onError(env: ErrorEnvelope): void {
    this._config.onError?.(env.message);
    const err = new Error(env.message);
    // Finish the streamEvents() generator with an error.
    const se = this._pendingStreamEvents;
    if (se) {
      this._pendingStreamEvents = null;
      se.finish(err);
    }
    // Reject whichever operation is currently pending.
    this._rejectAllPending(err);
  }

  private async _onToolCall(env: ToolCallEnvelope): Promise<void> {
    if (this._config.onToolCall) {
      try {
        const result = await this._config.onToolCall(env);
        this._sendRaw({ type: "tool_result", callId: env.callId, result });
      } catch (e) {
        this._sendRaw({
          type: "tool_result",
          callId: env.callId,
          error: e instanceof Error ? e.message : String(e),
        });
      }
    } else {
      // Auto-reject: no handler registered.
      this._sendRaw({
        type: "tool_result",
        callId: env.callId,
        error: "Tool calls are not supported by this client",
      });
    }
  }

  private _onSkillsList(env: SkillsListEnvelope): void {
    const pending = this._pendingSkills;
    this._pendingSkills = null;
    pending?.resolve(env.skills);
  }

  private _onSkillToggled(env: SkillToggledEnvelope): void {
    const pending = this._pendingSkillToggle;
    this._pendingSkillToggle = null;
    pending?.resolve({ id: env.id, enabled: env.enabled });
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private _sendRaw(envelope: object): void {
    if (!this._ws || this._ws.readyState !== 1 /* OPEN */) return;
    this._ws.send(JSON.stringify(envelope));
  }

  private _rejectAllPending(err: unknown): void {
    const ops = [
      this._pendingConnect,
      this._pendingSessions,
      this._pendingCreate,
      this._pendingChat,
      this._pendingSkills,
      this._pendingSkillToggle,
    ];
    this._pendingConnect = null;
    this._pendingSessions = null;
    this._pendingCreate = null;
    this._pendingChat = null;
    this._pendingSkills = null;
    this._pendingSkillToggle = null;
    for (const op of ops) op?.reject(err);
  }
}

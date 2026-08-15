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
  HistoryLoadedEnvelope,
  HistoryPage,
  InboundEnvelope,
  MediaItem,
  MemoryStats,
  MemoryUsageEnvelope,
  ModelInfo,
  ModelSwitchedEnvelope,
  ModelsListEnvelope,
  OutboundEnvelope,
  SessionInfo,
  SessionDeletedEnvelope,
  SessionRenamedEnvelope,
  SessionSwitchedEnvelope,
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
  /** Pending promise for listModels() */
  private _pendingModels: Resolver<ModelInfo[]> | null = null;
  /** Pending promise for switchModel() */
  private _pendingSwitchModel: Resolver<string> | null = null;
  /** Pending promise for switchSession() */
  private _pendingSwitchSession: Resolver<SessionInfo> | null = null;
  /** Pending promise for renameSession() */
  private _pendingRenameSession: Resolver<{ session_id: string; title: string }> | null = null;
  /** Pending promise for getHistory() */
  private _pendingHistory: Resolver<HistoryPage> | null = null;
  /** Pending promise for getMemoryUsage() */
  private _pendingMemory: Resolver<MemoryStats> | null = null;
  /** Pending promise for sessions.delete() */
  private _pendingDeleteSession: Resolver<string> | null = null;
  /** Active streamEvents() generator handle, if any. */
  private _pendingStreamEvents: StreamEventsHandle | null = null;

  /** Set to true once the connect ack is received. */
  private _connected = false;
  /**
   * The session ID assigned by the server in the connection ack.
   * `null` until `connect()` resolves (and the server sends `ack`).
   */
  private _sessionId: string | null = null;

  /** Exposed session manager. */
  readonly sessions: SessionManager;

  /**
   * The session ID assigned by the server in the connection acknowledgement.
   * Available after `connect()` resolves.  Useful when the server auto-creates
   * a default session on connect.
   */
  get sessionId(): string | null {
    return this._sessionId;
  }

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
   * @param options  Optional mode, channelId, contextPrefix, sessionId, mediaItems.
   */
  send(message: string, options?: StreamEventsOptions): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected. Call connect() first."));
        return;
      }
      this._pendingChat = { resolve, reject };
      const text = JiuwenSwarmClient._applyContextPrefix(
        message,
        options?.contextPrefix,
      );
      this._sendRaw({
        type: MSG.CHAT,
        message: text,
        session_id: options?.sessionId ?? this.sessions.activeId ?? undefined,
        mode: options?.mode ?? this._config.mode,
        channel_id: options?.channelId ?? this._config.channelId,
        media_items: options?.mediaItems,
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
      media_items: options?.mediaItems,
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
  // Public API — models (IDE parity)
  // ---------------------------------------------------------------------------

  /**
   * Fetch the list of available LLM models from the server.
   *
   * ```typescript
   * const models = await client.listModels();
   * models.forEach(m => console.log(m.id, m.active ? "(active)" : ""));
   * ```
   */
  listModels(): Promise<ModelInfo[]> {
    return new Promise<ModelInfo[]>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingModels = { resolve, reject };
      this._sendRaw({ type: MSG.MODELS });
    });
  }

  /**
   * Switch the active LLM model for the current session.
   *
   * ```typescript
   * await client.switchModel("gpt-4o");
   * ```
   *
   * @param modelId  Model identifier (from `ModelInfo.id`).
   */
  switchModel(modelId: string): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingSwitchModel = { resolve, reject };
      this._sendRaw({ type: MSG.SWITCH_MODEL, model_id: modelId });
    });
  }

  // ---------------------------------------------------------------------------
  // Public API — session lifecycle (IDE parity)
  // ---------------------------------------------------------------------------

  /**
   * Switch the active gateway session to an existing session by ID.
   *
   * ```typescript
   * const session = await client.switchSession("sess_abc123");
   * client.sessions.setActive(session.id);
   * ```
   *
   * @param sessionId  ID of the session to switch to.
   */
  switchSession(sessionId: string): Promise<SessionInfo> {
    return new Promise<SessionInfo>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingSwitchSession = { resolve, reject };
      this._sendRaw({ type: MSG.SWITCH_SESSION, session_id: sessionId });
    });
  }

  /**
   * Rename the active session.
   *
   * ```typescript
   * await client.renameSession("sess_abc123", "My research project");
   * ```
   *
   * @param sessionId  Session to rename.
   * @param title      New human-readable title.
   */
  renameSession(
    sessionId: string,
    title: string,
  ): Promise<{ session_id: string; title: string }> {
    return new Promise((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingRenameSession = { resolve, reject };
      this._sendRaw({ type: MSG.RENAME_SESSION, session_id: sessionId, title });
    });
  }

  /**
   * Load a page of message history for a session.
   *
   * ```typescript
   * const page = await client.getHistory("sess_abc123", 1);
   * page.messages.forEach(m => console.log(m.role, m.content));
   * ```
   *
   * @param sessionId  Session whose history to load.
   * @param page       1-based page number (default: 1).
   */
  getHistory(sessionId: string, page = 1): Promise<HistoryPage> {
    return new Promise<HistoryPage>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingHistory = { resolve, reject };
      this._sendRaw({ type: MSG.HISTORY_GET, session_id: sessionId, page });
    });
  }

  // ---------------------------------------------------------------------------
  // Public API — memory (IDE parity)
  // ---------------------------------------------------------------------------

  /**
   * Fetch process and system memory statistics from the gateway.
   *
   * ```typescript
   * const stats = await client.getMemoryUsage();
   * console.log(`RSS: ${stats.process_rss_mb} MB`);
   * ```
   */
  getMemoryUsage(): Promise<MemoryStats> {
    return new Promise<MemoryStats>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingMemory = { resolve, reject };
      this._sendRaw({ type: MSG.MEMORY_COMPUTE });
    });
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

  _deleteSession(sessionId: string): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected."));
        return;
      }
      this._pendingDeleteSession = { resolve, reject };
      this._sendRaw({ type: MSG.DELETE_SESSION, session_id: sessionId });
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
      case MSG.MODELS_LIST:
        this._onModelsList(envelope as ModelsListEnvelope);
        break;
      case MSG.MODEL_SWITCHED:
        this._onModelSwitched(envelope as ModelSwitchedEnvelope);
        break;
      case MSG.SESSION_SWITCHED:
        this._onSessionSwitched(envelope as SessionSwitchedEnvelope);
        break;
      case MSG.SESSION_RENAMED:
        this._onSessionRenamed(envelope as SessionRenamedEnvelope);
        break;
      case MSG.HISTORY_LOADED:
        this._onHistoryLoaded(envelope as HistoryLoadedEnvelope);
        break;
      case MSG.MEMORY_USAGE:
        this._onMemoryUsage(envelope as MemoryUsageEnvelope);
        break;
      case MSG.SESSION_DELETED:
        this._onSessionDeleted(envelope as SessionDeletedEnvelope);
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
      // Persist the server-assigned session ID if present.
      if (env.session_id) this._sessionId = env.session_id;
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

  private _onModelsList(env: ModelsListEnvelope): void {
    const pending = this._pendingModels;
    this._pendingModels = null;
    pending?.resolve(env.models);
  }

  private _onModelSwitched(env: ModelSwitchedEnvelope): void {
    const pending = this._pendingSwitchModel;
    this._pendingSwitchModel = null;
    pending?.resolve(env.model_id);
  }

  private _onSessionSwitched(env: SessionSwitchedEnvelope): void {
    // Update the session cache and active pointer.
    this.sessions._updateCache([env.session]);
    this.sessions.setActive(env.session.id);
    const pending = this._pendingSwitchSession;
    this._pendingSwitchSession = null;
    pending?.resolve(env.session);
  }

  private _onSessionRenamed(env: SessionRenamedEnvelope): void {
    const pending = this._pendingRenameSession;
    this._pendingRenameSession = null;
    pending?.resolve({ session_id: env.session_id, title: env.title });
  }

  private _onHistoryLoaded(env: HistoryLoadedEnvelope): void {
    const page: HistoryPage = {
      session_id: env.session_id,
      page: env.page,
      total_pages: env.total_pages,
      messages: env.messages,
    };
    const pending = this._pendingHistory;
    this._pendingHistory = null;
    pending?.resolve(page);
  }

  private _onMemoryUsage(env: MemoryUsageEnvelope): void {
    const stats: MemoryStats = {
      process_rss_mb: env.process_rss_mb,
      system_total_mb: env.system_total_mb,
      system_free_mb: env.system_free_mb,
      context_tokens: env.context_tokens,
    };
    const pending = this._pendingMemory;
    this._pendingMemory = null;
    pending?.resolve(stats);
  }

  private _onSessionDeleted(env: SessionDeletedEnvelope): void {
    const pending = this._pendingDeleteSession;
    this._pendingDeleteSession = null;
    pending?.resolve(env.session_id);
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
      this._pendingModels,
      this._pendingSwitchModel,
      this._pendingSwitchSession,
      this._pendingRenameSession,
      this._pendingHistory,
      this._pendingMemory,
      this._pendingDeleteSession,
    ];
    this._pendingConnect = null;
    this._pendingSessions = null;
    this._pendingCreate = null;
    this._pendingChat = null;
    this._pendingSkills = null;
    this._pendingSkillToggle = null;
    this._pendingModels = null;
    this._pendingSwitchModel = null;
    this._pendingSwitchSession = null;
    this._pendingRenameSession = null;
    this._pendingDeleteSession = null;
    this._pendingHistory = null;
    this._pendingMemory = null;
    for (const op of ops) op?.reject(err);
  }
}

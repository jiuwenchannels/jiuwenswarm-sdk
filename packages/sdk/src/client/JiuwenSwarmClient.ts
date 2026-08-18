/**
 * JiuwenSwarmClient — WebSocket client for the JiuwenSwarm gateway.
 *
 * The gateway speaks a JSON-RPC style protocol:
 *   - client → server: `{type:"req", id, method, params, is_stream}`
 *   - server → client (method response): `{type:"res", id, ok, payload, error}`
 *   - server → client (stream/event): `{type:"event", event, payload}`
 *
 * ```typescript
 * const client = new JiuwenSwarmClient({
 *   url: "ws://localhost:19000/ws",
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
  MetricsEnvelope,
  MetricsInfo,
  RewindableEnvelope,
  RewindDoneEnvelope,
  SessionDeletedEnvelope,
  SessionExport,
  SessionExportedEnvelope,
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
import { ConnectionError } from "../protocol/validate";
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
  /**
   * Fired when the server pushes gateway-level metrics.
   * Subscribe: `client.on("metrics", (info) => console.log(info.requests_total))`.
   */
  metrics: [info: MetricsInfo];
  /**
   * Fired when the server indicates a message is rewindable.
   * Subscribe: `client.on("rewindable", (messageId) => ...)`.
   */
  rewindable: [messageId: string];
  /**
   * Fired when a rewind operation completes on the server.
   * Subscribe: `client.on("rewind_done", (messageId) => ...)`.
   */
  rewind_done: [messageId: string];
};

type Resolver<T> = { resolve: (v: T) => void; reject: (e: unknown) => void };

/** Internal handle for an active `streamEvents()` generator. */
type StreamEventsHandle = {
  push: (event: StreamEvent) => void;
  finish: (err?: Error) => void;
};

/** Default timeout for a single RPC request (ms). */
const REQUEST_TIMEOUT_MS = 20_000;
/** Default timeout for the connection handshake (ms). */
const CONNECT_TIMEOUT_MS = 15_000;

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

function generateId(): string {
  if (
    typeof globalThis !== "undefined" &&
    typeof (globalThis as { crypto?: { randomUUID?: () => string } }).crypto?.randomUUID === "function"
  ) {
    return (
      globalThis as { crypto: { randomUUID: () => string } }
    ).crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : value == null ? fallback : String(value);
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
  private _connectTimer: ReturnType<typeof setTimeout> | null = null;
  /** Pending promise for send() */
  private _pendingChat: Resolver<void> | null = null;
  /** Pending request map keyed by RPC request id. */
  private _pendingRpc: Map<
    string,
    { resolve: (payload: Record<string, unknown>) => void; reject: (e: unknown) => void }
  > = new Map();
  /** Active streamEvents() generator handle, if any. */
  private _pendingStreamEvents: StreamEventsHandle | null = null;

  /** Set to true once the connection.ack event is received. */
  private _connected = false;
  /**
   * The session ID assigned by the server in the connection ack.
   * `null` until `connect()` resolves.
   */
  private _sessionId: string | null = null;

  /** Exposed session manager. */
  readonly sessions: SessionManager;

  /**
   * The session ID assigned by the server in the connection acknowledgement.
   * Available after `connect()` resolves.
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
   * Open the WebSocket connection and wait for the gateway's `connection.ack`.
   *
   * Resolves when the server sends the `connection.ack` event.
   * Rejects on connection errors or timeout.
   */
  connect(): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      if (this._connected) {
        resolve();
        return;
      }
      this._pendingConnect = { resolve, reject };
      this._connectTimer = setTimeout(() => {
        if (this._pendingConnect) {
          const pending = this._pendingConnect;
          this._pendingConnect = null;
          pending.reject(new ConnectionError("Connection timed out waiting for connection.ack"));
        }
      }, CONNECT_TIMEOUT_MS);
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
   * Resolves when the server sends the `chat.final` event.
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
      this._sendRpc(
        "chat.send",
        {
          session_id: options?.sessionId ?? this.sessions.activeId ?? undefined,
          content: text,
          query: text,
          mode: options?.mode ?? this._config.mode ?? "agent",
          media_items: options?.mediaItems,
          model_name: options?.modelName,
        },
        { stream: true },
      );
    });
  }

  /**
   * Send a chat message and iterate over typed `StreamEvent` objects as they
   * arrive from the server.
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

    this._sendRpc(
      "chat.send",
      {
        session_id: options?.sessionId ?? this.sessions.activeId ?? undefined,
        content: message,
        query: message,
        mode: options?.mode ?? this._config.mode ?? "agent",
        channel_id: options?.channelId ?? this._config.channelId,
        media_items: options?.mediaItems,
        model_name: options?.modelName,
      },
      { stream: true },
    );

    try {
      while (true) {
        while (buffer.length > 0) {
          yield buffer.shift()!;
        }
        if (done) {
          if (error) throw error;
          break;
        }
        await new Promise<void>((resolve) => {
          notify = resolve;
        });
      }
      while (buffer.length > 0) {
        yield buffer.shift()!;
      }
    } finally {
      if (this._pendingStreamEvents?.finish === finish) {
        this._pendingStreamEvents = null;
      }
    }
  }

  /**
   * Fire-and-forget interrupt: ask the server to cancel or pause the current
   * agent turn.  No response is expected.
   */
  interrupt(): void {
    this._sendRpc("chat.interrupt", {
      session_id: this.sessions.activeId ?? this._sessionId ?? undefined,
      intent: "cancel",
      mode: this._config.mode ?? "agent",
    });
  }

  // ---------------------------------------------------------------------------
  // Public API — rewind (IDE parity)
  // ---------------------------------------------------------------------------

  /** Rewind the conversation to a previous message (fire-and-forget). */
  rewind(messageId?: string): void {
    this._sendRpc("session.rewind", {
      message_id: messageId,
      session_id: this.sessions.activeId ?? this._sessionId ?? undefined,
    });
  }

  // ---------------------------------------------------------------------------
  // Public API — session export (IDE parity)
  // ---------------------------------------------------------------------------

  exportSession(sessionId: string, format?: string): Promise<SessionExport> {
    return this._request("session.export", { session_id: sessionId, format }).then(
      (payload) => ({
        session_id: asString(payload.session_id, sessionId),
        url: typeof payload.url === "string" ? payload.url : undefined,
        data: typeof payload.data === "string" ? payload.data : undefined,
        format: typeof payload.format === "string" ? payload.format : format,
      }),
    );
  }

  /**
   * Low-level envelope send.
   * Serialises `envelope` to JSON and writes it to the WebSocket.
   */
  sendEnvelope(envelope: OutboundEnvelope): void {
    this._sendRaw(envelope);
  }

  // ---------------------------------------------------------------------------
  // Public API — skills
  // ---------------------------------------------------------------------------

  listSkills(): Promise<SkillInfo[]> {
    return this._request("skills.list", {}).then((payload) => {
      const raw = Array.isArray(payload.skills) ? payload.skills : [];
      return raw.map((s) => JiuwenSwarmClient._toSkillInfo(s as Record<string, unknown>));
    });
  }

  toggleSkill(id: string, enabled: boolean): Promise<{ id: string; enabled: boolean }> {
    return this._request("skills.toggle", { skill_id: id, enabled }).then(() => ({ id, enabled }));
  }

  // ---------------------------------------------------------------------------
  // Public API — HITL
  // ---------------------------------------------------------------------------

  sendAnswer(requestId: string, answers: Record<string, string>): void {
    this._sendRpc("chat.user_answer", {
      request_id: requestId,
      answers,
      source: "confirm_interrupt",
      session_id: this.sessions.activeId ?? this._sessionId ?? undefined,
      mode: this._config.mode ?? "agent",
    });
  }

  // ---------------------------------------------------------------------------
  // Public API — models
  // ---------------------------------------------------------------------------

  listModels(): Promise<ModelInfo[]> {
    return this._request("models.list", {}).then((payload) => {
      const raw = Array.isArray(payload.models) ? payload.models : [];
      const active = asString(payload.active_model) || undefined;
      return raw.map((m) => JiuwenSwarmClient._toModelInfo(m as Record<string, unknown>, active));
    });
  }

  switchModel(modelId: string): Promise<string> {
    return this._request("models.switch", { model_id: modelId }).then(() => modelId);
  }

  // ---------------------------------------------------------------------------
  // Public API — session lifecycle (IDE parity)
  // ---------------------------------------------------------------------------

  switchSession(sessionId: string): Promise<SessionInfo> {
    return this._request("session.switch", { session_id: sessionId }).then((payload) => {
      const session = JiuwenSwarmClient._toSessionInfo(payload, sessionId);
      this.sessions._updateCache([session]);
      this.sessions.setActive(session.id);
      return session;
    });
  }

  renameSession(
    sessionId: string,
    title: string,
  ): Promise<{ session_id: string; title: string }> {
    return this._request("session.rename", { session_id: sessionId, title }).then(() => ({
      session_id: sessionId,
      title,
    }));
  }

  getHistory(sessionId: string, page = 1): Promise<HistoryPage> {
    return this._request("history.get", { session_id: sessionId, page_idx: page }).then(
      (payload) => ({
        session_id: asString(payload.session_id, sessionId),
        page: typeof payload.page === "number" ? payload.page : page,
        total_pages: typeof payload.total_pages === "number" ? payload.total_pages : 1,
        messages: Array.isArray(payload.messages)
          ? payload.messages.map((m) => m as never)
          : [],
      }),
    );
  }

  // ---------------------------------------------------------------------------
  // Public API — memory
  // ---------------------------------------------------------------------------

  getMemoryUsage(): Promise<MemoryStats> {
    return this._request("memory.compute", {}).then((payload) => ({
      process_rss_mb: typeof payload.rss_mb === "number" ? payload.rss_mb : 0,
      system_total_mb: typeof payload.total_mb === "number" ? payload.total_mb : 0,
      system_free_mb: typeof payload.available_mb === "number" ? payload.available_mb : 0,
      context_tokens: typeof payload.context_tokens === "number" ? payload.context_tokens : undefined,
    }));
  }

  // ---------------------------------------------------------------------------
  // SessionDelegate implementation (called by SessionManager)
  // ---------------------------------------------------------------------------

  _listSessions(): Promise<SessionInfo[]> {
    return this._request("session.list", { limit: 50 }).then((payload) => {
      const raw = Array.isArray(payload.sessions) ? payload.sessions : [];
      return raw.map((s) => JiuwenSwarmClient._toSessionInfo(s as Record<string, unknown>, undefined));
    });
  }

  _createSession(params: {
    title?: string;
    agent_id?: string;
    mode?: AgentMode;
  }): Promise<SessionInfo> {
    return this._request("session.create", {
      title: params.title,
      mode: params.mode ?? this._config.mode ?? "agent",
      create_token: generateId(),
    }).then((payload) => {
      const id = asString(payload.session_id) || asString(payload.sessionId) || "";
      const session = JiuwenSwarmClient._toSessionInfo(payload, id || undefined);
      if (!session.id) session.id = id;
      if (params.title && !session.title) session.title = params.title;
      return session;
    });
  }

  _deleteSession(sessionId: string): Promise<string> {
    return this._request("session.delete", { session_id: sessionId }).then(() => sessionId);
  }

  // ---------------------------------------------------------------------------
  // Static helpers — mapping
  // ---------------------------------------------------------------------------

  static _applyContextPrefix(prompt: string, contextPrefix?: string): string {
    if (!contextPrefix || contextPrefix.trim() === "") {
      return prompt;
    }
    return `${contextPrefix.trimEnd()}\n\n---\n\n${prompt}`;
  }

  private static _toSessionInfo(
    raw: Record<string, unknown>,
    fallbackId?: string,
  ): SessionInfo {
    const id = asString(raw.session_id) || asString(raw.id) || fallbackId || "";
    const mode = asString(raw.mode, "agent") as AgentMode;
    return {
      id,
      title: asString(raw.title),
      agent_id: asString(raw.agent_id, ""),
      mode,
      created_at: asString(raw.created_at),
    };
  }

  private static _toModelInfo(
    raw: Record<string, unknown>,
    active?: string,
  ): ModelInfo {
    const id = asString(raw.model_name) || asString(raw.id) || asString(raw.alias);
    return {
      id,
      name: asString(raw.alias, id),
      provider: asString(raw.model_provider),
      context_length:
        typeof raw.context_length === "number" ? raw.context_length : undefined,
      active: active !== undefined ? id === active : undefined,
    };
  }

  private static _toSkillInfo(raw: Record<string, unknown>): SkillInfo {
    const id = asString(raw.skill_id) || asString(raw.id);
    return {
      id,
      name: asString(raw.name, id),
      description: asString(raw.description),
      enabled: raw.enabled === true || raw.enabled === "true",
    };
  }

  // ---------------------------------------------------------------------------
  // Internal — socket lifecycle
  // ---------------------------------------------------------------------------

  private _openSocket(): void {
    const WS = getWebSocket();
    const ws = new WS(this._config.url);
    this._ws = ws;

    ws.onopen = () => {
      // The gateway sends `connection.ack` automatically on connect; there is
      // no client-side `connect` request to send.
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
  // Internal — outbound
  // ---------------------------------------------------------------------------

  private _sendRpc(
    method: string,
    params: Record<string, unknown>,
    opts?: { stream?: boolean },
  ): string {
    const id = generateId();
    if (!this._ws || this._ws.readyState !== 1 /* OPEN */) return id;
    const frame: Record<string, unknown> = {
      type: "req",
      id,
      method,
      params,
      timestamp: Date.now() / 1000,
    };
    if (opts?.stream) frame["is_stream"] = true;
    this._ws.send(JSON.stringify(frame));
    return id;
  }

  /** Send a method request and resolve with the gateway `res.payload`. */
  private _request(
    method: string,
    params: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    return new Promise<Record<string, unknown>>((resolve, reject) => {
      if (!this._connected || !this._ws) {
        reject(new ConnectionError("Not connected. Call connect() first."));
        return;
      }
      const id = this._sendRpc(method, params);
      const timer = setTimeout(() => {
        this._pendingRpc.delete(id);
        reject(new Error(`Request '${method}' timed out`));
      }, REQUEST_TIMEOUT_MS);
      this._pendingRpc.set(id, {
        resolve: (payload) => {
          clearTimeout(timer);
          resolve(payload);
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        },
      });
    });
  }

  /**
   * Legacy flat-envelope send. Translates the flat envelope into a gateway
   * RPC request on a best-effort basis.
   */
  private _sendRaw(envelope: object): void {
    const env = envelope as Record<string, unknown>;
    const type = asString(env.type);
    const method = JiuwenSwarmClient._RPC_METHOD[type] ?? type;
    const params = JiuwenSwarmClient._flatToRpcParams(type, envelope);
    this._sendRpc(method, params, { stream: type === "chat" });
  }

  private static readonly _RPC_METHOD: Record<string, string> = {
    connect: "initialize",
    sessions: "session.list",
    create_session: "session.create",
    chat: "chat.send",
    tool_result: "tool.result",
    skills: "skills.list",
    skill_toggle: "skills.toggle",
    hitl_answer: "chat.user_answer",
    "chat.interrupt": "chat.interrupt",
    "models.list": "models.list",
    "models.switch": "models.switch",
    "session.switch": "session.switch",
    "session.rename": "session.rename",
    "session.delete": "session.delete",
    "history.get": "history.get",
    "memory.compute": "memory.compute",
    rewind: "session.rewind",
    "session.export": "session.export",
  };

  private static _flatToRpcParams(
    type: string,
    envelope: object,
  ): Record<string, unknown> {
    const { type: _t, ...rest } = envelope as Record<string, unknown>;
    void _t;

    if (type === "chat" && "message" in rest) {
      const { message, ...remaining } = rest;
      return { content: message, query: message, ...remaining };
    }
    if (type === "skill_toggle" && "id" in rest) {
      const { id, ...remaining } = rest;
      return { skill_id: id, ...remaining };
    }
    if (type === "history.get" && "page" in rest) {
      const { page, ...remaining } = rest;
      return { page_idx: page, ...remaining };
    }
    return rest;
  }

  // ---------------------------------------------------------------------------
  // Internal — inbound dispatch
  // ---------------------------------------------------------------------------

  private _handleMessage(raw: string): void {
    let data: Record<string, unknown>;
    try {
      const parsed = JSON.parse(raw);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return;
      data = parsed as Record<string, unknown>;
    } catch {
      return;
    }

    const frameType = asString(data.type);

    // Gateway RPC response frame.
    if (frameType === "res") {
      this._handleResFrame(data);
      return;
    }

    // Gateway event frame → normalize to the SDK's flat envelope vocabulary.
    if (frameType === "event") {
      const flat = this._normalizeEventFrame(data);
      if (flat === null) return;
      data = flat;
    }

    // From here, `data` is a flat envelope (either already-flat or normalized).
    const envelope = data as unknown as InboundEnvelope;
    const rawEnv = data;

    // Push to the active streamEvents() generator before lifecycle side-effects.
    if (this._pendingStreamEvents) {
      const event = parseStreamEvent(rawEnv);
      if (event !== null) {
        this._pendingStreamEvents.push(event);
      }
    }

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
      case MSG.REWINDABLE:
        this._onRewindable(envelope as RewindableEnvelope);
        break;
      case MSG.REWIND_DONE:
        this._onRewindDone(envelope as RewindDoneEnvelope);
        break;
      case MSG.SESSION_EXPORTED:
        this._onSessionExported(envelope as SessionExportedEnvelope);
        break;
      case MSG.METRICS:
        this._onMetrics(envelope as MetricsEnvelope);
        break;
    }
  }

  /** Handle a gateway `res` frame, correlating by request id. */
  private _handleResFrame(data: Record<string, unknown>): void {
    const id = asString(data.id);
    if (!id) return;
    const pending = this._pendingRpc.get(id);
    if (!pending) return;
    this._pendingRpc.delete(id);

    if (data.ok === true) {
      const payload =
        typeof data.payload === "object" && data.payload !== null
          ? (data.payload as Record<string, unknown>)
          : {};
      pending.resolve(payload);
    } else {
      const payload =
        typeof data.payload === "object" && data.payload !== null
          ? (data.payload as Record<string, unknown>)
          : {};
      const error =
        asString(data.error) || asString(payload.error) || "request failed";
      pending.reject(new Error(error));
    }
  }

  /**
   * Normalize a gateway `event` frame into the SDK's flat envelope vocabulary.
   * Returns `null` when the event carries no SDK-relevant meaning.
   */
  private _normalizeEventFrame(data: Record<string, unknown>): Record<string, unknown> | null {
    const event = asString(data.event);
    const payload =
      typeof data.payload === "object" && data.payload !== null
        ? (data.payload as Record<string, unknown>)
        : {};

    switch (event) {
      case "connection.ack":
        return {
          type: "ack",
          protocol_version: asString(payload.protocol_version, "1.0"),
          session_id:
            typeof payload.session_id === "string" ? payload.session_id : undefined,
        };

      case "chat.delta":
        return { type: "token", text: asString(payload.content) };

      case "chat.reasoning":
        return { type: "reasoning", text: asString(payload.content) };

      case "chat.tool_call":
        return {
          type: "tool_call",
          name: asString(payload.tool_name) || asString(payload.name, "?"),
          arguments:
            typeof payload.arguments === "object" && payload.arguments !== null
              ? payload.arguments
              : typeof payload.input === "object" && payload.input !== null
                ? payload.input
                : {},
          callId: asString(payload.call_id) || asString(payload.id),
        };

      case "chat.tool_result":
        return {
          type: "tool_result_server",
          callId: asString(payload.call_id) || asString(payload.id),
          result:
            typeof payload.content === "string" ? payload.content : undefined,
          error:
            typeof payload.error === "string" ? payload.error : undefined,
        };

      case "chat.final": {
        const inner = asString(payload.event_type);
        // team.error is broadcast through the chat.final envelope.
        if (inner === "team.error") {
          return {
            type: "error",
            message: asString(payload.error) || asString(payload.message, "team error"),
          };
        }
        return {
          type: "done",
          session_id:
            typeof payload.session_id === "string" ? payload.session_id : undefined,
        };
      }

      case "chat.error":
        return {
          type: "error",
          message: asString(payload.error) || asString(payload.message, "unknown error"),
        };

      case "chat.processing_status":
        return {
          type: "status",
          status: payload.is_processing === true ? "processing" : "idle",
          agent_id:
            typeof payload.agent_id === "string" ? payload.agent_id : undefined,
        };

      case "chat.ask_user_question":
      case "plan.approval_required":
        return {
          type: "confirm_interrupt",
          request_id: asString(payload.request_id),
          question: asString(payload.question) || asString(payload.message),
        };

      case "chat.usage_metadata":
      case "usage":
        return {
          type: "usage",
          input_tokens: typeof payload.input_tokens === "number" ? payload.input_tokens : 0,
          output_tokens: typeof payload.output_tokens === "number" ? payload.output_tokens : 0,
          cost_usd: typeof payload.cost_usd === "number" ? payload.cost_usd : undefined,
        };

      case "team.member.spawned":
        return {
          type: "team.member.spawned",
          agent_id: asString(payload.agent_id),
          role: typeof payload.role === "string" ? payload.role : undefined,
        };

      case "team.member.status_changed":
        return {
          type: "team.member.status_changed",
          agent_id: asString(payload.agent_id),
          status: asString(payload.status),
        };

      case "team.task.created":
        return {
          type: "team.task.created",
          task_id: asString(payload.task_id),
          assigned_to: asString(payload.assigned_to),
          description: asString(payload.description),
        };

      case "team.task.completed":
        return {
          type: "team.task.completed",
          task_id: asString(payload.task_id),
          agent_id: asString(payload.agent_id),
        };

      case "team.handoff":
        return {
          type: "team.handoff",
          from_agent_id: asString(payload.from_agent_id),
          to_agent_id: asString(payload.to_agent_id),
          summary: typeof payload.summary === "string" ? payload.summary : undefined,
        };

      default:
        return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Internal — flat envelope handlers
  // ---------------------------------------------------------------------------

  private _onAck(env: AckEnvelope): void {
    this._connected = true;
    if (env.session_id) this._sessionId = env.session_id;
    this._scheduler?.reset();
    if (this._connectTimer) {
      clearTimeout(this._connectTimer);
      this._connectTimer = null;
    }
    const pending = this._pendingConnect;
    this._pendingConnect = null;
    pending?.resolve();
    this.emit("connected");
  }

  private _onSessions(env: SessionsEnvelope): void {
    this.sessions._updateCache(env.sessions);
  }

  private _onSessionCreated(env: SessionCreatedEnvelope): void {
    this.sessions._updateCache([env.session]);
  }

  private _onToken(env: TokenEnvelope): void {
    this._config.onToken?.(env.text);
  }

  private _onDone(env: DoneEnvelope): void {
    this._config.onDone?.(env.session_id);
    const pending = this._pendingChat;
    this._pendingChat = null;
    pending?.resolve();
    const se = this._pendingStreamEvents;
    if (se) {
      this._pendingStreamEvents = null;
      se.finish();
    }
  }

  private _onError(env: ErrorEnvelope): void {
    this._config.onError?.(env.message);
    const err = new Error(env.message);
    const se = this._pendingStreamEvents;
    if (se) {
      this._pendingStreamEvents = null;
      se.finish(err);
    }
    const pending = this._pendingChat;
    this._pendingChat = null;
    pending?.reject(err);
  }

  private async _onToolCall(env: ToolCallEnvelope): Promise<void> {
    if (this._config.onToolCall) {
      try {
        const result = await this._config.onToolCall(env);
        this._sendRpc("tool.result", { call_id: env.callId, result });
      } catch (e) {
        this._sendRpc("tool.result", {
          call_id: env.callId,
          error: e instanceof Error ? e.message : String(e),
        });
      }
    } else {
      this._sendRpc("tool.result", {
        call_id: env.callId,
        error: "Tool calls are not supported by this client",
      });
    }
  }

  private _onSkillsList(env: SkillsListEnvelope): void {
    void env;
  }

  private _onSkillToggled(env: SkillToggledEnvelope): void {
    void env;
  }

  private _onModelsList(env: ModelsListEnvelope): void {
    void env;
  }

  private _onModelSwitched(env: ModelSwitchedEnvelope): void {
    void env;
  }

  private _onSessionSwitched(env: SessionSwitchedEnvelope): void {
    this.sessions._updateCache([env.session]);
    this.sessions.setActive(env.session.id);
  }

  private _onSessionRenamed(env: SessionRenamedEnvelope): void {
    void env;
  }

  private _onHistoryLoaded(env: HistoryLoadedEnvelope): void {
    void env;
  }

  private _onMemoryUsage(env: MemoryUsageEnvelope): void {
    void env;
  }

  private _onSessionDeleted(env: SessionDeletedEnvelope): void {
    void env;
  }

  private _onRewindable(env: RewindableEnvelope): void {
    this.emit("rewindable", env.message_id);
  }

  private _onRewindDone(env: RewindDoneEnvelope): void {
    this.emit("rewind_done", env.message_id);
  }

  private _onSessionExported(env: SessionExportedEnvelope): void {
    void env;
  }

  private _onMetrics(env: MetricsEnvelope): void {
    this.emit("metrics", {
      requests_total: env.requests_total,
      tokens_total: env.tokens_total,
      active_sessions: env.active_sessions,
      uptime_s: env.uptime_s,
    });
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private _rejectAllPending(err: unknown): void {
    if (this._connectTimer) {
      clearTimeout(this._connectTimer);
      this._connectTimer = null;
    }
    const pendingConnect = this._pendingConnect;
    this._pendingConnect = null;
    pendingConnect?.reject(err);

    const pendingChat = this._pendingChat;
    this._pendingChat = null;
    pendingChat?.reject(err);

    const se = this._pendingStreamEvents;
    if (se) {
      this._pendingStreamEvents = null;
      se.finish(err instanceof Error ? err : new Error(String(err)));
    }

    for (const [, pending] of this._pendingRpc) {
      pending.reject(err);
    }
    this._pendingRpc.clear();
  }
}

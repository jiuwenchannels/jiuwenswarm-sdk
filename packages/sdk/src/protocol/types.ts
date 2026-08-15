/**
 * Protocol types for the JiuwenSwarm WebSocket gateway.
 *
 * All messages exchanged over the WebSocket are JSON objects with a "type"
 * discriminator field (InboundEnvelope / OutboundEnvelope unions below).
 */

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/** Agent operating modes, mirroring Python SDK's `AgentMode`. */
export type AgentMode = "agent" | "code" | "team" | "code.team";

/**
 * Named constants for agent operating modes.
 *
 * @example
 * ```typescript
 * import { AgentModeConstants } from "@jiuwenswarm/sdk";
 * const session = await client.sessions.create("Dev", undefined, AgentModeConstants.CODE);
 * ```
 */
export const AgentModeConstants = {
  /** Standard conversational agent (default). */
  AGENT: "agent" as const,
  /** Code-focused agent with extra IDE context. */
  CODE: "code" as const,
  /** Multi-agent team coordinator. */
  TEAM: "team" as const,
  /** Code-focused team mode. */
  CODE_TEAM: "code.team" as const,
  /** Alias for AGENT. */
  DEFAULT: "agent" as const,
} as const;

/** Channel identifiers that tell the server which surface is connecting. */
export type ChannelId = "api" | "jupyter" | "ide" | "browser" | "cli" | "mobile";

/**
 * Named constants for channel identifiers, mirroring Python SDK's `ChannelId`.
 *
 * @example
 * ```typescript
 * import { ChannelIdConstants } from "@jiuwenswarm/sdk";
 * // passed via streamEvents() options:
 * client.streamEvents("prompt", { channelId: ChannelIdConstants.IDE });
 * ```
 */
export const ChannelIdConstants = {
  API: "api" as const,
  JUPYTER: "jupyter" as const,
  IDE: "ide" as const,
  BROWSER: "browser" as const,
  CLI: "cli" as const,
  MOBILE: "mobile" as const,
} as const;

/** Information about an installed skill/plugin. */
export interface SkillInfo {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  version?: string;
}

/** Information about an available LLM model. */
export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  /** Token context window size. */
  context_length?: number;
  /** Whether this is the currently active model. */
  active?: boolean;
}

/**
 * A media item attached to a chat message (image, audio, or file).
 * Mirrors the Python SDK's `MediaItem` / `ImageInput` structures.
 */
export interface MediaItem {
  /** MIME type, e.g. `"image/png"`, `"audio/wav"`, `"application/pdf"`. */
  mime_type: string;
  /**
   * Base-64-encoded content (for small blobs) OR a URL/path the server
   * can fetch.  Exactly one of `data` or `url` must be provided.
   */
  data?: string;
  url?: string;
  /** Optional display name / filename shown in the chat UI. */
  name?: string;
}

/** A single page of session history messages. */
export interface HistoryPage {
  session_id: string;
  page: number;
  total_pages: number;
  messages: ChatMessage[];
}

/**
 * Gateway-level metrics pushed periodically by the server.
 * Listen via `client.on("metrics", handler)`.
 */
export interface MetricsInfo {
  /** Total WebSocket requests handled since gateway start. */
  requests_total: number;
  /** Cumulative token count across all sessions. */
  tokens_total: number;
  /** Number of currently connected sessions. */
  active_sessions: number;
  /** Gateway uptime in seconds. */
  uptime_s: number;
}

/**
 * The result of an `exportSession()` call.
 * Contains either a download URL or inline base-64 data.
 */
export interface SessionExport {
  session_id: string;
  /** Pre-signed download URL (valid for a limited time). */
  url?: string;
  /** Inline base-64-encoded export data (for small exports). */
  data?: string;
  /** Export format, e.g. `"markdown"`, `"json"`, `"html"`. */
  format?: string;
}

/** Process and system memory statistics returned by `getMemoryUsage()`. */
export interface MemoryStats {
  /** Resident set size of the gateway process in megabytes. */
  process_rss_mb: number;
  /** Total system RAM in megabytes. */
  system_total_mb: number;
  /** Free system RAM in megabytes. */
  system_free_mb: number;
  /** Approximate token count consumed by the active context window. */
  context_tokens?: number;
}

export interface SessionInfo {
  id: string;
  title: string;
  agent_id: string;
  mode: AgentMode;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Inbound envelopes (server → client)
// ---------------------------------------------------------------------------

export interface AckEnvelope {
  type: "ack";
  protocol_version?: string;
  client_type?: string;
  session_id?: string;
}

export interface SessionsEnvelope {
  type: "sessions";
  sessions: SessionInfo[];
}

export interface SessionCreatedEnvelope {
  type: "session_created";
  session: SessionInfo;
}

export interface TokenEnvelope {
  type: "token";
  text: string;
}

export interface DoneEnvelope {
  type: "done";
  session_id?: string;
}

export interface ErrorEnvelope {
  type: "error";
  message: string;
}

export interface ToolCallEnvelope {
  type: "tool_call";
  name: string;
  arguments: Record<string, unknown>;
  callId: string;
}

/** Server response to a `SkillsRequestEnvelope`. */
export interface SkillsListEnvelope {
  type: "skills_list";
  skills: SkillInfo[];
}

/** Acknowledgment that a skill's enabled state was toggled. */
export interface SkillToggledEnvelope {
  type: "skill_toggled";
  id: string;
  enabled: boolean;
}

/** Server response to a `ModelsRequestEnvelope`. */
export interface ModelsListEnvelope {
  type: "models_list";
  models: ModelInfo[];
  /** ID of the currently active model. */
  active_model?: string;
}

/** Sent by the server after `SwitchModelEnvelope` is processed. */
export interface ModelSwitchedEnvelope {
  type: "model_switched";
  model_id: string;
}

/** Sent by the server after `SwitchSessionEnvelope` is processed. */
export interface SessionSwitchedEnvelope {
  type: "session_switched";
  session: SessionInfo;
}

/** Sent by the server after `RenameSessionEnvelope` is processed. */
export interface SessionRenamedEnvelope {
  type: "session_renamed";
  session_id: string;
  title: string;
}

/** A page of history messages delivered by the server. */
export interface HistoryLoadedEnvelope {
  type: "history_loaded";
  session_id: string;
  page: number;
  total_pages: number;
  messages: ChatMessage[];
}

/** Memory statistics delivered in response to `MemoryComputeEnvelope`. */
export interface MemoryUsageEnvelope {
  type: "memory_usage";
  process_rss_mb: number;
  system_total_mb: number;
  system_free_mb: number;
  context_tokens?: number;
}

/** Confirmation that a session was successfully deleted. */
export interface SessionDeletedEnvelope {
  type: "session_deleted";
  session_id: string;
}

/**
 * Pushed by the server when a rewind is available for a message.
 * Received as an `EventEmitter` event: `client.on("rewindable", ...)`.
 */
export interface RewindableEnvelope {
  type: "rewindable";
  message_id: string;
}

/**
 * Pushed by the server when a rewind operation completes.
 * Received as an `EventEmitter` event: `client.on("rewind_done", ...)`.
 */
export interface RewindDoneEnvelope {
  type: "rewind_done";
  message_id: string;
}

/** Delivered in response to an `ExportSessionEnvelope`. */
export interface SessionExportedEnvelope {
  type: "session_exported";
  session_id: string;
  url?: string;
  data?: string;
  format?: string;
}

/**
 * Pushed periodically by the server with gateway-level metrics.
 * Received as an `EventEmitter` event: `client.on("metrics", ...)`.
 */
export interface MetricsEnvelope {
  type: "metrics";
  requests_total: number;
  tokens_total: number;
  active_sessions: number;
  uptime_s: number;
}

export type InboundEnvelope =
  | AckEnvelope
  | SessionsEnvelope
  | SessionCreatedEnvelope
  | TokenEnvelope
  | DoneEnvelope
  | ErrorEnvelope
  | ToolCallEnvelope
  | SkillsListEnvelope
  | SkillToggledEnvelope
  | ModelsListEnvelope
  | ModelSwitchedEnvelope
  | SessionSwitchedEnvelope
  | SessionRenamedEnvelope
  | HistoryLoadedEnvelope
  | MemoryUsageEnvelope
  | SessionDeletedEnvelope
  | RewindableEnvelope
  | RewindDoneEnvelope
  | SessionExportedEnvelope
  | MetricsEnvelope;

// ---------------------------------------------------------------------------
// Outbound envelopes (client → server)
// ---------------------------------------------------------------------------

export interface ConnectEnvelope {
  type: "connect";
  client_type?: string;
  token?: string;
}

export interface SessionsRequestEnvelope {
  type: "sessions";
}

export interface CreateSessionEnvelope {
  type: "create_session";
  agent_id?: string;
  title?: string;
  mode?: AgentMode;
}

export interface ChatEnvelope {
  type: "chat";
  message: string;
  session_id?: string;
  /** Agent operating mode for this request. */
  mode?: AgentMode;
  /** Channel identifier so the server knows which surface is calling. */
  channel_id?: ChannelId;
  /** Optional media attachments (images, audio, files). */
  media_items?: MediaItem[];
  /**
   * Override the active LLM model for this single request.
   * Takes precedence over any session-level model setting.
   */
  model_name?: string;
}

export interface ToolResultEnvelope {
  type: "tool_result";
  callId: string;
  result?: string;
  error?: string;
}

/** Request the list of installed skills. */
export interface SkillsRequestEnvelope {
  type: "skills";
}

/** Enable or disable a skill by ID. */
export interface SkillToggleEnvelope {
  type: "skill_toggle";
  id: string;
  enabled: boolean;
}

/**
 * Reply to a `confirm_interrupt` stream event.
 * Call `client.sendAnswer(requestId, answers)` which sends this envelope.
 */
export interface HitlAnswerEnvelope {
  type: "hitl_answer";
  request_id: string;
  answers: Record<string, string>;
}

/** Fire-and-forget interrupt: cancel or pause the current agent turn. */
export interface InterruptEnvelope {
  type: "chat.interrupt";
}

/** Request the list of available LLM models. */
export interface ModelsRequestEnvelope {
  type: "models.list";
}

/** Switch the active LLM model for the current session. */
export interface SwitchModelEnvelope {
  type: "models.switch";
  model_id: string;
}

/** Switch the active session to an existing one by ID. */
export interface SwitchSessionEnvelope {
  type: "session.switch";
  session_id: string;
}

/** Rename the active session. */
export interface RenameSessionEnvelope {
  type: "session.rename";
  session_id: string;
  title: string;
}

/** Load a page of message history for a session. */
export interface HistoryGetEnvelope {
  type: "history.get";
  session_id: string;
  page?: number;
}

/** Request current process and system memory statistics. */
export interface MemoryComputeEnvelope {
  type: "memory.compute";
}

/** Delete an existing session by ID. */
export interface DeleteSessionEnvelope {
  type: "session.delete";
  session_id: string;
}

/**
 * Rewind the conversation to a previous message.
 * If `message_id` is omitted, the server rewinds to the last user turn.
 */
export interface RewindEnvelope {
  type: "rewind";
  message_id?: string;
}

/** Request an export of a session's full conversation. */
export interface ExportSessionEnvelope {
  type: "session.export";
  session_id: string;
  /** Desired format: `"markdown"` (default), `"json"`, `"html"`. */
  format?: string;
}

export type OutboundEnvelope =
  | ConnectEnvelope
  | SessionsRequestEnvelope
  | CreateSessionEnvelope
  | ChatEnvelope
  | ToolResultEnvelope
  | SkillsRequestEnvelope
  | SkillToggleEnvelope
  | HitlAnswerEnvelope
  | InterruptEnvelope
  | ModelsRequestEnvelope
  | SwitchModelEnvelope
  | SwitchSessionEnvelope
  | RenameSessionEnvelope
  | HistoryGetEnvelope
  | MemoryComputeEnvelope
  | DeleteSessionEnvelope
  | RewindEnvelope
  | ExportSessionEnvelope;

// ---------------------------------------------------------------------------
// Client configuration
// ---------------------------------------------------------------------------

export interface ReconnectConfig {
  /** Maximum number of reconnect attempts before giving up (default: Infinity). */
  maxAttempts?: number;
  /** Delay before the first reconnect attempt in ms (default: 1 000). */
  initialDelayMs?: number;
  /** Maximum delay between attempts in ms (default: 30 000). */
  maxDelayMs?: number;
  /** Multiplicative factor applied to the delay each attempt (default: 2). */
  factor?: number;
}

export interface ClientConfig {
  /** WebSocket URL, e.g. `ws://localhost:19000/v1/ws`. */
  url: string;
  /** Bearer token sent in the `connect` envelope (optional in dev mode). */
  authToken?: string;
  /**
   * Reconnect behaviour.
   * - `false`  — disable auto-reconnect.
   * - `ReconnectConfig` — configure exponential back-off.
   * - omitted  — use defaults (1 → 2 → 5 → 10 → 30 s, unlimited attempts).
   */
  reconnect?: false | ReconnectConfig;
  /**
   * Default agent operating mode sent with every chat/stream request.
   * Can be overridden per-call via `streamEvents()` options.
   */
  mode?: AgentMode;
  /**
   * Channel identifier — tells the server which surface is connecting.
   * Can be overridden per-call via `streamEvents()` options.
   */
  channelId?: ChannelId;
  /** Called for each streaming token received from the server. */
  onToken?: (text: string) => void;
  /** Called when the agent finishes a response. */
  onDone?: (sessionId?: string) => void;
  /** Called when the server reports a protocol-level error. */
  onError?: (message: string) => void;
  /**
   * Called for `tool_call` envelopes from the server.
   * Return the result string or throw to send an error back.
   * If omitted, all tool calls are automatically rejected.
   */
  onToolCall?: (call: ToolCallEnvelope) => Promise<string>;
  /**
   * Enable the correlated-RPC wire format used by jiuwenswarm-ide.
   *
   * When `true` every outbound message is wrapped in:
   * ```json
   * { "id": "<uuid>", "type": "req", "method": "<rpc-method>",
   *   "params": { ...fields }, "channel_id": "ide", "timestamp": 1234.5 }
   * ```
   * and inbound `{ "type": "res", "id": "...", "data": {...} }` envelopes
   * are unwrapped before being dispatched.
   *
   * Use this option when the SDK is replacing the transport layer of an IDE
   * plugin that talks to the gateway via its RPC protocol.
   *
   * Default: `false` (flat envelope protocol).
   */
  rpcMode?: boolean;
  /**
   * Channel identifier inserted into every outbound RPC envelope.
   * Only used when `rpcMode` is `true`.
   * Default: `"ide"`.
   */
  rpcChannelId?: string;
}

/** Options for `client.streamEvents()` and `client.send()`. */
export interface StreamEventsOptions {
  /**
   * Agent operating mode for this request.
   * Overrides `ClientConfig.mode` for this call only.
   */
  mode?: AgentMode;
  /**
   * Channel identifier for this call.
   * Overrides `ClientConfig.channelId` for this call only.
   */
  channelId?: ChannelId;
  /**
   * Optional context prepended to the prompt with a `\n\n---\n\n` separator,
   * mirroring Python SDK's `context_prefix` parameter.
   */
  contextPrefix?: string;
  /** Explicit session ID to use (defaults to the active session). */
  sessionId?: string;
  /**
   * Optional media attachments sent alongside the message.
   * Mirrors Python SDK's `ImageInput` / `AudioInput` support.
   *
   * @example
   * ```typescript
   * import { readFileSync } from "fs";
   * await client.send("Describe this image", {
   *   mediaItems: [{
   *     mime_type: "image/png",
   *     data: readFileSync("screenshot.png").toString("base64"),
   *     name: "screenshot.png",
   *   }],
   * });
   * ```
   */
  mediaItems?: MediaItem[];
  /**
   * Override the active LLM model for this single request.
   * Mirrors the IDE's per-message `model_name` param in `chat.send`.
   *
   * @example
   * ```typescript
   * for await (const event of client.streamEvents("Summarise this", {
   *   modelName: "gpt-4o",
   * })) { ... }
   * ```
   */
  modelName?: string;
}

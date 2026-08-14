/**
 * Protocol types for the JiuwenSwarm WebSocket gateway.
 *
 * All messages exchanged over the WebSocket are JSON objects with a "type"
 * discriminator field (InboundEnvelope / OutboundEnvelope unions below).
 */

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

export type AgentMode = "default" | "focused" | "creative";

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

export type InboundEnvelope =
  | AckEnvelope
  | SessionsEnvelope
  | SessionCreatedEnvelope
  | TokenEnvelope
  | DoneEnvelope
  | ErrorEnvelope
  | ToolCallEnvelope;

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
}

export interface ToolResultEnvelope {
  type: "tool_result";
  callId: string;
  result?: string;
  error?: string;
}

export type OutboundEnvelope =
  | ConnectEnvelope
  | SessionsRequestEnvelope
  | CreateSessionEnvelope
  | ChatEnvelope
  | ToolResultEnvelope;

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
}

/**
 * @jiuwenswarm/sdk — TypeScript / JavaScript SDK for the JiuwenSwarm gateway.
 *
 * @example
 * ```typescript
 * import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";
 *
 * const client = new JiuwenSwarmClient({
 *   url: "ws://localhost:19000/v1/ws",
 *   onToken: (text) => process.stdout.write(text),
 * });
 * await client.connect();
 * const session = await client.sessions.create("Demo");
 * client.sessions.setActive(session.id);
 * await client.send("Hello!");
 * client.disconnect();
 * ```
 */

// Core client
export { JiuwenSwarmClient } from "./client/JiuwenSwarmClient";

// Session management
export { SessionManager } from "./session/SessionManager";

// Protocol types
export type {
  ClientConfig,
  ReconnectConfig,
  AgentMode,
  SessionInfo,
  ChatMessage,
  InboundEnvelope,
  OutboundEnvelope,
  AckEnvelope,
  SessionsEnvelope,
  SessionCreatedEnvelope,
  TokenEnvelope,
  DoneEnvelope,
  ErrorEnvelope,
  ToolCallEnvelope,
  ConnectEnvelope,
  SessionsRequestEnvelope,
  CreateSessionEnvelope,
  ChatEnvelope,
  ToolResultEnvelope,
} from "./protocol/types";

// Protocol constants and utilities
export { MSG } from "./protocol/constants";
export type { MsgType } from "./protocol/constants";
export { ProtocolError, ConnectionError, parseEnvelope } from "./protocol/validate";

// EventEmitter (for advanced use)
export { EventEmitter } from "./events/EventEmitter";

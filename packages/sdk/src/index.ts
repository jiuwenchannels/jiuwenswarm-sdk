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
 *
 * @example Typed stream events
 * ```typescript
 * import { JiuwenSwarmClient, AgentModeConstants } from "@jiuwenswarm/sdk";
 *
 * const client = new JiuwenSwarmClient({ url: "ws://localhost:19000/v1/ws" });
 * await client.connect();
 *
 * for await (const event of client.streamEvents("Explain closures", {
 *   mode: AgentModeConstants.CODE,
 * })) {
 *   switch (event.kind) {
 *     case "delta":   process.stdout.write(event.text); break;
 *     case "done":    console.log("\n[done]", event.sessionId); break;
 *     case "error":   console.error("[error]", event.message); break;
 *   }
 * }
 * ```
 */

// Core client
export { JiuwenSwarmClient } from "./client/JiuwenSwarmClient";

// Session management
export { SessionManager } from "./session/SessionManager";

// Swarm state (Phase 12)
export { SwarmStateManager } from "./swarm/SwarmStateManager";
export type {
  AgentState,
  TaskState,
  HandoffRecord,
  SwarmSnapshot,
} from "./swarm/SwarmStateManager";

// Protocol types
export type {
  ClientConfig,
  ReconnectConfig,
  StreamEventsOptions,
  AgentMode,
  ChannelId,
  SessionInfo,
  ChatMessage,
  SkillInfo,
  InboundEnvelope,
  OutboundEnvelope,
  AckEnvelope,
  SessionsEnvelope,
  SessionCreatedEnvelope,
  TokenEnvelope,
  DoneEnvelope,
  ErrorEnvelope,
  ToolCallEnvelope,
  SkillsListEnvelope,
  SkillToggledEnvelope,
  ConnectEnvelope,
  SessionsRequestEnvelope,
  CreateSessionEnvelope,
  ChatEnvelope,
  ToolResultEnvelope,
  SkillsRequestEnvelope,
  SkillToggleEnvelope,
  HitlAnswerEnvelope,
  InterruptEnvelope,
} from "./protocol/types";

// AgentMode + ChannelId named constants
export { AgentModeConstants, ChannelIdConstants } from "./protocol/types";

// StreamEvent types (Phase 11 + Phase 12)
export type {
  StreamEvent,
  DeltaEvent,
  ReasoningEvent,
  StatusEvent,
  ToolCallEvent,
  ToolResultEvent,
  TeamEvent,
  TeamMemberSpawnedEvent,
  TeamMemberStatusChangedEvent,
  TeamTaskCreatedEvent,
  TeamTaskCompletedEvent,
  TeamHandoffEvent,
  UsageEvent,
  ConfirmInterruptEvent,
  DoneEvent,
  ErrorEvent,
} from "./protocol/events";

// parseStreamEvent utility
export { parseStreamEvent } from "./protocol/events";

// Protocol constants and utilities
export { MSG } from "./protocol/constants";
export type { MsgType } from "./protocol/constants";
export { ProtocolError, ConnectionError, parseEnvelope } from "./protocol/validate";

// EventEmitter (for advanced use)
export { EventEmitter } from "./events/EventEmitter";

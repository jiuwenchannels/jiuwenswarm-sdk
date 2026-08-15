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
  // Configuration
  ClientConfig,
  ReconnectConfig,
  StreamEventsOptions,
  // Domain types
  AgentMode,
  ChannelId,
  SessionInfo,
  ChatMessage,
  SkillInfo,
  ModelInfo,
  MediaItem,
  HistoryPage,
  MemoryStats,
  MetricsInfo,
  SessionExport,
  // Envelope unions
  InboundEnvelope,
  OutboundEnvelope,
  // Inbound — core
  AckEnvelope,
  SessionsEnvelope,
  SessionCreatedEnvelope,
  TokenEnvelope,
  DoneEnvelope,
  ErrorEnvelope,
  ToolCallEnvelope,
  // Inbound — skills
  SkillsListEnvelope,
  SkillToggledEnvelope,
  // Inbound — models
  ModelsListEnvelope,
  ModelSwitchedEnvelope,
  // Inbound — session lifecycle
  SessionSwitchedEnvelope,
  SessionRenamedEnvelope,
  SessionDeletedEnvelope,
  // Inbound — history and memory
  HistoryLoadedEnvelope,
  MemoryUsageEnvelope,
  // Inbound — rewind (server push)
  RewindableEnvelope,
  RewindDoneEnvelope,
  // Inbound — export result
  SessionExportedEnvelope,
  // Inbound — metrics (periodic server push)
  MetricsEnvelope,
  // Outbound — core
  ConnectEnvelope,
  SessionsRequestEnvelope,
  CreateSessionEnvelope,
  ChatEnvelope,
  ToolResultEnvelope,
  // Outbound — skills
  SkillsRequestEnvelope,
  SkillToggleEnvelope,
  // Outbound — HITL
  HitlAnswerEnvelope,
  InterruptEnvelope,
  // Outbound — models
  ModelsRequestEnvelope,
  SwitchModelEnvelope,
  // Outbound — session lifecycle
  SwitchSessionEnvelope,
  RenameSessionEnvelope,
  DeleteSessionEnvelope,
  // Outbound — history and memory
  HistoryGetEnvelope,
  MemoryComputeEnvelope,
  // Outbound — rewind and export
  RewindEnvelope,
  ExportSessionEnvelope,
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

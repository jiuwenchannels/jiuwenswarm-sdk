/**
 * Typed stream events for the JiuwenSwarm gateway.
 *
 * `StreamEvent` is a discriminated union covering every event type that can be
 * emitted during a `client.streamEvents()` session.  Use the `kind` field as
 * the discriminator in switch / if-else chains:
 *
 * ```typescript
 * for await (const event of client.streamEvents("Explain closures")) {
 *   switch (event.kind) {
 *     case "delta":     process.stdout.write(event.text); break;
 *     case "reasoning": console.log("[think]", event.text); break;
 *     case "tool_call": console.log("[tool]", event.name, event.arguments); break;
 *     case "done":      console.log("\n[done]", event.sessionId); break;
 *     case "error":     console.error("[error]", event.message); break;
 *   }
 * }
 * ```
 *
 * `parseStreamEvent()` maps a raw gateway envelope object to the appropriate
 * `StreamEvent` subtype.  It returns `null` for envelopes that are not part of
 * the stream event vocabulary (e.g. ack, sessions, session_created).
 */

// ---------------------------------------------------------------------------
// StreamEvent subtypes
// ---------------------------------------------------------------------------

/** A single text token chunk from the model. */
export interface DeltaEvent {
  kind: "delta";
  /** Incremental text token. */
  text: string;
}

/**
 * An internal reasoning step from the model (chain-of-thought).
 * Only emitted when the model supports visible reasoning (e.g. o1, R1 style).
 */
export interface ReasoningEvent {
  kind: "reasoning";
  /** Incremental reasoning text. */
  text: string;
}

/** A status update describing what the agent is currently doing. */
export interface StatusEvent {
  kind: "status";
  /** Human-readable status message, e.g. "Searching the web…". */
  status: string;
  /** Optional agent identifier that produced this status. */
  agentId?: string;
}

/** The agent has invoked a tool. */
export interface ToolCallEvent {
  kind: "tool_call";
  /** Tool name. */
  name: string;
  /** Arguments passed to the tool. */
  arguments: Record<string, unknown>;
  /** Opaque call identifier — pass to `ToolResultEvent.callId`. */
  callId: string;
}

/** A tool execution has completed and the result is available. */
export interface ToolResultEvent {
  kind: "tool_result";
  /** Matches the originating `ToolCallEvent.callId`. */
  callId: string;
  /** Result returned by the tool, if successful. */
  result?: string;
  /** Error message if the tool execution failed. */
  error?: string;
}

// ---------------------------------------------------------------------------
// Team events
// ---------------------------------------------------------------------------

/** A new agent was spawned into the team. */
export interface TeamMemberSpawnedEvent {
  kind: "team.member.spawned";
  /** Identifier of the newly spawned agent. */
  agentId: string;
  /** Human-readable role label (e.g. "researcher", "writer"). */
  role?: string;
}

/** An existing agent changed its activity state. */
export interface TeamMemberStatusChangedEvent {
  kind: "team.member.status_changed";
  agentId: string;
  /** New status string (e.g. "idle", "working", "done"). */
  status: string;
}

/** A task was created and assigned to an agent. */
export interface TeamTaskCreatedEvent {
  kind: "team.task.created";
  taskId: string;
  /** Agent that was assigned the task. */
  assignedTo: string;
  /** Short description of the task. */
  description: string;
}

/** An agent completed its assigned task. */
export interface TeamTaskCompletedEvent {
  kind: "team.task.completed";
  taskId: string;
  agentId: string;
}

/** Control or result was handed off between agents. */
export interface TeamHandoffEvent {
  kind: "team.handoff";
  fromAgentId: string;
  toAgentId: string;
  /** Optional short summary of what was handed off. */
  summary?: string;
}

/** Union of all team-coordination event subtypes. */
export type TeamEvent =
  | TeamMemberSpawnedEvent
  | TeamMemberStatusChangedEvent
  | TeamTaskCreatedEvent
  | TeamTaskCompletedEvent
  | TeamHandoffEvent;

// ---------------------------------------------------------------------------
// Usage + control events
// ---------------------------------------------------------------------------

/** Token usage and cost summary for the completed turn. */
export interface UsageEvent {
  kind: "usage";
  /** Number of prompt/input tokens consumed. */
  inputTokens: number;
  /** Number of completion/output tokens generated. */
  outputTokens: number;
  /** Estimated monetary cost in USD, if reported by the server. */
  costUsd?: number;
}

/**
 * The server has paused and requires a human answer before continuing.
 * Call `client.sendAnswer(requestId, answers)` to resume.
 */
export interface ConfirmInterruptEvent {
  kind: "confirm_interrupt";
  /** Opaque identifier — pass to `client.sendAnswer()`. */
  requestId: string;
  /** The question(s) the agent needs answered. */
  question: string;
}

/** The agent finished producing its response. */
export interface DoneEvent {
  kind: "done";
  /** Session that this response belongs to. */
  sessionId?: string;
}

/** A protocol-level or agent-level error occurred. */
export interface ErrorEvent {
  kind: "error";
  /** Human-readable error description. */
  message: string;
}

// ---------------------------------------------------------------------------
// StreamEvent union
// ---------------------------------------------------------------------------

/**
 * Discriminated union of every event type that can be emitted during
 * `client.streamEvents()`.
 *
 * Use `event.kind` as the discriminator.
 */
export type StreamEvent =
  | DeltaEvent
  | ReasoningEvent
  | StatusEvent
  | ToolCallEvent
  | ToolResultEvent
  | TeamMemberSpawnedEvent
  | TeamMemberStatusChangedEvent
  | TeamTaskCreatedEvent
  | TeamTaskCompletedEvent
  | TeamHandoffEvent
  | UsageEvent
  | ConfirmInterruptEvent
  | DoneEvent
  | ErrorEvent;

// ---------------------------------------------------------------------------
// parseStreamEvent
// ---------------------------------------------------------------------------

/**
 * Map a raw gateway envelope object to the appropriate `StreamEvent`.
 *
 * Handles both the legacy gateway format (envelope `type` field) and the E2A
 * format used by newer JiuwenSwarm server releases (`response_kind` field).
 *
 * Returns `null` for envelopes that are not part of the stream vocabulary
 * (e.g. `ack`, `sessions`, `session_created`).
 *
 * @example
 * ```typescript
 * ws.onmessage = (msg) => {
 *   const env = JSON.parse(msg.data);
 *   const event = parseStreamEvent(env);
 *   if (event) handleStreamEvent(event);
 * };
 * ```
 */
export function parseStreamEvent(
  envelope: Record<string, unknown>,
): StreamEvent | null {
  // E2A format: use response_kind when present.
  const rawKind =
    typeof envelope["response_kind"] === "string"
      ? envelope["response_kind"]
      : typeof envelope["type"] === "string"
        ? envelope["type"]
        : null;

  if (!rawKind) return null;

  switch (rawKind) {
    // Legacy token → delta
    case "token":
    case "e2a.chunk":
      return {
        kind: "delta",
        text: typeof envelope["text"] === "string" ? envelope["text"] : "",
      };

    case "reasoning":
      return {
        kind: "reasoning",
        text: typeof envelope["text"] === "string" ? envelope["text"] : "",
      };

    case "status":
      return {
        kind: "status",
        status:
          typeof envelope["status"] === "string" ? envelope["status"] : "",
        agentId:
          typeof envelope["agent_id"] === "string"
            ? envelope["agent_id"]
            : undefined,
      };

    case "tool_call":
      return {
        kind: "tool_call",
        name: typeof envelope["name"] === "string" ? envelope["name"] : "",
        arguments:
          typeof envelope["arguments"] === "object" &&
          envelope["arguments"] !== null
            ? (envelope["arguments"] as Record<string, unknown>)
            : {},
        callId:
          typeof envelope["callId"] === "string" ? envelope["callId"] : "",
      };

    case "tool_result_server":
      return {
        kind: "tool_result",
        callId:
          typeof envelope["callId"] === "string" ? envelope["callId"] : "",
        result:
          typeof envelope["result"] === "string"
            ? envelope["result"]
            : undefined,
        error:
          typeof envelope["error"] === "string"
            ? envelope["error"]
            : undefined,
      };

    // Team events
    case "team.member.spawned":
      return {
        kind: "team.member.spawned",
        agentId:
          typeof envelope["agent_id"] === "string"
            ? envelope["agent_id"]
            : "",
        role:
          typeof envelope["role"] === "string" ? envelope["role"] : undefined,
      };

    case "team.member.status_changed":
      return {
        kind: "team.member.status_changed",
        agentId:
          typeof envelope["agent_id"] === "string"
            ? envelope["agent_id"]
            : "",
        status:
          typeof envelope["status"] === "string" ? envelope["status"] : "",
      };

    case "team.task.created":
      return {
        kind: "team.task.created",
        taskId:
          typeof envelope["task_id"] === "string" ? envelope["task_id"] : "",
        assignedTo:
          typeof envelope["assigned_to"] === "string"
            ? envelope["assigned_to"]
            : "",
        description:
          typeof envelope["description"] === "string"
            ? envelope["description"]
            : "",
      };

    case "team.task.completed":
      return {
        kind: "team.task.completed",
        taskId:
          typeof envelope["task_id"] === "string" ? envelope["task_id"] : "",
        agentId:
          typeof envelope["agent_id"] === "string"
            ? envelope["agent_id"]
            : "",
      };

    case "team.handoff":
      return {
        kind: "team.handoff",
        fromAgentId:
          typeof envelope["from_agent_id"] === "string"
            ? envelope["from_agent_id"]
            : "",
        toAgentId:
          typeof envelope["to_agent_id"] === "string"
            ? envelope["to_agent_id"]
            : "",
        summary:
          typeof envelope["summary"] === "string"
            ? envelope["summary"]
            : undefined,
      };

    case "usage":
      return {
        kind: "usage",
        inputTokens:
          typeof envelope["input_tokens"] === "number"
            ? envelope["input_tokens"]
            : 0,
        outputTokens:
          typeof envelope["output_tokens"] === "number"
            ? envelope["output_tokens"]
            : 0,
        costUsd:
          typeof envelope["cost_usd"] === "number"
            ? envelope["cost_usd"]
            : undefined,
      };

    case "confirm_interrupt":
      return {
        kind: "confirm_interrupt",
        requestId:
          typeof envelope["request_id"] === "string"
            ? envelope["request_id"]
            : "",
        question:
          typeof envelope["question"] === "string"
            ? envelope["question"]
            : "",
      };

    case "done":
    case "e2a.complete":
      return {
        kind: "done",
        sessionId:
          typeof envelope["session_id"] === "string"
            ? envelope["session_id"]
            : undefined,
      };

    case "error":
    case "e2a.error":
      return {
        kind: "error",
        message:
          typeof envelope["message"] === "string" ? envelope["message"] : "",
      };

    default:
      return null;
  }
}

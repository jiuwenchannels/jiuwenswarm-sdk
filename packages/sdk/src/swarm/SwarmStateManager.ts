/**
 * SwarmStateManager — live view of a multi-agent team's state.
 *
 * Feed a `streamEvents()` generator into `SwarmStateManager.feed()` and it
 * tracks agent statuses, tasks, and handoffs automatically.  Use `.snapshot()`
 * at any point to read the current state.
 *
 * ```typescript
 * import { JiuwenSwarmClient, SwarmStateManager } from "@jiuwenswarm/sdk";
 *
 * const client = new JiuwenSwarmClient({ url: "ws://localhost:19000/v1/ws" });
 * await client.connect();
 *
 * const swarm = new SwarmStateManager();
 *
 * for await (const event of client.streamEvents("Research climate change", {
 *   mode: "team",
 * })) {
 *   swarm.feed(event);
 *
 *   if (event.kind === "delta") process.stdout.write(event.text);
 * }
 *
 * console.log(swarm.snapshot());
 * ```
 */
import type {
  StreamEvent,
  TeamMemberSpawnedEvent,
  TeamMemberStatusChangedEvent,
  TeamTaskCreatedEvent,
  TeamTaskCompletedEvent,
  TeamHandoffEvent,
} from "../protocol/events";

// ---------------------------------------------------------------------------
// State types
// ---------------------------------------------------------------------------

/** Current state of a single agent in the team. */
export interface AgentState {
  /** Unique agent identifier. */
  id: string;
  /** Human-readable role label (e.g. "researcher", "writer"). */
  role?: string;
  /** Last reported status string (e.g. "idle", "working", "done"). */
  status: string;
  /** Timestamp of the last status update (ms since epoch). */
  updatedAt: number;
}

/** State of a task tracked by the swarm. */
export interface TaskState {
  /** Unique task identifier. */
  id: string;
  /** Agent the task is assigned to. */
  assignedTo: string;
  /** Short description of the task. */
  description: string;
  /** Whether the task has completed. */
  completed: boolean;
  /** Timestamp when the task was created (ms since epoch). */
  createdAt: number;
  /** Timestamp when the task was completed, or undefined if still active. */
  completedAt?: number;
}

/** A handoff record between two agents. */
export interface HandoffRecord {
  fromAgentId: string;
  toAgentId: string;
  summary?: string;
  /** Timestamp of the handoff (ms since epoch). */
  at: number;
}

/** Full snapshot of the current swarm state. */
export interface SwarmSnapshot {
  /** All known agents, keyed by agent ID. */
  agents: Map<string, AgentState>;
  /** All known tasks, keyed by task ID. */
  tasks: Map<string, TaskState>;
  /** Ordered log of all handoffs that occurred. */
  handoffs: HandoffRecord[];
}

// ---------------------------------------------------------------------------
// SwarmStateManager
// ---------------------------------------------------------------------------

/**
 * Tracks the live state of a multi-agent team by consuming `StreamEvent`
 * objects from `client.streamEvents()`.
 *
 * The manager is intentionally state-only: it does not open any WebSocket
 * connection itself.  Connect it to a stream via `feed()`.
 */
export class SwarmStateManager {
  private readonly _agents = new Map<string, AgentState>();
  private readonly _tasks = new Map<string, TaskState>();
  private readonly _handoffs: HandoffRecord[] = [];

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Process a single `StreamEvent`.  Only team-related event kinds are handled;
   * all other events are silently ignored.
   *
   * Typically called inside a `for await` loop:
   * ```typescript
   * for await (const event of client.streamEvents(...)) {
   *   swarm.feed(event);
   *   // handle delta / done etc. here
   * }
   * ```
   */
  feed(event: StreamEvent): void {
    switch (event.kind) {
      case "team.member.spawned":
        this._onMemberSpawned(event);
        break;
      case "team.member.status_changed":
        this._onMemberStatusChanged(event);
        break;
      case "team.task.created":
        this._onTaskCreated(event);
        break;
      case "team.task.completed":
        this._onTaskCompleted(event);
        break;
      case "team.handoff":
        this._onHandoff(event);
        break;
      // All other events (delta, done, tool_call, etc.) are ignored.
    }
  }

  /**
   * Return the current state snapshot.
   *
   * The returned `Map` instances are copies — mutating them does not affect the
   * manager's internal state.
   */
  snapshot(): SwarmSnapshot {
    return {
      agents: new Map(this._agents),
      tasks: new Map(this._tasks),
      handoffs: [...this._handoffs],
    };
  }

  /**
   * Return the state of a single agent by ID, or `undefined` if not found.
   */
  agent(id: string): AgentState | undefined {
    return this._agents.get(id);
  }

  /**
   * Return the state of a single task by ID, or `undefined` if not found.
   */
  task(id: string): TaskState | undefined {
    return this._tasks.get(id);
  }

  /**
   * Return all agents currently in "working" status.
   */
  activeAgents(): AgentState[] {
    return [...this._agents.values()].filter((a) => a.status === "working");
  }

  /**
   * Return all incomplete tasks.
   */
  pendingTasks(): TaskState[] {
    return [...this._tasks.values()].filter((t) => !t.completed);
  }

  /**
   * Reset all tracked state.  Call between requests if reusing the manager.
   */
  reset(): void {
    this._agents.clear();
    this._tasks.clear();
    this._handoffs.length = 0;
  }

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------

  private _onMemberSpawned(event: TeamMemberSpawnedEvent): void {
    this._agents.set(event.agentId, {
      id: event.agentId,
      role: event.role,
      status: "idle",
      updatedAt: Date.now(),
    });
  }

  private _onMemberStatusChanged(event: TeamMemberStatusChangedEvent): void {
    const existing = this._agents.get(event.agentId);
    if (existing) {
      existing.status = event.status;
      existing.updatedAt = Date.now();
    } else {
      // Received a status change before the spawn event — create the entry.
      this._agents.set(event.agentId, {
        id: event.agentId,
        status: event.status,
        updatedAt: Date.now(),
      });
    }
  }

  private _onTaskCreated(event: TeamTaskCreatedEvent): void {
    this._tasks.set(event.taskId, {
      id: event.taskId,
      assignedTo: event.assignedTo,
      description: event.description,
      completed: false,
      createdAt: Date.now(),
    });
  }

  private _onTaskCompleted(event: TeamTaskCompletedEvent): void {
    const existing = this._tasks.get(event.taskId);
    if (existing) {
      existing.completed = true;
      existing.completedAt = Date.now();
    }
    // Update agent status to idle when it finishes a task.
    const agent = this._agents.get(event.agentId);
    if (agent && agent.status === "working") {
      agent.status = "idle";
      agent.updatedAt = Date.now();
    }
  }

  private _onHandoff(event: TeamHandoffEvent): void {
    this._handoffs.push({
      fromAgentId: event.fromAgentId,
      toAgentId: event.toAgentId,
      summary: event.summary,
      at: Date.now(),
    });
  }
}

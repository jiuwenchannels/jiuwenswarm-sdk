/**
 * SessionManager — tracks and manages sessions over the WebSocket gateway.
 *
 * Accessed via `client.sessions`:
 * ```typescript
 * const session = await client.sessions.create("My session");
 * client.sessions.setActive(session.id);
 * const all = await client.sessions.list();
 * await client.sessions.refresh();
 * const current = client.sessions.active;
 * ```
 */
import type { AgentMode, SessionInfo } from "../protocol/types";

/**
 * The subset of JiuwenSwarmClient that SessionManager needs.
 * Declared here so the two files do not create a circular import.
 */
export interface SessionDelegate {
  /** Send a `sessions` envelope and resolve with the server's list. */
  _listSessions(): Promise<SessionInfo[]>;
  /** Send a `create_session` envelope and resolve with the new session. */
  _createSession(params: {
    title?: string;
    agent_id?: string;
    mode?: AgentMode;
  }): Promise<SessionInfo>;
  /** Send a `session.delete` envelope and resolve with the deleted session ID. */
  _deleteSession(sessionId: string): Promise<string>;
}

export class SessionManager {
  private _sessions: SessionInfo[] = [];
  private _activeId: string | null = null;

  constructor(private readonly _delegate: SessionDelegate) {}

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Fetch the current list of sessions from the server.
   * Also updates the internal cache.
   */
  async list(): Promise<SessionInfo[]> {
    this._sessions = await this._delegate._listSessions();
    return this._sessions;
  }

  /**
   * Create a new session on the server.
   *
   * @param title     Human-readable session title.
   * @param agentId   ID of the agent to associate (optional).
   * @param mode      Agent mode (default: `"default"`).
   */
  async create(
    title: string,
    agentId?: string,
    mode?: AgentMode,
  ): Promise<SessionInfo> {
    const session = await this._delegate._createSession({
      title,
      agent_id: agentId,
      mode,
    });
    this._sessions = [session, ...this._sessions];
    return session;
  }

  /**
   * Delete a session on the server and remove it from the local cache.
   * If the deleted session was active, the active pointer is cleared.
   *
   * ```typescript
   * await client.sessions.delete("sess_abc123");
   * ```
   *
   * @param sessionId  ID of the session to delete.
   */
  async delete(sessionId: string): Promise<void> {
    await this._delegate._deleteSession(sessionId);
    this._sessions = this._sessions.filter((s) => s.id !== sessionId);
    if (this._activeId === sessionId) this._activeId = null;
  }

  /**
   * Mark a session as the active one.
   * The session ID is automatically included in subsequent `chat` envelopes.
   */
  setActive(id: string): void {
    this._activeId = id;
  }

  /**
   * Re-fetch the session list from the server and update the internal cache.
   * The active session ID is preserved.
   */
  async refresh(): Promise<void> {
    this._sessions = await this._delegate._listSessions();
  }

  /** The currently active session, or `null` if none is set. */
  get active(): SessionInfo | null {
    if (this._activeId === null) return null;
    return this._sessions.find((s) => s.id === this._activeId) ?? null;
  }

  /** The active session ID (for internal use by JiuwenSwarmClient). */
  get activeId(): string | null {
    return this._activeId;
  }

  /** Replace the cached session list (called by JiuwenSwarmClient on push). */
  _updateCache(sessions: SessionInfo[]): void {
    this._sessions = sessions;
  }
}

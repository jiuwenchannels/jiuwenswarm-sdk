import { describe, it, expect, vi } from "vitest";
import { SessionManager } from "../src/session/SessionManager";
import type { SessionInfo, AgentMode } from "../src/protocol/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let _idCounter = 0;

function makeSession(overrides: Partial<SessionInfo> = {}): SessionInfo {
  _idCounter++;
  return {
    id: `session-${_idCounter}`,
    title: `Session ${_idCounter}`,
    agent_id: `agent-${_idCounter}`,
    mode: "default" as AgentMode,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

const makeDelegate = () => ({
  _listSessions: vi.fn<[], Promise<SessionInfo[]>>(),
  _createSession: vi.fn<[object], Promise<SessionInfo>>(),
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SessionManager", () => {
  it("list() calls _listSessions and returns its result", async () => {
    const delegate = makeDelegate();
    const sessions = [makeSession(), makeSession()];
    delegate._listSessions.mockResolvedValue(sessions);

    const manager = new SessionManager(delegate);
    const result = await manager.list();

    expect(delegate._listSessions).toHaveBeenCalledOnce();
    expect(result).toEqual(sessions);
  });

  it("list() updates the internal cache so active returns the right session", async () => {
    const delegate = makeDelegate();
    const s1 = makeSession({ id: "s1" });
    const s2 = makeSession({ id: "s2" });
    delegate._listSessions.mockResolvedValue([s1, s2]);

    const manager = new SessionManager(delegate);
    manager.setActive("s1");
    // active is null before list() because cache is empty
    expect(manager.active).toBeNull();

    await manager.list();
    expect(manager.active).toEqual(s1);
  });

  it("create(title) calls _createSession with correct params and returns the new session", async () => {
    const delegate = makeDelegate();
    const newSession = makeSession({ title: "My New Session" });
    delegate._createSession.mockResolvedValue(newSession);

    const manager = new SessionManager(delegate);
    const result = await manager.create("My New Session");

    expect(delegate._createSession).toHaveBeenCalledOnce();
    expect(delegate._createSession).toHaveBeenCalledWith({
      title: "My New Session",
      agent_id: undefined,
      mode: undefined,
    });
    expect(result).toEqual(newSession);
  });

  it("create(title, agentId, mode) passes all params through to _createSession", async () => {
    const delegate = makeDelegate();
    const newSession = makeSession({ agent_id: "agent-x", mode: "focused" });
    delegate._createSession.mockResolvedValue(newSession);

    const manager = new SessionManager(delegate);
    await manager.create("Focused Session", "agent-x", "focused");

    expect(delegate._createSession).toHaveBeenCalledWith({
      title: "Focused Session",
      agent_id: "agent-x",
      mode: "focused",
    });
  });

  it("create() prepends the new session to the cache", async () => {
    const delegate = makeDelegate();
    const existing = [makeSession({ id: "old-1" }), makeSession({ id: "old-2" })];
    delegate._listSessions.mockResolvedValue(existing);
    const freshSession = makeSession({ id: "new-1" });
    delegate._createSession.mockResolvedValue(freshSession);

    const manager = new SessionManager(delegate);
    await manager.list(); // populate cache with existing

    await manager.create("New");
    // active should be findable from cache; new session is first
    manager.setActive("new-1");
    expect(manager.active).toEqual(freshSession);
  });

  it("setActive(id) sets activeId; active getter returns the matching cached session", async () => {
    const delegate = makeDelegate();
    const s = makeSession({ id: "target" });
    delegate._listSessions.mockResolvedValue([s]);

    const manager = new SessionManager(delegate);
    await manager.list();
    manager.setActive("target");

    expect(manager.active).toEqual(s);
  });

  it("active returns null if no active session is set", async () => {
    const delegate = makeDelegate();
    delegate._listSessions.mockResolvedValue([makeSession()]);

    const manager = new SessionManager(delegate);
    await manager.list();
    expect(manager.active).toBeNull();
  });

  it("active returns null if set ID is not found in cache", async () => {
    const delegate = makeDelegate();
    delegate._listSessions.mockResolvedValue([makeSession({ id: "a" })]);

    const manager = new SessionManager(delegate);
    await manager.list();
    manager.setActive("non-existent-id");

    expect(manager.active).toBeNull();
  });

  it("refresh() re-fetches and updates cache; preserves activeId", async () => {
    const delegate = makeDelegate();
    const s1 = makeSession({ id: "s1", title: "Old Title" });
    delegate._listSessions.mockResolvedValueOnce([s1]);

    const manager = new SessionManager(delegate);
    await manager.list();
    manager.setActive("s1");

    // Server returns an updated session list
    const s1Updated = { ...s1, title: "Updated Title" };
    delegate._listSessions.mockResolvedValueOnce([s1Updated]);
    await manager.refresh();

    expect(delegate._listSessions).toHaveBeenCalledTimes(2);
    // active still resolves to the same ID but with updated data
    expect(manager.active).toEqual(s1Updated);
  });

  it("refresh() does not clear activeId", async () => {
    const delegate = makeDelegate();
    const s = makeSession({ id: "keep-me" });
    delegate._listSessions.mockResolvedValue([s]);

    const manager = new SessionManager(delegate);
    await manager.list();
    manager.setActive("keep-me");
    await manager.refresh();

    expect(manager.active).toEqual(s);
  });

  it("_updateCache() replaces the cache; active reflects the updated list", () => {
    const delegate = makeDelegate();
    const manager = new SessionManager(delegate);

    const s = makeSession({ id: "pushed" });
    manager.setActive("pushed");
    expect(manager.active).toBeNull(); // not in cache yet

    manager._updateCache([s]);
    expect(manager.active).toEqual(s);
  });

  it("_updateCache() with empty array makes active return null even if activeId is set", () => {
    const delegate = makeDelegate();
    const manager = new SessionManager(delegate);

    manager.setActive("some-id");
    manager._updateCache([]);
    expect(manager.active).toBeNull();
  });
});

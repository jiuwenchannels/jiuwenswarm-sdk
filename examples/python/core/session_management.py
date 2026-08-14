"""session_management.py — session CRUD and conversation continuity.

Shows:
  - Creating a named session
  - Reusing the same session across multiple agent.run() calls
  - Reading conversation history
  - Listing all sessions
  - Deleting a session

Run:
    python examples/session_management.py
"""

import asyncio

from openjiuwen.sdk import Agent, ModelConfig, Session


async def main() -> None:
    agent = await Agent.create("assistant", model=ModelConfig.from_env())

    # ------------------------------------------------------------------
    # Create a named session
    # ------------------------------------------------------------------
    session = Session.create(title="Paris trip planning")
    print(f"Created session: {session.session_id!r}  title={session.title!r}")

    # ------------------------------------------------------------------
    # Run two turns in the same session
    # ------------------------------------------------------------------
    r1 = await agent.run("What are three must-see places in Paris?", session_id=session.session_id)
    print("\nTurn 1:", r1.text[:120], "…")

    r2 = await agent.run("Which one is the most family-friendly?", session_id=session.session_id)
    print("\nTurn 2:", r2.text[:120], "…")

    # ------------------------------------------------------------------
    # Read history
    # ------------------------------------------------------------------
    history = await session.history()
    print(f"\nHistory ({len(history)} messages):")
    for msg in history:
        snippet = msg.text[:60].replace("\n", " ")
        print(f"  [{msg.role:9s}] {snippet}…")

    # ------------------------------------------------------------------
    # List all sessions
    # ------------------------------------------------------------------
    all_sessions = Session.list()
    print(f"\nAll sessions ({len(all_sessions)}):")
    for s in all_sessions:
        print(f"  {s.session_id}  {s.title!r}")

    # ------------------------------------------------------------------
    # Retrieve by ID and confirm it's the same session
    # ------------------------------------------------------------------
    retrieved = Session.get(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id
    print(f"\nRetrieved session: {retrieved.session_id!r}")

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    session.delete()
    assert Session.get(session.session_id) is None
    print("Session deleted.")


if __name__ == "__main__":
    asyncio.run(main())

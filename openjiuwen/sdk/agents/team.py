"""SDK Team façade.

A :class:`Team` orchestrates multiple :class:`~openjiuwen.sdk.core.agent.Agent`
instances via the JiuwenSwarm agent-teams subsystem.

Usage::

    researcher = await Agent.create("researcher", model=model_cfg)
    writer     = await Agent.create("writer",     model=model_cfg)

    team = await Team.create(agents=[researcher, writer], model=model_cfg)
    result = await team.spawn("Research quantum computing and write a summary.")
    print(result.final_output)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from openjiuwen.sdk.core.agent import Agent
    from openjiuwen.sdk.core.config import ModelConfig


# ---------------------------------------------------------------------------
# TeamResult — returned by Team.spawn()
# ---------------------------------------------------------------------------


@dataclass
class TeamResult:
    """The result of a team task.

    Attributes:
        final_output:  The leader agent's final answer / deliverable.
        session_id:    The team session ID.
        member_outputs: Per-member outputs keyed by member name.
    """

    final_output: str
    session_id: str | None = None
    member_outputs: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Team façade
# ---------------------------------------------------------------------------


class Team:
    """Orchestrates multiple agents under a shared leader.

    Do **not** instantiate directly.  Use :meth:`create`.
    """

    def __init__(self, _handle: Any) -> None:
        self._handle = _handle

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        agents: list["Agent"],
        *,
        model: Optional["ModelConfig"] = None,
        spec: Any = None,
        team_name: Optional[str] = None,
    ) -> "Team":
        """Create a team from a list of agents.

        Args:
            agents:     Agent list.  The first agent becomes the team leader.
            model:      Model config for the leader (defaults to
                        :meth:`~openjiuwen.sdk.core.config.ModelConfig.from_env`).
            spec:       Advanced — pass a raw ``TeamAgentSpec`` to override
                        everything.  When provided, *agents* is ignored.
            team_name:  Name for the team.  Auto-generated if omitted.

        Returns:
            A :class:`Team` ready to call :meth:`spawn`.
        """
        try:
            from openjiuwen.core.runner import Runner  # noqa: F401
        except ImportError as exc:
            from openjiuwen.sdk.core.errors import RuntimeNotAvailableError

            raise RuntimeNotAvailableError(
                "openjiuwen runtime is not installed.  Install: pip install openjiuwen"
            ) from exc

        from openjiuwen.sdk._internal.runner_bridge import _get_runner
        from openjiuwen.sdk.core.config import ModelConfig

        if model is None:
            model = ModelConfig.from_env()

        # If a raw TeamAgentSpec was passed, use it directly.
        if spec is not None:
            handle = _TeamHandle(spec=spec, model_cfg=model)
            await handle._ensure_team()
            return cls(handle)

        # Build a TeamAgentSpec from the SDK agent list.
        import uuid

        name = team_name or f"sdk-team-{uuid.uuid4().hex[:8]}"
        handle = _TeamHandle.from_agents(name, agents, model)
        await handle._ensure_team()
        return cls(handle)

    # ------------------------------------------------------------------
    # Spawn a task
    # ------------------------------------------------------------------

    async def spawn(self, prompt: str) -> TeamResult:
        """Assign a task to the team and wait for the result.

        The leader agent breaks the task down and coordinates teammates.

        Args:
            prompt: The high-level task description.

        Returns:
            :class:`TeamResult` with ``final_output``.
        """
        return await self._handle.spawn(prompt)

    async def send(self, message: str, *, to: Optional[str] = None) -> None:
        """Send a message to a specific team member (or broadcast).

        Args:
            message: The message text.
            to:      Member name.  If ``None``, broadcasts to all.
        """
        await self._handle.send(message, to=to)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Team(handle={self._handle!r})"


# ---------------------------------------------------------------------------
# Internal team handle
# ---------------------------------------------------------------------------


@dataclass
class _TeamHandle:
    """Internal state for one Team instance."""

    model_cfg: Any
    spec: Any = None
    _agents: list["Agent"] = field(default_factory=list, init=False, repr=False)
    _team_agent: Any = field(default=None, init=False, repr=False)

    @classmethod
    def from_agents(
        cls,
        team_name: str,
        agents: list["Agent"],
        model_cfg: Any,
    ) -> "_TeamHandle":
        handle = cls(model_cfg=model_cfg)
        handle._agents = agents
        handle._team_name = team_name
        return handle

    async def _ensure_team(self) -> Any:
        if self._team_agent is not None:
            return self._team_agent

        from openjiuwen.sdk._internal.runner_bridge import _build_model, _get_runner

        if self.spec is not None:
            # Use the provided TeamAgentSpec
            team = self.spec.build()
            self._team_agent = team
            return team

        # Build from SDK Agent list
        from openjiuwen.agent_teams.schema.blueprint import TeamAgentSpec
        from openjiuwen.harness.schema.config import DeepAgentConfig
        from openjiuwen.harness.factory import create_deep_agent
        from openjiuwen.core.single_agent.schema.agent_card import AgentCard

        import uuid

        runner = await _get_runner()
        model = _build_model(self.model_cfg)

        # Build per-member DeepAgentSpec entries
        agents_spec: dict[str, Any] = {}
        for i, agent in enumerate(self._agents):
            role = "leader" if i == 0 else f"teammate_{i}"
            member_handle = agent._handle
            if hasattr(member_handle, "_deep_agent") and member_handle._deep_agent is not None:
                agents_spec[role] = member_handle._deep_agent
            else:
                # Build a fresh DeepAgentSpec for this member
                from openjiuwen.harness.schema.config import DeepAgentSpec

                member_name = getattr(member_handle, "name", role)
                deep_cfg = DeepAgentConfig(
                    model=model,
                    card=AgentCard(id=f"sdk-{uuid.uuid4().hex[:8]}", name=member_name),
                    enable_task_loop=True,
                )
                agents_spec[role] = create_deep_agent(deep_cfg)

        team_spec = TeamAgentSpec(
            team_name=getattr(self, "_team_name", f"sdk-team-{uuid.uuid4().hex[:8]}"),
            agents=agents_spec,
            spawn_mode="inprocess",
        )
        self._team_agent = team_spec.build()
        return self._team_agent

    async def spawn(self, prompt: str) -> TeamResult:
        team = await self._ensure_team()

        from openjiuwen.core.session import create_agent_session

        session = create_agent_session()
        await session.pre_run()

        try:
            result = await team.invoke({"query": prompt}, agent_session=session)
        finally:
            try:
                await session.post_run()
            except Exception:  # noqa: BLE001
                pass

        # Extract text from result
        if isinstance(result, dict):
            text = result.get("text") or result.get("content") or result.get("output", str(result))
        else:
            text = str(result)

        return TeamResult(final_output=text, session_id=session.get_session_id())

    async def send(self, message: str, *, to: Optional[str] = None) -> None:
        team = await self._ensure_team()
        if hasattr(team, "send_message"):
            await team.send_message(message, target=to)

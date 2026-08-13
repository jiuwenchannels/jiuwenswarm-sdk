"""SDK SwarmFlow façade — structured multi-agent orchestration.

:class:`SwarmFlow` orchestrates multiple agents using ``best_of`` or
``majority_vote`` strategies, collecting all candidate outputs and selecting
the best one.

Quick start::

    from openjiuwen.sdk.swarm import SwarmFlow

    agents = [agent1, agent2, agent3]
    swarm = SwarmFlow.create(agents, strategy="best_of")
    result = await swarm.run("Write a concise product description.")
    print(result.output)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openjiuwen.sdk._internal import swarm_bridge as _sb
from openjiuwen.sdk.errors import SdkError

if TYPE_CHECKING:
    from openjiuwen.sdk.agent import Agent


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class SwarmResult:
    """The result of a :class:`SwarmFlow` run.

    Attributes:
        output:    The selected candidate output (string).
        strategy:  The selection strategy that was used.
        candidates: All candidate outputs from each agent.
        metadata:  Extra fields.
    """

    output: str
    strategy: str = "best_of"
    candidates: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SwarmFlow façade
# ---------------------------------------------------------------------------


class SwarmFlow:
    """Runs multiple agents in parallel and selects the best output.

    Strategies
    ----------
    * ``"best_of"``       — pick the longest response (default heuristic).
    * ``"majority_vote"`` — pick the most common response (exact match).
    * ``"first"``         — pick the first non-empty response.

    Example::

        swarm = SwarmFlow.create([agent_a, agent_b, agent_c], strategy="best_of")
        result = await swarm.run("Summarise the latest AI research trends.")
        print(result.output)
    """

    _VALID_STRATEGIES = {"best_of", "majority_vote", "first"}

    def __init__(
        self,
        agents: list["Agent"],
        strategy: str = "best_of",
    ) -> None:
        if not agents:
            raise SdkError("SwarmFlow requires at least one agent.")
        if strategy not in self._VALID_STRATEGIES:
            raise SdkError(
                f"Unknown strategy {strategy!r}. "
                f"Valid options: {sorted(self._VALID_STRATEGIES)}"
            )
        self._agents = agents
        self._strategy = strategy

    @classmethod
    def create(
        cls,
        agents: list["Agent"],
        strategy: str = "best_of",
    ) -> "SwarmFlow":
        """Create a new :class:`SwarmFlow`.

        Args:
            agents:   List of :class:`~openjiuwen.sdk.agent.Agent` instances.
            strategy: Selection strategy (``"best_of"`` / ``"majority_vote"`` / ``"first"``).

        Returns:
            A configured :class:`SwarmFlow`.
        """
        return cls(agents, strategy=strategy)

    async def run(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
    ) -> SwarmResult:
        """Run all agents concurrently on *prompt* and return the selected result.

        Args:
            prompt:     The task prompt sent to every agent.
            session_id: Optional session to continue.

        Returns:
            :class:`SwarmResult` with ``output`` and ``candidates``.

        Raises:
            :class:`~openjiuwen.sdk.errors.SdkError`: If all agents fail.
        """
        tasks = [agent.run(prompt, session_id=session_id) for agent in self._agents]
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates: list[str] = []
        for r in agent_results:
            if isinstance(r, Exception):
                candidates.append("")
            else:
                candidates.append(getattr(r, "text", str(r)))

        non_empty = [c for c in candidates if c]
        if not non_empty:
            raise SdkError("All agents in the swarm failed to produce output.")

        if self._strategy == "majority_vote":
            output = _sb.majority_vote(non_empty)
        elif self._strategy == "first":
            output = non_empty[0]
        else:  # best_of
            output = _sb.select_best_of(non_empty)

        return SwarmResult(
            output=output,
            strategy=self._strategy,
            candidates=candidates,
        )

    def __repr__(self) -> str:
        return f"SwarmFlow(agents={len(self._agents)}, strategy={self._strategy!r})"

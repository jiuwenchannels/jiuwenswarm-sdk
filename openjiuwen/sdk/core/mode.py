"""Agent execution modes and channel routing constants.

These are thin namespaces over the raw strings accepted by the jiuwenswarm
server.  Using them instead of bare strings gives IDE autocomplete and avoids
silent typos.

Example::

    from openjiuwen.sdk import AgentMode, ChannelId

    agent = await Agent.create(
        "coder",
        model=cfg,
        mode=AgentMode.CODE,
        channel_id=ChannelId.API,
    )

    result = await agent.run("Write a binary search.", mode=AgentMode.CODE)
"""

from __future__ import annotations


class AgentMode:
    """Execution mode constants for :class:`~openjiuwen.sdk.core.agent.Agent`.

    Pass as the ``mode`` argument to :meth:`~openjiuwen.sdk.core.agent.Agent.create`,
    :meth:`~openjiuwen.sdk.core.agent.Agent.connect`,
    :meth:`~openjiuwen.sdk.core.agent.Agent.run`, or
    :meth:`~openjiuwen.sdk.core.agent.Agent.stream_events`.

    Attributes:
        AGENT:      General-purpose agent (default).  The model uses all
                    available tools and reasons step-by-step.
        CODE:       Code generation mode.  The model focuses on producing
                    correct, runnable code with minimal prose.
        TEAM:       Multi-agent team mode.  The request is dispatched to the
                    leader of a :class:`~openjiuwen.sdk.agents.team.Team` who
                    coordinates teammates.
        CODE_TEAM:  Code generation + team coordination.  Combines CODE and
                    TEAM: multiple code-focused agents collaborate.
    """

    AGENT:     str = "agent"
    CODE:      str = "code"
    TEAM:      str = "team"
    CODE_TEAM: str = "code.team"

    # Alias accepted by some older gateway versions
    DEFAULT:   str = "agent"

    @classmethod
    def values(cls) -> list[str]:
        """Return all valid mode strings."""
        return [cls.AGENT, cls.CODE, cls.TEAM, cls.CODE_TEAM]

    @classmethod
    def validate(cls, value: str) -> str:
        """Return *value* unchanged, or raise ``ValueError`` if it's unknown.

        Args:
            value: Mode string to validate.

        Returns:
            The validated mode string.

        Raises:
            ValueError: If *value* is not a recognised mode.
        """
        if value not in cls.values():
            raise ValueError(
                f"Unknown AgentMode {value!r}. "
                f"Valid values: {cls.values()}"
            )
        return value


class ChannelId:
    """Channel routing constants for :class:`~openjiuwen.sdk.core.agent.Agent`.

    The jiuwenswarm server routes requests to named channels so that
    different clients (API, IDE, browser, notebook) can be handled with
    per-channel configuration (logging, context injection, tool sets, …).

    Pass as the ``channel_id`` argument to
    :meth:`~openjiuwen.sdk.core.agent.Agent.create`,
    :meth:`~openjiuwen.sdk.core.agent.Agent.connect`,
    :meth:`~openjiuwen.sdk.core.agent.Agent.run`, or
    :meth:`~openjiuwen.sdk.core.agent.Agent.stream_events`.

    Attributes:
        API:        Generic programmatic / REST API channel (default for SDK).
        JUPYTER:    JupyterLab extension channel.
        IDE:        IDE (JetBrains / VS Code) extension channel.
        BROWSER:    Browser extension channel.
        CLI:        Command-line interface channel.
    """

    API:     str = "api"
    JUPYTER: str = "jupyter"
    IDE:     str = "ide"
    BROWSER: str = "browser"
    CLI:     str = "cli"

    @classmethod
    def values(cls) -> list[str]:
        """Return all predefined channel ID strings."""
        return [cls.API, cls.JUPYTER, cls.IDE, cls.BROWSER, cls.CLI]

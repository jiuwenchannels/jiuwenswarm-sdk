"""SDK Agent façade.

:class:`Agent` is the primary entry point of the Python SDK.  It has two
constructors — :meth:`create` (in-process) and :meth:`connect` (remote) —
and exposes the same ``run`` / ``stream`` / ``on`` API in both modes.

In-process mode::

    agent = await Agent.create("researcher", model=ModelConfig.from_env())
    result = await agent.run("Explain asyncio in one sentence.")
    print(result.text)

Remote mode::

    agent = await Agent.connect("ws://localhost:19000/v1/ws")
    result = await agent.run("Hello!")
    print(result.text)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Optional

from openjiuwen.sdk.core.events import EventEmitter

if TYPE_CHECKING:
    from openjiuwen.sdk.core.config import ModelConfig, RemoteConfig
    from openjiuwen.sdk.core.hooks import Hooks
    from openjiuwen.sdk.core.tools import SdkTool


# ---------------------------------------------------------------------------
# AgentResult — returned by Agent.run()
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """The result of a non-streaming agent invocation.

    Attributes:
        text:       The agent's response as plain text.
        session_id: The session ID used for this run.
        metadata:   Optional extra data (tokens used, tool calls, etc.).
    """

    text: str
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent façade
# ---------------------------------------------------------------------------


class Agent(EventEmitter):
    """JiuwenSwarm agent — thin façade over the runtime or a remote server.

    Do **not** instantiate directly.  Use :meth:`create` or :meth:`connect`.

    Events
    ------
    ``"token"``       — ``(text: str)`` streaming token arrived.
    ``"done"``        — ``()``          agent finished.
    ``"error"``       — ``(msg: str)``  agent encountered an error.
    ``"tool_call"``   — ``(name: str, args: dict)``   tool call started.
    ``"tool_result"`` — ``(name: str, result: str)``  tool call completed.
    """

    def __init__(self, _handle: Any, *, _mode: str) -> None:
        super().__init__()
        self._handle = _handle
        self._mode = _mode  # "inprocess" or "remote"

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        name: str,
        *,
        model: Optional["ModelConfig"] = None,
        tools: Optional[list["SdkTool"]] = None,
        workspace: Any = None,
        memory_scope: Any = None,
        knowledge_bases: Optional[list[Any]] = None,
        event_handler: Any = None,
        checkpoint_store: Optional[str] = None,
        checkpoint_every: Optional[int] = None,
        permission_engine: Any = None,
        context_engine: Any = None,
        rl_optimizer: Any = None,
        system_prompt: Optional[str] = None,
        hooks: Optional["Hooks"] = None,
    ) -> "Agent":
        """Create an in-process agent.

        The agent runtime (``openjiuwen.core``, ``openjiuwen.harness``) runs
        inside the caller's Python process.  Requires the ``openjiuwen``
        package to be installed.

        Args:
            name:              Agent name (used for logging and registration).
            model:             LLM configuration.  Defaults to
                               :meth:`~openjiuwen.sdk.core.config.ModelConfig.from_env`.
            tools:             :class:`~openjiuwen.sdk.core.tools.SdkTool` list.
            workspace:         :class:`~openjiuwen.harness.workspace.Workspace`
                               instance that bounds the agent to a directory.
            memory_scope:      Long-term memory scope.
            knowledge_bases:   Knowledge base list for RAG.
            event_handler:     Task loop event handler for observing/intercepting steps.
            checkpoint_store:  Name of a registered checkpoint backend
                               (e.g. ``"sqlite"``, ``"s3"``).
            checkpoint_every:  Auto-checkpoint every N task-loop turns.
            permission_engine: :class:`~openjiuwen.harness.security.PermissionEngine`
                               instance for tool permission enforcement.
            context_engine:    :class:`~openjiuwen.core.context_engine.ContextEngine`
                               for context compression.
            rl_optimizer:      Online/offline RL optimizer for trajectory collection.
            system_prompt:     Override the default system prompt.
            hooks:             :class:`~openjiuwen.sdk.core.hooks.Hooks` instance
                               with pre-registered lifecycle callbacks.

        Returns:
            An :class:`Agent` ready for ``run()`` / ``stream()`` calls.
        """
        from openjiuwen.sdk._internal.runner_bridge import AgentHandle
        from openjiuwen.sdk.core.config import ModelConfig

        if model is None:
            model = ModelConfig.from_env()

        handle = AgentHandle(
            name=name,
            model_cfg=model,
            tools=tools or [],
            workspace=workspace,
            memory_scope=memory_scope,
            knowledge_bases=knowledge_bases or [],
            event_handler=event_handler,
            checkpoint_store=checkpoint_store,
            checkpoint_every=checkpoint_every,
            permission_engine=permission_engine,
            context_engine=context_engine,
            rl_optimizer=rl_optimizer,
            system_prompt=system_prompt,
        )
        # Eagerly initialise the DeepAgent so errors surface here, not at
        # the first run() call.
        await handle._ensure_agent()
        agent = cls(handle, _mode="inprocess")
        if hooks is not None:
            hooks.wire(agent)
        return agent

    @classmethod
    async def connect(
        cls,
        server_url: str,
        *,
        auth_token: Optional[str] = None,
        config: Optional["RemoteConfig"] = None,
    ) -> "Agent":
        """Connect to a remote JiuwenSwarm server.

        Equivalent to what the browser extension and mobile app do — drives the
        JiuwenSwarm WebSocket gateway from Python.

        Args:
            server_url:  WebSocket (``ws://``) or HTTP (``http://``) URL of the
                         gateway.  Example: ``"ws://localhost:19000/v1/ws"``.
            auth_token:  Bearer token for the ``Authorization`` header.
            config:      Full :class:`~openjiuwen.sdk.core.config.RemoteConfig`
                         (takes precedence over individual args).

        Returns:
            An :class:`Agent` backed by the remote server.

        Note:
            Remote mode does **not** support ``checkpoint()``, ``workspace``,
            ``event_handler``, or custom backend registration — those require
            direct access to the runtime.
        """
        from openjiuwen.sdk._internal.remote_bridge import RemoteHandle

        if config is not None:
            server_url = config.server_url
            auth_token = auth_token or config.auth_token
            timeout = config.timeout
            max_retries = config.max_retries
        else:
            timeout = 60.0
            max_retries = 3

        handle = RemoteHandle(
            server_url=server_url,
            auth_token=auth_token,
            timeout=timeout,
            max_retries=max_retries,
        )
        await handle.connect()
        return cls(handle, _mode="remote")

    # ------------------------------------------------------------------
    # Sync convenience constructor (in-process only)
    # ------------------------------------------------------------------

    @classmethod
    def create_sync(
        cls,
        name: str,
        *,
        model: Optional["ModelConfig"] = None,
        tools: Optional[list["SdkTool"]] = None,
        **kwargs: Any,
    ) -> "Agent":
        """Synchronous variant of :meth:`create`.

        Blocks the calling thread until the agent is ready.  Useful in scripts
        and REPL sessions that do not have an event loop.

        Example::

            agent = Agent.create_sync("my-agent", model=ModelConfig.from_env())
            result = agent.run_sync("Hello!")
        """
        from openjiuwen.sdk._internal.sync_wrapper import run_sync

        return run_sync(cls.create(name, model=model, tools=tools, **kwargs))

    # ------------------------------------------------------------------
    # Run (non-streaming)
    # ------------------------------------------------------------------

    async def run(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
    ) -> AgentResult:
        """Run the agent and return the complete response.

        Args:
            prompt:     The user prompt / task description.
            session_id: Existing session ID to continue.  A new session is
                        created automatically if omitted.

        Returns:
            :class:`AgentResult` with ``text`` and ``session_id``.
        """
        if self._mode == "inprocess":
            raw = await self._handle.run(prompt, session_id=session_id)
            result = AgentResult(text=raw.text, session_id=raw.session_id, metadata=raw.metadata)
        else:
            raw = await self._handle.run(prompt, session_id=session_id)
            result = AgentResult(text=raw.text, session_id=raw.session_id)

        self.emit("done")
        return result

    def run_sync(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
    ) -> AgentResult:
        """Synchronous variant of :meth:`run`.

        Example::

            result = agent.run_sync("What is the capital of France?")
            print(result.text)
        """
        from openjiuwen.sdk._internal.sync_wrapper import run_sync

        return run_sync(self.run(prompt, session_id=session_id))

    # ------------------------------------------------------------------
    # Stream
    # ------------------------------------------------------------------

    async def stream(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream the agent's response, yielding text tokens as they arrive.

        Args:
            prompt:     The user prompt / task description.
            session_id: Existing session ID to continue.

        Yields:
            Text tokens (``str``).

        Example::

            async for token in agent.stream("Write a haiku."):
                print(token, end="", flush=True)
        """
        if self._mode == "inprocess":
            async for token in self._handle.stream(prompt, session_id=session_id):
                self.emit("token", token)
                yield token
        else:
            async for token in self._handle.stream(prompt, session_id=session_id):
                self.emit("token", token)
                yield token
        self.emit("done")

    # ------------------------------------------------------------------
    # Checkpoint (in-process only)
    # ------------------------------------------------------------------

    async def checkpoint(self) -> str:
        """Save the agent's state and return an opaque checkpoint ID.

        The returned ID can be passed to :meth:`restore` to resume from this
        exact point.

        Only available in in-process mode.
        """
        if self._mode != "inprocess":
            from openjiuwen.sdk.core.errors import AgentError

            raise AgentError("checkpoint() is only available in in-process mode.")
        return await self._handle.checkpoint()

    @classmethod
    async def restore(
        cls,
        checkpoint_id: str,
        *,
        model: Optional["ModelConfig"] = None,
    ) -> "Agent":
        """Restore an agent from a previously saved checkpoint.

        Args:
            checkpoint_id: ID returned by :meth:`checkpoint`.
            model:         Override the model config.

        Returns:
            A new :class:`Agent` pre-loaded with the checkpoint state.
        """
        # For now, create a fresh agent and let the runtime load state.
        # Full checkpointing support will be wired in a later phase.
        from openjiuwen.sdk._internal.runner_bridge import AgentHandle
        from openjiuwen.sdk.core.config import ModelConfig

        if model is None:
            model = ModelConfig.from_env()

        handle = AgentHandle(name=f"restored-{checkpoint_id[:8]}", model_cfg=model)
        await handle._ensure_agent()
        agent = cls(handle, _mode="inprocess")
        return agent

    # ------------------------------------------------------------------
    # Disconnect (remote mode)
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying connection (remote mode) or release resources."""
        if self._mode == "remote":
            await self._handle.disconnect()

    async def __aenter__(self) -> "Agent":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        mode = self._mode
        if mode == "inprocess" and hasattr(self._handle, "name"):
            return f"Agent(name={self._handle.name!r}, mode='inprocess')"
        if mode == "remote" and hasattr(self._handle, "server_url"):
            return f"Agent(server={self._handle.server_url!r}, mode='remote')"
        return f"Agent(mode={mode!r})"

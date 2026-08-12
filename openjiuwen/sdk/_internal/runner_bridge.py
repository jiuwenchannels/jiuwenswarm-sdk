"""In-process runner bridge.

Wraps the ``openjiuwen.harness`` / ``openjiuwen.core`` runtime so that the
:class:`~openjiuwen.sdk.agent.Agent` façade can drive it through a stable
internal API without leaking internals into the public surface.

Key responsibilities
--------------------
* Lazily start a process-global ``Runner`` on first use.
* Translate :class:`~openjiuwen.sdk.config.ModelConfig` → runtime ``Model``.
* Build a ``DeepAgent`` via the harness factory.
* Drive non-streaming and streaming invocations.
* Extract plain text from whatever the runtime returns.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from openjiuwen.sdk.config import ModelConfig
    from openjiuwen.sdk.tools import SdkTool

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Runtime availability guard
# ---------------------------------------------------------------------------

_RUNTIME_MISSING_MSG = (
    "The openjiuwen runtime is not installed.  "
    "Install it with: pip install openjiuwen"
)


def _require_runtime() -> None:
    try:
        import openjiuwen.core  # noqa: F401
    except ImportError as exc:
        from openjiuwen.sdk.errors import RuntimeNotAvailableError

        raise RuntimeNotAvailableError(_RUNTIME_MISSING_MSG) from exc


# ---------------------------------------------------------------------------
# Lazy global runner
# ---------------------------------------------------------------------------

_runner: Any = None          # openjiuwen.core.runner.Runner instance
_runner_lock = asyncio.Lock()


async def _get_runner() -> Any:
    """Return (and lazily start) the process-global Runner."""
    global _runner  # noqa: PLW0603
    # Fast path — already initialised.
    if _runner is not None:
        return _runner

    async with _runner_lock:
        if _runner is not None:
            return _runner
        _require_runtime()
        from openjiuwen.core.runner import Runner

        runner = Runner()
        await runner.start()
        _runner = runner
        log.debug("[sdk] global Runner started")
    return _runner


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

def _build_model(cfg: "ModelConfig") -> Any:
    """Translate a :class:`ModelConfig` into a runtime ``Model``."""
    from openjiuwen.core.foundation.llm import init_model

    return init_model(
        provider=cfg._normalised_provider,
        model_name=cfg.model,
        api_key=cfg.api_key or "",
        api_base=cfg.api_base or "",
        temperature=cfg.temperature if cfg.temperature is not None else 0.95,
        timeout=cfg.timeout,
        max_retries=cfg.max_retries,
        max_tokens=cfg.max_tokens,
    )


# ---------------------------------------------------------------------------
# Tool conversion
# ---------------------------------------------------------------------------

def _sdk_tools_to_runtime(sdk_tools: list["SdkTool"]) -> list[Any]:
    """Wrap :class:`SdkTool` instances as runtime ``ToolCard`` + ``LocalFunction`` pairs.

    The runtime expects either registered tool IDs or ``ToolCard``-like objects.
    We wrap each :class:`SdkTool` in a minimal adapter that the harness can call.
    """
    from openjiuwen.core.foundation.tool import ToolCard
    from openjiuwen.core.foundation.tool.tool import tool as runtime_tool_decorator

    runtime_tools: list[Any] = []
    for sdk_t in sdk_tools:
        # Re-wrap the underlying function with the runtime @tool decorator so
        # it gets a proper ToolCard and is callable by the harness.
        wrapped = runtime_tool_decorator(
            fn=sdk_t.fn,
            name=sdk_t.name,
            description=sdk_t.description,
        )
        runtime_tools.append(wrapped.card)
    return runtime_tools


# ---------------------------------------------------------------------------
# Text extraction from runtime output
# ---------------------------------------------------------------------------

def _extract_text(result: Any) -> str:
    """Extract plain text from whatever the runtime agent returns."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("text", "content", "output", "response", "answer", "result"):
            if key in result and isinstance(result[key], str):
                return result[key]
        # Fallback: concatenate all string values
        parts = [str(v) for v in result.values() if isinstance(v, (str, int, float))]
        return " ".join(parts) if parts else str(result)
    # Pydantic model or OutputSchema-like object
    for attr in ("text", "content", "output"):
        val = getattr(result, attr, None)
        if isinstance(val, str):
            return val
    return str(result)


def _extract_token(chunk: Any) -> str | None:
    """Extract a text token from a streaming chunk, or return ``None`` to skip."""
    if isinstance(chunk, str):
        return chunk or None
    if isinstance(chunk, dict):
        for key in ("text", "content", "token", "delta"):
            val = chunk.get(key)
            if isinstance(val, str) and val:
                return val
        return None
    for attr in ("text", "content", "token"):
        val = getattr(chunk, attr, None)
        if isinstance(val, str) and val:
            return val
    return None


# ---------------------------------------------------------------------------
# AgentHandle — holds a live agent + runner reference
# ---------------------------------------------------------------------------


@dataclass
class AgentHandle:
    """Internal state for one in-process :class:`~openjiuwen.sdk.agent.Agent`."""

    name: str
    model_cfg: "ModelConfig"
    tools: list["SdkTool"] = field(default_factory=list)
    workspace: Any = None  # openjiuwen.harness.workspace.Workspace | None
    memory_scope: Any = None
    knowledge_bases: list[Any] = field(default_factory=list)
    event_handler: Any = None
    checkpoint_store: str | None = None
    checkpoint_every: int | None = None
    permission_engine: Any = None
    context_engine: Any = None
    rl_optimizer: Any = None
    system_prompt: str | None = None

    _deep_agent: Any = field(default=None, init=False, repr=False)
    _agent_id: str = field(default_factory=lambda: f"sdk-{uuid.uuid4().hex[:8]}", init=False)

    async def _ensure_agent(self) -> Any:
        if self._deep_agent is not None:
            return self._deep_agent

        _require_runtime()
        from openjiuwen.core.single_agent.schema.agent_card import AgentCard
        from openjiuwen.harness.factory import create_deep_agent
        from openjiuwen.harness.schema.config import DeepAgentConfig

        model = _build_model(self.model_cfg)
        card = AgentCard(id=self._agent_id, name=self.name)

        runtime_tools = _sdk_tools_to_runtime(self.tools) if self.tools else None

        config = DeepAgentConfig(
            model=model,
            card=card,
            tools=runtime_tools,
            workspace=self.workspace,
            system_prompt=self.system_prompt,
            permissions=self.permission_engine.config if self.permission_engine else None,
            permission_host=(
                self.permission_engine._host if self.permission_engine else None
            ),
            context_engine_config=self.context_engine,
            enable_task_loop=True,
        )

        agent = create_deep_agent(config)

        # Register tools with the runner resource manager
        runner = await _get_runner()
        for sdk_t in self.tools:
            try:
                from openjiuwen.core.foundation.tool.tool import tool as rt_tool

                wrapped = rt_tool(fn=sdk_t.fn, name=sdk_t.name, description=sdk_t.description)
                runner.resource_mgr.register_tool(wrapped.card, owner_id=self._agent_id)
            except Exception:  # noqa: BLE001
                log.debug("[sdk] could not register tool %s", sdk_t.name)

        self._deep_agent = agent
        log.debug("[sdk] created DeepAgent id=%s name=%s", self._agent_id, self.name)
        return agent

    # ------------------------------------------------------------------
    # Run (non-streaming)
    # ------------------------------------------------------------------

    async def run(self, prompt: str, session_id: str | None = None) -> "AgentRunResult":
        from openjiuwen.core.session import create_agent_session
        from openjiuwen.sdk._internal.session_bridge import (
            append_message,
            create_session as _create_sess,
            get_session,
            make_internal_session,
        )

        agent = await self._ensure_agent()

        # Resolve or create the SDK session record.
        if session_id is not None:
            record = get_session(session_id)
            if record is None:
                from openjiuwen.sdk.errors import SessionError

                raise SessionError(f"Session '{session_id}' not found.")
        else:
            record = _create_sess(title=f"{self.name} session", mode="default")

        internal_sess = make_internal_session(record)
        await internal_sess.pre_run()

        try:
            result = await agent.invoke({"query": prompt}, agent_session=internal_sess)
        except Exception as exc:
            from openjiuwen.sdk.errors import AgentError

            raise AgentError(f"Agent '{self.name}' failed: {exc}") from exc
        finally:
            try:
                await internal_sess.post_run()
            except Exception:  # noqa: BLE001
                pass

        text = _extract_text(result)
        append_message(record.id, role="user", text=prompt)
        append_message(record.id, role="assistant", text=text)
        return AgentRunResult(text=text, session_id=record.id)

    # ------------------------------------------------------------------
    # Stream
    # ------------------------------------------------------------------

    async def stream(self, prompt: str, session_id: str | None = None) -> AsyncIterator[str]:
        from openjiuwen.sdk._internal.session_bridge import (
            append_message,
            create_session as _create_sess,
            get_session,
            make_internal_session,
        )

        agent = await self._ensure_agent()

        if session_id is not None:
            record = get_session(session_id)
            if record is None:
                from openjiuwen.sdk.errors import SessionError

                raise SessionError(f"Session '{session_id}' not found.")
        else:
            record = _create_sess(title=f"{self.name} session", mode="default")

        internal_sess = make_internal_session(record)
        await internal_sess.pre_run()

        collected: list[str] = []
        try:
            async for chunk in agent.stream({"query": prompt}, agent_session=internal_sess):
                token = _extract_token(chunk)
                if token:
                    collected.append(token)
                    yield token
        except Exception as exc:
            from openjiuwen.sdk.errors import StreamError

            raise StreamError(f"Streaming agent '{self.name}' failed: {exc}") from exc
        finally:
            try:
                await internal_sess.post_run()
            except Exception:  # noqa: BLE001
                pass

        text = "".join(collected)
        append_message(record.id, role="user", text=prompt)
        append_message(record.id, role="assistant", text=text)

    # ------------------------------------------------------------------
    # Checkpoint
    # ------------------------------------------------------------------

    async def checkpoint(self) -> str:
        """Save agent state and return a checkpoint ID."""
        ckpt_id = f"ckpt_{uuid.uuid4().hex[:12]}"
        # Delegate to runtime checkpointer if available
        try:
            runner = await _get_runner()
            if hasattr(runner, "checkpoint"):
                await runner.checkpoint(agent_id=self._agent_id, checkpoint_id=ckpt_id)
        except Exception:  # noqa: BLE001
            pass  # checkpoint is best-effort for now
        return ckpt_id


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


@dataclass
class AgentRunResult:
    """Result of a non-streaming agent run."""

    text: str
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

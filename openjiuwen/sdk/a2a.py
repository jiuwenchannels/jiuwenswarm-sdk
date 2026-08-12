"""A2A (agent-to-agent) remote client facade.

Provides a thin, type-safe wrapper over the JiuwenSwarm A2A protocol so SDK
users can call a remote agent as if it were a local one.

Quick start::

    from openjiuwen.sdk import RemoteAgent

    agent = RemoteAgent(url="http://agent-service:9000", agent_id="summariser")
    result = await agent.run("Summarise this document")
    print(result.text)

    # Streaming:
    async for token in agent.stream("Tell me a joke"):
        print(token, end="", flush=True)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from openjiuwen.sdk.errors import AgentError, ConnectionError, SdkError, StreamError


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class A2AError(SdkError):
    """Raised on A2A protocol or transport errors."""


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class A2AResult:
    """Outcome of a :meth:`RemoteAgent.run` call."""

    text: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Module-level patchable callables (testability)
# ---------------------------------------------------------------------------


def _create_a2a_client(url: str, agent_id: str, auth_token: str | None, timeout: float) -> Any:
    """Build a runtime A2AClient (patchable)."""
    from openjiuwen.extensions.a2a.client import A2AClient
    from openjiuwen.extensions.a2a.schema import RemoteClientConfig

    cfg = RemoteClientConfig(
        id=agent_id,
        protocol="A2A",
        url=url,
        kwargs={"auth_token": auth_token} if auth_token else {},
    )
    return A2AClient(config=cfg, timeout=timeout)


async def _a2a_invoke(client: Any, inputs: dict[str, Any]) -> Any:
    """Call client.invoke (patchable)."""
    return await client.invoke(inputs)


async def _a2a_stream(client: Any, inputs: dict[str, Any]) -> AsyncIterator[Any]:
    """Call client.stream (patchable)."""
    async for chunk in client.stream(inputs):
        yield chunk


# ---------------------------------------------------------------------------
# RemoteAgent facade
# ---------------------------------------------------------------------------


class RemoteAgent:
    """SDK client for a remote JiuwenSwarm agent reachable via the A2A protocol.

    Args:
        url:        Base URL of the remote agent service
                    (e.g. ``"http://agent-host:9000"``).
        agent_id:   Identifier of the target agent on the remote service.
        auth_token: Optional bearer token for service authentication.
        timeout:    Request timeout in seconds (default 60 s).

    Example::

        agent = RemoteAgent(url="http://localhost:9001", agent_id="planner")
        result = await agent.run("Plan a trip to Tokyo")
    """

    def __init__(
        self,
        url: str,
        agent_id: str,
        *,
        auth_token: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._agent_id = agent_id
        self._auth_token = auth_token
        self._timeout = timeout
        self._client: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                self._client = _create_a2a_client(
                    self._url, self._agent_id, self._auth_token, self._timeout
                )
            except ImportError as exc:
                raise ConnectionError(
                    "A2A extension not installed. "
                    "Install it with: pip install openjiuwen[a2a]"
                ) from exc
        return self._client

    async def close(self) -> None:
        """Release the underlying A2A connection."""
        if self._client is not None and hasattr(self._client, "stop"):
            await self._client.stop()
        self._client = None

    async def __aenter__(self) -> "RemoteAgent":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    async def run(self, prompt: str, *, task_id: str | None = None) -> A2AResult:
        """Invoke the remote agent and return the final text output.

        Args:
            prompt:  Natural-language prompt to send.
            task_id: Optional correlation ID (auto-generated if omitted).

        Returns:
            :class:`A2AResult` with the agent's text reply.

        Raises:
            :class:`~openjiuwen.sdk.errors.ConnectionError`: service unreachable.
            :class:`A2AError`: protocol-level failure.
        """
        client = await self._get_client()
        task_id = task_id or f"task-{uuid.uuid4().hex[:8]}"
        inputs: dict[str, Any] = {"query": prompt, "task_id": task_id}
        try:
            result = await _a2a_invoke(client, inputs)
        except (ConnectionError, A2AError):
            raise
        except Exception as exc:
            raise A2AError(f"Remote agent '{self._agent_id}' failed: {exc}") from exc

        text = _extract_text(result)
        return A2AResult(text=text, task_id=task_id)

    async def stream(self, prompt: str, *, task_id: str | None = None) -> AsyncIterator[str]:
        """Stream the remote agent's response token by token.

        Args:
            prompt:  Natural-language prompt to send.
            task_id: Optional correlation ID (auto-generated if omitted).

        Yields:
            Text token strings from the remote agent.

        Raises:
            :class:`~openjiuwen.sdk.errors.ConnectionError`: service unreachable.
            :class:`~openjiuwen.sdk.errors.StreamError`:   streaming broke.
        """
        client = await self._get_client()
        task_id = task_id or f"task-{uuid.uuid4().hex[:8]}"
        inputs: dict[str, Any] = {"query": prompt, "task_id": task_id}
        try:
            async for chunk in _a2a_stream(client, inputs):
                token = _extract_text(chunk)
                if token:
                    yield token
        except (ConnectionError, A2AError, StreamError):
            raise
        except Exception as exc:
            raise StreamError(f"Remote stream from '{self._agent_id}' failed: {exc}") from exc

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task on the remote agent.

        Args:
            task_id: Task correlation ID returned by a previous :meth:`run`
                     call.

        Returns:
            ``True`` if the cancellation was acknowledged.
        """
        client = await self._get_client()
        try:
            if hasattr(client, "cancel_task"):
                await client.cancel_task(task_id)
            return True
        except Exception as exc:
            raise A2AError(f"Cancel task '{task_id}' failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"RemoteAgent(url={self._url!r}, agent_id={self._agent_id!r})"


# ---------------------------------------------------------------------------
# Text extraction (mirrors runner_bridge, kept local to avoid circular import)
# ---------------------------------------------------------------------------


def _extract_text(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for key in ("text", "content", "output", "response", "answer", "result"):
            val = obj.get(key)
            if isinstance(val, str) and val:
                return val
        parts = [str(v) for v in obj.values() if isinstance(v, (str, int, float))]
        return " ".join(parts) if parts else str(obj)
    for attr in ("text", "content", "output"):
        val = getattr(obj, attr, None)
        if isinstance(val, str) and val:
            return val
    return str(obj)

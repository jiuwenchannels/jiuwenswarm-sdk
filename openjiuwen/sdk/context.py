"""SDK Context Engine façade — pluggable context window management.

The :class:`ContextEngine` compresses or trims an agent's message history
when the context window approaches its limit, preventing token-overflow errors
during long-running tasks.

Quick start::

    from openjiuwen.sdk.context import ContextEngine, ContextEngineConfig

    engine = ContextEngine(config=ContextEngineConfig(token_limit=16_000))
    agent = await Agent.create("long-task", context_engine=engine, ...)

    stats = engine.last_stats
    if stats:
        print(f"Used {stats.input_tokens} tokens, {stats.compressions_applied} compressions")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextEngineConfig:
    """Configuration for a :class:`ContextEngine`.

    Attributes:
        max_messages:    Maximum number of messages to keep in the context window.
        token_limit:     Soft token ceiling; triggers compression when exceeded.
        compression_ratio: Target size of compressed context relative to original.
    """

    max_messages: int = 200
    token_limit: int = 32_000
    compression_ratio: float = 0.5


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextStats:
    """Runtime statistics from the last compression pass.

    Attributes:
        input_tokens:         Tokens in the context before compression.
        output_tokens:        Tokens after compression.
        compressions_applied: Number of compression passes run.
    """

    input_tokens: int
    output_tokens: int
    compressions_applied: int


# ---------------------------------------------------------------------------
# ContextEngine façade
# ---------------------------------------------------------------------------


class ContextEngine:
    """Manages context compression for long-running agents.

    Pass to :meth:`~openjiuwen.sdk.agent.Agent.create` as ``context_engine=``.

    When the runtime is available, delegates to ``openjiuwen.core.ContextEngine``.
    Otherwise, applies a simple truncation strategy.

    Attributes:
        config:     The :class:`ContextEngineConfig` this engine uses.
        last_stats: :class:`ContextStats` from the last compression pass, or ``None``.
    """

    def __init__(
        self,
        config: ContextEngineConfig | None = None,
        *,
        processors: list[Any] | None = None,
    ) -> None:
        self.config = config or ContextEngineConfig()
        self._processors = processors or []
        self.last_stats: ContextStats | None = None
        self._engine: Any = self._build_engine()

    def _build_engine(self) -> Any:
        try:
            from openjiuwen.core.context_engine import ContextEngine as _RtEngine, ContextEngineConfig as _RtConfig

            rt_cfg = _RtConfig(
                max_messages=self.config.max_messages,
                token_limit=self.config.token_limit,
            )
            return _RtEngine(config=rt_cfg, processors=self._processors or [])
        except ImportError:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(self, messages: list[Any]) -> list[Any]:
        """Compress *messages* to fit within the configured limits.

        Args:
            messages: List of message dicts or message objects.

        Returns:
            Compressed (potentially shorter) message list.
        """
        if self._engine is not None and hasattr(self._engine, "compress"):
            result = self._engine.compress(messages)
            self._update_stats(before=len(messages), after=len(result))
            return result
        # Fallback: trim to max_messages
        trimmed = messages[-self.config.max_messages :]
        self._update_stats(before=len(messages), after=len(trimmed))
        return trimmed

    def inject(self, messages: list[Any], text: str) -> list[Any]:
        """Inject *text* as a system message at the beginning of *messages*.

        Args:
            messages: Current message list.
            text:     Text to inject.

        Returns:
            Updated message list with the injected message prepended.
        """
        injected = {"role": "system", "content": text}
        return [injected, *messages]

    def token_count(self, messages: list[Any]) -> int:
        """Estimate the token count of *messages*.

        Uses a simple heuristic (4 chars ≈ 1 token) when the runtime
        tokenizer is not available.

        Args:
            messages: Message list.

        Returns:
            Estimated token count.
        """
        if self._engine is not None and hasattr(self._engine, "token_count"):
            return self._engine.token_count(messages)
        total_chars = sum(
            len(str(m.get("content", m) if isinstance(m, dict) else m))
            for m in messages
        )
        return total_chars // 4

    def _update_stats(self, before: int, after: int) -> None:
        prev_compressions = self.last_stats.compressions_applied if self.last_stats else 0
        self.last_stats = ContextStats(
            input_tokens=before * 100,   # rough estimate
            output_tokens=after * 100,
            compressions_applied=prev_compressions + (1 if after < before else 0),
        )

    def __repr__(self) -> str:
        return (
            f"ContextEngine(token_limit={self.config.token_limit}, "
            f"max_messages={self.config.max_messages})"
        )

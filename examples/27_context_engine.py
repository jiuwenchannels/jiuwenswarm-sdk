"""27_context_engine.py — pluggable context window compression for long-running agents.

Corresponds to §27 of the usage examples.

Shows:
  - ContextEngine with ContextEngineConfig (max_messages, token_limit)
  - ToolResultBudgetProcessor: trim oversized tool results
  - MessageSummaryOffloader: summarise old messages when window is 80% full
  - FullCompactProcessor: aggressive full-history compaction as fallback
  - Agent.create(context_engine=engine) integration
  - engine.last_stats for observability
  - MicroCompactProcessor for lighter per-turn compaction

Run:
    python examples/27_context_engine.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.core.context_engine import (
    ContextEngine,
    ContextEngineConfig,
    FullCompactProcessor,
    MessageSummaryOffloader,
    ToolResultBudgetProcessor,
)


async def main():
    model_cfg = ModelConfig.from_env()

    # Configure a compression strategy: budget tool results, then summarise old messages
    engine = ContextEngine(
        config=ContextEngineConfig(
            max_messages=200,
            token_limit=16_000,
        ),
        processors=[
            # First, trim oversized tool results
            ToolResultBudgetProcessor(max_chars_per_result=2000),
            # Then, summarise message history when the window is 80% full
            MessageSummaryOffloader(
                trigger_ratio=0.8,
                summary_model=model_cfg.build_llm_client(),
            ),
            # Final fallback: full compact (aggressive summarisation)
            FullCompactProcessor(model=model_cfg.build_llm_client()),
        ],
    )

    agent = await Agent.create(
        "long-context-agent",
        model=model_cfg,
        context_engine=engine,
    )

    # The agent can now handle very long research tasks without hitting token limits
    result = await agent.run(
        "Read all files in /workspace and produce a comprehensive architecture document."
    )
    print(result.text)

    # Inspect how much context was used
    stats = engine.last_stats
    if stats:
        print(f"\nContext stats: {stats.input_tokens} tokens used, "
              f"{stats.compressions_applied} compressions applied")


# ---------------------------------------------------------------------------
# MicroCompactProcessor — lighter, turn-by-turn compaction
# ---------------------------------------------------------------------------

def micro_compact_example(model_cfg: ModelConfig) -> ContextEngine:
    from openjiuwen.core.context_engine import MicroCompactProcessor

    return ContextEngine(
        config=ContextEngineConfig(token_limit=8_000),
        processors=[MicroCompactProcessor()],  # compact after every N turns
    )


if __name__ == "__main__":
    asyncio.run(main())

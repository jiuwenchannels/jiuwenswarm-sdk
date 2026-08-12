"""workflow_dag.py — build and run a multi-step DAG workflow.

Shows:
  - Linear pipeline: two LLM steps chained
  - Conditional branch: route based on a runtime condition
  - Streaming the workflow output token by token
  - Printing the Mermaid diagram for any workflow

Run:
    python examples/workflow_dag.py
"""

import asyncio

from openjiuwen.sdk import LLMNode, ModelConfig, Workflow
from openjiuwen.sdk.workflow import ConditionNode


# ---------------------------------------------------------------------------
# Example 1 — linear pipeline
# ---------------------------------------------------------------------------

async def linear_pipeline() -> None:
    model = ModelConfig.from_env()

    wf = (
        Workflow.create("summarise-and-translate", model=model)
        .add_node("summarise", LLMNode("Summarise the following text in one sentence: {input}"))
        .add_node("translate",  LLMNode("Translate to Spanish: {summarise}"))
        .connect("summarise", "translate")
    )

    print("=== Linear pipeline ===")
    print(wf.draw())
    print()

    result = await wf.run({"input": "Distributed systems must balance consistency, availability, and partition tolerance according to the CAP theorem."})
    print("Output:", result.output)
    print("State: ", result.state)


# ---------------------------------------------------------------------------
# Example 2 — conditional branch
# ---------------------------------------------------------------------------

async def conditional_branch() -> None:
    model = ModelConfig.from_env()

    # The condition reads from the workflow's runtime context.
    # In this toy example we use a simple closure variable.
    is_long_input = False

    def length_check() -> bool:
        return is_long_input

    wf = (
        Workflow.create("branch-demo", model=model)
        .add_node("analyse",    LLMNode("Analyse the sentiment of: {input}"))
        .add_node("summarise",  LLMNode("Summarise (long): {analyse}"))
        .add_node("shorten",    LLMNode("Make shorter (short): {analyse}"))
        .connect("analyse", "summarise")
        .connect("analyse", "shorten")
        .branch("analyse", length_check, true_target="summarise", false_target="shorten")
    )

    print("=== Conditional branch ===")
    print(wf.draw())
    print()

    result = await wf.run({"input": "I love this product!"})
    print("Output:", result.output)


# ---------------------------------------------------------------------------
# Example 3 — streaming
# ---------------------------------------------------------------------------

async def streaming_workflow() -> None:
    model = ModelConfig.from_env()

    wf = (
        Workflow.create("stream-demo", model=model)
        .add_node("generate", LLMNode("Write a haiku about {input}"))
    )

    print("=== Streaming workflow ===")
    async for chunk in wf.stream({"input": "clouds"}):
        text = chunk.get("text", "")
        if text:
            print(text, end="", flush=True)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    await linear_pipeline()
    print()
    await conditional_branch()
    print()
    await streaming_workflow()


if __name__ == "__main__":
    asyncio.run(main())

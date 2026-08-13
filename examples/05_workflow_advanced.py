"""05_workflow_advanced.py — DAG workflow with components, branches, and loops.

Corresponds to §5 of the usage examples.

Shows:
  - LLMComponent, BranchComponent, Condition
  - LoopComponent iterating over a list variable
  - workflow.create_session() + workflow.run()

Run:
    python examples/05_workflow_advanced.py
"""

import asyncio
from openjiuwen.sdk import Workflow, ModelConfig
from openjiuwen.sdk.workflow import (
    Start, End,
    LLMComponent, ToolComponent,
    BranchComponent, Condition,
)


async def main():
    # Define components
    start = Start()
    classify = LLMComponent(
        name="classify",
        prompt="Classify this text as 'technical' or 'general': {{input}}",
        output_var="category",
    )
    technical_answer = LLMComponent(
        name="technical_answer",
        prompt="Give a detailed technical explanation of: {{input}}",
    )
    simple_answer = LLMComponent(
        name="simple_answer",
        prompt="Explain in simple terms: {{input}}",
    )
    branch = BranchComponent(
        name="route",
        conditions=[
            Condition(expression="category == 'technical'", target="technical_answer"),
        ],
        default_target="simple_answer",
    )
    end = End()

    # Wire the DAG
    workflow = Workflow(
        name="adaptive-qa",
        components=[start, classify, branch, technical_answer, simple_answer, end],
        edges=[
            (start, classify),
            (classify, branch),
            (branch, technical_answer),
            (branch, simple_answer),
            (technical_answer, end),
            (simple_answer, end),
        ],
        model=ModelConfig.from_env(),
    )

    session = await workflow.create_session()
    result = await workflow.run(session, input="What is a garbage collector?")
    print(result.text)


# ---------------------------------------------------------------------------
# Loop example (summarise a list of URLs one by one)
# ---------------------------------------------------------------------------

def loop_example():
    """Demonstrates LoopComponent — not executed here, shown for reference."""
    from openjiuwen.sdk.workflow import LoopComponent

    loop = LoopComponent(
        name="summarise_urls",
        iterate_over="urls",        # variable containing a list
        item_var="url",
        body=[
            LLMComponent(
                name="summarise",
                prompt="Summarise the content at {{url}} in one sentence.",
            )
        ],
        collect_output_as="summaries",
    )
    return loop


if __name__ == "__main__":
    asyncio.run(main())

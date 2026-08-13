"""09_swarmflow.py — structured multi-agent orchestration with parallel, pipeline, phase.

Corresponds to §9 of the usage examples.

Shows:
  - parallel() to fan-out work across multiple agents simultaneously
  - pipeline() to chain agents sequentially (each output feeds next)
  - phase() for structured multi-phase execution
  - run_swarmflow() entry point
  - Inspecting per-phase activity records

Run:
    python examples/09_swarmflow.py
"""

import asyncio
from openjiuwen.sdk.swarmflow import run_swarmflow, agent, parallel, pipeline, phase


# Define a SwarmFlow script as a Python module (can also be inline)
META = {
    "name": "research-and-publish",
    "description": "Research a topic, write an article, then proofread it.",
}


async def run(args: dict) -> str:
    topic = args["topic"]

    # Phase 1: parallel research across three angles
    research_results = await parallel(
        agent("researcher", f"Research economic impacts of {topic}"),
        agent("researcher", f"Research environmental impacts of {topic}"),
        agent("researcher", f"Research social impacts of {topic}"),
    )

    # Phase 2: combine into a draft (sequential)
    draft = await pipeline(
        agent("writer", f"Write a 600-word article on {topic} using: {research_results}"),
        agent("editor", "Improve flow and clarity of the draft."),
    )

    # Phase 3: final checks in parallel
    await parallel(
        agent("fact-checker", f"Verify all claims in: {draft}"),
        agent("proofreader", f"Fix grammar and spelling in: {draft}"),
    )

    return draft


async def main():
    result = await run_swarmflow(
        script=run,
        args={"topic": "large language models"},
        meta=META,
    )
    print(result.final_output)
    # Inspect execution timeline
    for phase_record in result.phases:
        print(f"  Phase {phase_record.index}: {len(phase_record.activities)} activities")


if __name__ == "__main__":
    asyncio.run(main())

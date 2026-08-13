"""18_sub_workflow.py — embed one workflow inside another (sub-workflow composition).

Corresponds to §18 of the usage examples.

Shows:
  - SubWorkflowComponent wrapping a reusable inner workflow
  - input_mapping and output_mapping between outer and inner workflow variables
  - Outer workflow calling the sub-workflow as a single step

Run:
    python examples/18_sub_workflow.py
"""

import asyncio
from openjiuwen.sdk import Workflow, ModelConfig
from openjiuwen.sdk.workflow import (
    Start, End, LLMComponent, SubWorkflowComponent,
)


async def main():
    model_cfg = ModelConfig.from_env()

    # --- Reusable inner workflow: translate + proofread ---
    translate = LLMComponent(
        name="translate",
        prompt="Translate the following to French: {{text}}",
        output_var="translated",
    )
    proofread = LLMComponent(
        name="proofread",
        prompt="Fix any grammar errors in: {{translated}}",
        output_var="proofread_text",
    )
    translation_pipeline = Workflow(
        name="translate-and-proofread",
        components=[Start(), translate, proofread, End()],
        edges=[(Start(), translate), (translate, proofread), (proofread, End())],
        model=model_cfg,
    )

    # --- Outer workflow that calls the inner one ---
    summarise = LLMComponent(
        name="summarise",
        prompt="Summarise this article in 3 sentences: {{input}}",
        output_var="text",
    )
    translate_sub = SubWorkflowComponent(
        name="translate_summary",
        workflow=translation_pipeline,
        input_mapping={"text": "text"},          # outer var → inner input
        output_mapping={"proofread_text": "final"},
    )
    outer = Workflow(
        name="summarise-and-translate",
        components=[Start(), summarise, translate_sub, End()],
        edges=[
            (Start(), summarise),
            (summarise, translate_sub),
            (translate_sub, End()),
        ],
        model=model_cfg,
    )

    session = await outer.create_session()
    result = await outer.run(session, input="[long English article text here]")
    print(result.text)   # French, proofread summary


if __name__ == "__main__":
    asyncio.run(main())

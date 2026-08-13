"""20_prompt_builder.py — iterate on system prompts using feedback and bad-case examples.

Corresponds to §20 of the usage examples.

Shows:
  - MetaTemplateBuilder: generate a prompt from intent + examples
  - FeedbackPromptBuilder: refine a prompt using observed bad cases
  - The generated/refined prompts can be passed directly to Agent.create(system_prompt=...)

Run:
    python examples/20_prompt_builder.py
"""

import asyncio
from openjiuwen.sdk.prompt import MetaTemplateBuilder, FeedbackPromptBuilder


async def meta_template_example():
    """Generate an initial system prompt from a rough intent."""
    builder = MetaTemplateBuilder(
        intent="Answer customer support questions concisely and politely.",
        examples=[
            {"input": "Where is my order?",  "ideal": "I can look that up — please share your order ID."},
            {"input": "I want a refund.",     "ideal": "I'm sorry to hear that. Refunds take 3–5 business days."},
        ],
    )
    template_v1 = await builder.build()
    print("Generated prompt:\n", template_v1)
    return template_v1


async def feedback_refine_example():
    """Refine an existing prompt using cases where the agent responded poorly."""
    bad_cases = [
        {
            "input": "My package arrived broken.",
            "bad_response": "That sucks.",
            "reason": "Too informal; no action offered.",
        },
    ]

    builder = FeedbackPromptBuilder(
        current_prompt="You are a helpful support agent.",
        bad_cases=bad_cases,
    )
    improved_prompt = await builder.refine()
    print("Improved prompt:\n", improved_prompt)
    return improved_prompt


async def main():
    print("=== Meta template ===")
    prompt = await meta_template_example()

    print("\n=== Feedback refinement ===")
    await feedback_refine_example()

    # Use the generated prompt in an agent
    from openjiuwen.sdk import Agent, ModelConfig
    agent = await Agent.create(
        "support-bot",
        model=ModelConfig.from_env(),
        system_prompt=prompt,
    )
    result = await agent.run("Where is my order?")
    print("\nAgent response:", result.text)


if __name__ == "__main__":
    asyncio.run(main())

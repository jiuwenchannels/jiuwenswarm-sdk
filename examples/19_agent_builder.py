"""19_agent_builder.py — programmatic agent construction from config objects.

Corresponds to §19 of the usage examples.

Shows:
  - LlmAgentBuilder with fluent API: name, system_prompt, model, temperature, tools
  - builder.build() → Agent
  - WorkflowBuilder for wrapping a DAG behind the Agent interface

Run:
    python examples/19_agent_builder.py
"""

import asyncio
from openjiuwen.sdk.builder import AgentBuilder, LlmAgentBuilder


async def main():
    # Build a plain LLM agent
    agent = (
        LlmAgentBuilder()
        .name("support-bot")
        .system_prompt("You are a helpful customer support agent for Acme Corp.")
        .model("gpt-4o")
        .temperature(0.3)
        .max_turns(20)
        .tool("fetch_url")       # reference a registered tool by name
        .tool("word_count")
        .build()
    )
    await agent.init()
    result = await agent.run("How do I reset my password?")
    print(result.text)


# ---------------------------------------------------------------------------
# WorkflowBuilder — wraps a Workflow behind the Agent interface
# ---------------------------------------------------------------------------

def workflow_agent_example():
    from openjiuwen.sdk.builder import WorkflowBuilder
    from openjiuwen.sdk.workflow import LLMComponent, Start, End

    agent = (
        WorkflowBuilder()
        .name("qa-workflow-agent")
        .add_component(Start())
        .add_component(LLMComponent(name="answer", prompt="Answer: {{input}}"))
        .add_component(End())
        .add_edge(Start(), "answer")
        .add_edge("answer", End())
        .build()
    )
    return agent


if __name__ == "__main__":
    asyncio.run(main())

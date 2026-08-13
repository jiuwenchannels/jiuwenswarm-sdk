"""Unit tests for openjiuwen.sdk.builder — AgentBuilder, LlmAgentBuilder, etc."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.builder import (
    AgentBuilder,
    LlmAgentBuilder,
    PromptBuilder,
    WorkflowBuilder,
    _BuiltAgent,
    _BuiltWorkflowAgent,
)


# ---------------------------------------------------------------------------
# AgentBuilder tests
# ---------------------------------------------------------------------------


def test_agent_builder_fluent_api():
    builder = (
        AgentBuilder("test-agent")
        .with_system_prompt("You are a test agent.")
    )
    assert builder._name == "test-agent"
    assert builder._system_prompt == "You are a test agent."


def test_agent_builder_returns_built_agent():
    built = AgentBuilder("my-agent").build()
    assert isinstance(built, _BuiltAgent)


def test_agent_builder_with_tools():
    builder = AgentBuilder().with_tools(["tool_a", "tool_b"])
    assert builder._tools == ["tool_a", "tool_b"]


def test_agent_builder_with_workspace():
    ws = object()
    builder = AgentBuilder().with_workspace(ws)
    assert builder._workspace is ws


def test_agent_builder_with_memory():
    builder = AgentBuilder().with_memory("user", user_id="u123")
    assert builder._memory_scope == "user"


def test_agent_builder_with_knowledge_bases():
    builder = AgentBuilder().with_knowledge_bases(["kb1", "kb2"])
    assert len(builder._knowledge_bases) == 2


# ---------------------------------------------------------------------------
# LlmAgentBuilder tests
# ---------------------------------------------------------------------------


def test_llm_agent_builder_defaults():
    builder = LlmAgentBuilder()
    assert builder._name == "agent"
    assert builder._model_name == "gpt-4o"


def test_llm_agent_builder_fluent():
    builder = (
        LlmAgentBuilder()
        .name("research-agent")
        .system_prompt("You are a researcher.")
        .model("gpt-4o-mini")
        .temperature(0.7)
        .max_turns(20)
        .tool("web_search")
    )
    assert builder._name == "research-agent"
    assert builder._system_prompt == "You are a researcher."
    assert builder._model_name == "gpt-4o-mini"
    assert builder._temperature == 0.7
    assert builder._max_turns == 20
    assert "web_search" in builder._tool_names


def test_llm_agent_builder_tool_obj():
    class FakeTool:
        pass

    tool = FakeTool()
    builder = LlmAgentBuilder().tool(tool)
    assert tool in builder._sdk_tools


def test_llm_agent_builder_build_returns_built_agent():
    from openjiuwen.sdk.config import ModelConfig

    built = (
        LlmAgentBuilder()
        .name("bot")
        .with_model_config(ModelConfig(model="gpt-4o", api_key="key"))
        .build()
    )
    assert isinstance(built, _BuiltAgent)
    assert repr(built).startswith("_BuiltAgent")


def test_llm_agent_builder_with_hooks():
    hooks = object()
    builder = LlmAgentBuilder().with_hooks(hooks)
    assert builder._hooks is hooks


def test_llm_agent_builder_with_workspace():
    ws = object()
    builder = LlmAgentBuilder().with_workspace(ws)
    assert builder._workspace is ws


# ---------------------------------------------------------------------------
# WorkflowBuilder tests
# ---------------------------------------------------------------------------


def test_workflow_builder_name():
    builder = WorkflowBuilder().name("my-workflow")
    assert builder._name == "my-workflow"


def test_workflow_builder_add_component():
    comp = object()
    builder = WorkflowBuilder().add_component(comp)
    assert comp in builder._components


def test_workflow_builder_add_edge():
    builder = WorkflowBuilder().add_edge("start", "end")
    assert ("start", "end") in builder._edges


def test_workflow_builder_build_returns_built_workflow():
    built = WorkflowBuilder().name("test").build()
    assert isinstance(built, _BuiltWorkflowAgent)
    assert repr(built).startswith("_BuiltWorkflowAgent")


# ---------------------------------------------------------------------------
# PromptBuilder tests
# ---------------------------------------------------------------------------


def test_prompt_builder_user_message():
    pb = PromptBuilder().user("What is 2+2?")
    result = pb.build()
    assert "[USER] What is 2+2?" in result


def test_prompt_builder_system_message():
    pb = PromptBuilder().system("You are helpful.").user("Hello")
    result = pb.build()
    assert "[SYSTEM] You are helpful." in result
    assert "[USER] Hello" in result


def test_prompt_builder_assistant_message():
    pb = PromptBuilder().user("Q").assistant("A")
    result = pb.build()
    assert "[USER] Q" in result
    assert "[ASSISTANT] A" in result


def test_prompt_builder_few_shot():
    pb = PromptBuilder().few_shot([
        ("What is 2+2?", "4"),
        ("What is 3+3?", "6"),
    ])
    result = pb.build()
    assert "[USER] What is 2+2?" in result
    assert "[ASSISTANT] 4" in result
    assert "[USER] What is 3+3?" in result
    assert "[ASSISTANT] 6" in result


def test_prompt_builder_build_messages():
    pb = (
        PromptBuilder()
        .system("System prompt")
        .user("User question")
    )
    messages = pb.build_messages()
    assert messages[0] == {"role": "system", "content": "System prompt"}
    assert messages[1] == {"role": "user", "content": "User question"}


def test_prompt_builder_system_prepends():
    """system() should insert at position 0 even if called after user()."""
    pb = PromptBuilder().user("Hello").system("Be concise.")
    messages = pb.build_messages()
    assert messages[0]["role"] == "system"


def test_prompt_builder_empty_build():
    pb = PromptBuilder()
    assert pb.build() == ""
    assert pb.build_messages() == []


# ---------------------------------------------------------------------------
# _BuiltAgent tests
# ---------------------------------------------------------------------------


def test_built_agent_run_before_init_raises():
    built = AgentBuilder("a").build()

    with pytest.raises(RuntimeError, match="not initialised"):
        import asyncio
        asyncio.get_event_loop().run_until_complete(built.run("hello"))


def test_built_agent_repr():
    built = AgentBuilder("my-agent").build()
    rep = repr(built)
    assert "my-agent" in rep
    assert "initialised=False" in rep

"""SDK Builder façade — fluent builder API for agents and prompts.

Quick start::

    from openjiuwen.sdk.builder import LlmAgentBuilder, PromptBuilder

    agent = (
        LlmAgentBuilder()
        .name("support-bot")
        .system_prompt("You are a helpful support agent.")
        .model("gpt-4o")
        .temperature(0.3)
        .build()
    )
    await agent.init()
    result = await agent.run("How do I reset my password?")
    print(result.text)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openjiuwen.sdk.agent import Agent
    from openjiuwen.sdk.config import ModelConfig
    from openjiuwen.sdk.hooks import Hooks
    from openjiuwen.sdk.tools import SdkTool


# ---------------------------------------------------------------------------
# AgentBuilder — generic fluent builder (roadmap API)
# ---------------------------------------------------------------------------


class AgentBuilder:
    """Generic fluent builder for :class:`~openjiuwen.sdk.agent.Agent` instances.

    Example::

        agent = (
            AgentBuilder("assistant")
            .with_model(ModelConfig.from_env())
            .with_tools([my_tool])
            .with_hooks(hooks)
            .with_memory(MemoryScope.USER)
            .build()
        )
        await agent.init()
    """

    def __init__(self, name: str = "agent") -> None:
        self._name = name
        self._model_cfg: Any = None
        self._tools: list[Any] = []
        self._hooks: Any = None
        self._memory_scope: Any = None
        self._system_prompt: str | None = None
        self._workspace: Any = None
        self._knowledge_bases: list[Any] = []

    def with_model(self, model: "ModelConfig") -> "AgentBuilder":
        """Set the LLM configuration."""
        self._model_cfg = model
        return self

    def with_tools(self, tools: list["SdkTool"]) -> "AgentBuilder":
        """Set the tool list."""
        self._tools = list(tools)
        return self

    def with_hooks(self, hooks: "Hooks") -> "AgentBuilder":
        """Set lifecycle hooks."""
        self._hooks = hooks
        return self

    def with_memory(self, scope: Any, *, user_id: str | None = None) -> "AgentBuilder":
        """Set a memory scope."""
        self._memory_scope = scope
        return self

    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        """Set the system prompt."""
        self._system_prompt = prompt
        return self

    def with_workspace(self, workspace: Any) -> "AgentBuilder":
        """Set the workspace."""
        self._workspace = workspace
        return self

    def with_knowledge_bases(self, kbs: list[Any]) -> "AgentBuilder":
        """Set knowledge bases for RAG."""
        self._knowledge_bases = list(kbs)
        return self

    def build(self) -> "_BuiltAgent":
        """Return a :class:`_BuiltAgent` ready to be initialised with :meth:`_BuiltAgent.init`."""
        return _BuiltAgent(
            name=self._name,
            model_cfg=self._model_cfg,
            tools=self._tools,
            hooks=self._hooks,
            system_prompt=self._system_prompt,
            workspace=self._workspace,
            knowledge_bases=self._knowledge_bases,
        )


# ---------------------------------------------------------------------------
# LlmAgentBuilder — LLM-specific fluent builder (matches examples)
# ---------------------------------------------------------------------------


class LlmAgentBuilder:
    """Fluent builder for LLM agents.

    Example::

        agent = (
            LlmAgentBuilder()
            .name("researcher")
            .system_prompt("You are an expert researcher.")
            .model("gpt-4o")
            .temperature(0.7)
            .max_turns(30)
            .tool("web_search")
            .build()
        )
        await agent.init()
    """

    def __init__(self) -> None:
        self._name: str = "agent"
        self._system_prompt: str | None = None
        self._model_name: str = "gpt-4o"
        self._temperature: float | None = None
        self._max_turns: int | None = None
        self._tool_names: list[str] = []
        self._sdk_tools: list[Any] = []
        self._hooks: Any = None
        self._workspace: Any = None
        self._model_cfg: Any = None

    def name(self, name: str) -> "LlmAgentBuilder":
        """Set the agent name."""
        self._name = name
        return self

    def system_prompt(self, prompt: str) -> "LlmAgentBuilder":
        """Set the system prompt."""
        self._system_prompt = prompt
        return self

    def model(self, model_name: str) -> "LlmAgentBuilder":
        """Set the model name (e.g. ``"gpt-4o"``)."""
        self._model_name = model_name
        return self

    def temperature(self, temp: float) -> "LlmAgentBuilder":
        """Set the sampling temperature."""
        self._temperature = temp
        return self

    def max_turns(self, n: int) -> "LlmAgentBuilder":
        """Set the maximum task-loop turns."""
        self._max_turns = n
        return self

    def tool(self, tool_name_or_obj: "str | SdkTool") -> "LlmAgentBuilder":
        """Register a tool by name or :class:`~openjiuwen.sdk.tools.SdkTool` object."""
        if isinstance(tool_name_or_obj, str):
            self._tool_names.append(tool_name_or_obj)
        else:
            self._sdk_tools.append(tool_name_or_obj)
        return self

    def with_hooks(self, hooks: Any) -> "LlmAgentBuilder":
        """Set lifecycle hooks."""
        self._hooks = hooks
        return self

    def with_workspace(self, workspace: Any) -> "LlmAgentBuilder":
        """Set the workspace."""
        self._workspace = workspace
        return self

    def with_model_config(self, model_cfg: "ModelConfig") -> "LlmAgentBuilder":
        """Set a full :class:`~openjiuwen.sdk.config.ModelConfig` (overrides :meth:`model`)."""
        self._model_cfg = model_cfg
        return self

    def build(self) -> "_BuiltAgent":
        """Return a :class:`_BuiltAgent` ready to be initialised."""
        from openjiuwen.sdk.config import ModelConfig

        if self._model_cfg is None:
            self._model_cfg = ModelConfig(
                model=self._model_name,
                temperature=self._temperature,
            )
        return _BuiltAgent(
            name=self._name,
            model_cfg=self._model_cfg,
            tools=self._sdk_tools,
            hooks=self._hooks,
            system_prompt=self._system_prompt,
            workspace=self._workspace,
            knowledge_bases=[],
        )


# ---------------------------------------------------------------------------
# WorkflowBuilder — wraps a Workflow behind the Agent interface
# ---------------------------------------------------------------------------


class WorkflowBuilder:
    """Fluent builder for workflow-backed agents.

    Example::

        agent = (
            WorkflowBuilder()
            .name("qa-workflow")
            .add_component(Start())
            .add_component(LLMComponent(name="answer", prompt="Answer: {{input}}"))
            .add_component(End())
            .add_edge(Start(), "answer")
            .add_edge("answer", End())
            .build()
        )
    """

    def __init__(self) -> None:
        self._name: str = "workflow-agent"
        self._components: list[Any] = []
        self._edges: list[tuple[Any, Any]] = []
        self._model_cfg: Any = None

    def name(self, name: str) -> "WorkflowBuilder":
        self._name = name
        return self

    def with_model_config(self, model_cfg: Any) -> "WorkflowBuilder":
        self._model_cfg = model_cfg
        return self

    def add_component(self, component: Any) -> "WorkflowBuilder":
        """Add a workflow component node."""
        self._components.append(component)
        return self

    def add_edge(self, src: Any, dst: Any) -> "WorkflowBuilder":
        """Add a directed edge from *src* to *dst*."""
        self._edges.append((src, dst))
        return self

    def build(self) -> "_BuiltWorkflowAgent":
        return _BuiltWorkflowAgent(
            name=self._name,
            components=self._components,
            edges=self._edges,
            model_cfg=self._model_cfg,
        )


# ---------------------------------------------------------------------------
# PromptBuilder — fluent builder for structured prompts
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Fluent builder for structured LLM prompts.

    Example::

        prompt = (
            PromptBuilder()
            .system("You are a helpful assistant.")
            .user("What is the capital of France?")
            .few_shot([
                ("What is 2+2?", "4"),
                ("What is 3+3?", "6"),
            ])
            .build()
        )
        print(prompt)
    """

    def __init__(self) -> None:
        self._parts: list[dict[str, str]] = []

    def system(self, text: str) -> "PromptBuilder":
        """Prepend a system message."""
        self._parts.insert(0, {"role": "system", "content": text})
        return self

    def user(self, text: str) -> "PromptBuilder":
        """Append a user message."""
        self._parts.append({"role": "user", "content": text})
        return self

    def assistant(self, text: str) -> "PromptBuilder":
        """Append an assistant turn."""
        self._parts.append({"role": "assistant", "content": text})
        return self

    def few_shot(self, examples: list[tuple[str, str]]) -> "PromptBuilder":
        """Append a list of (user, assistant) few-shot examples."""
        for user_text, asst_text in examples:
            self._parts.append({"role": "user", "content": user_text})
            self._parts.append({"role": "assistant", "content": asst_text})
        return self

    def build(self) -> str:
        """Return the prompt as a formatted string.

        Returns:
            A newline-separated prompt string with role labels.
        """
        lines: list[str] = []
        for part in self._parts:
            role = part["role"].upper()
            content = part["content"]
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    def build_messages(self) -> list[dict[str, str]]:
        """Return the prompt as a list of message dicts (OpenAI format)."""
        return list(self._parts)


# ---------------------------------------------------------------------------
# Internal: BuiltAgent (returned by builder.build())
# ---------------------------------------------------------------------------


class _BuiltAgent:
    """An agent configuration assembled by a builder.

    Call :meth:`init` (async) before calling :meth:`run`.
    """

    def __init__(
        self,
        name: str,
        model_cfg: Any,
        tools: list[Any],
        hooks: Any,
        system_prompt: str | None,
        workspace: Any,
        knowledge_bases: list[Any],
    ) -> None:
        self._name = name
        self._model_cfg = model_cfg
        self._tools = tools
        self._hooks = hooks
        self._system_prompt = system_prompt
        self._workspace = workspace
        self._knowledge_bases = knowledge_bases
        self._agent: Any = None

    async def init(self) -> None:
        """Initialise the underlying agent (async).  Must be called before :meth:`run`."""
        from openjiuwen.sdk.agent import Agent
        from openjiuwen.sdk.config import ModelConfig

        model = self._model_cfg if self._model_cfg is not None else ModelConfig.from_env()
        self._agent = await Agent.create(
            self._name,
            model=model,
            tools=self._tools or [],
            hooks=self._hooks,
            system_prompt=self._system_prompt,
            workspace=self._workspace,
            knowledge_bases=self._knowledge_bases or [],
        )

    async def run(self, prompt: str, **kwargs: Any) -> Any:
        """Run the agent.  :meth:`init` must have been called first."""
        if self._agent is None:
            raise RuntimeError(
                "Agent not initialised.  Call await agent.init() before agent.run()."
            )
        return await self._agent.run(prompt, **kwargs)

    def on(self, event: str, callback: Any) -> None:
        if self._agent is not None:
            self._agent.on(event, callback)

    def __repr__(self) -> str:
        return f"_BuiltAgent(name={self._name!r}, initialised={self._agent is not None})"


class _BuiltWorkflowAgent:
    """A workflow-backed agent assembled by :class:`WorkflowBuilder`."""

    def __init__(
        self,
        name: str,
        components: list[Any],
        edges: list[tuple[Any, Any]],
        model_cfg: Any,
    ) -> None:
        self._name = name
        self._components = components
        self._edges = edges
        self._model_cfg = model_cfg

    async def init(self) -> None:
        """No-op for workflow agents; the workflow is compiled on first run."""

    async def run(self, prompt: str, **kwargs: Any) -> Any:
        """Run the workflow with *prompt* as the ``input`` variable."""
        from openjiuwen.sdk.agent import AgentResult

        # Build a simple workflow and run it
        from openjiuwen.sdk.workflow import Workflow, LLMNode
        from openjiuwen.sdk.config import ModelConfig

        model = self._model_cfg or ModelConfig.from_env()
        wf = Workflow.create(self._name, model=model)
        if not self._components:
            wf.add_node("main", LLMNode(prompt_template="{input}"))
        result = await wf.run({"input": prompt})
        return AgentResult(text=str(result.output), session_id=result.session_id)

    def __repr__(self) -> str:
        return f"_BuiltWorkflowAgent(name={self._name!r})"

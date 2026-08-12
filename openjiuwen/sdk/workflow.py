"""Workflow facade — DAG-based multi-step orchestration.

Build a directed acyclic graph of LLM, tool, and branching steps, then run it
end-to-end or stream its output token by token.

Quick start::

    from openjiuwen.sdk import Workflow, LLMNode, ModelConfig

    wf = Workflow.create("summarise", model=ModelConfig.from_env())
    wf.add_node("summarise", LLMNode("Summarise this text: {input}"))
    wf.add_node("translate", LLMNode("Translate to Spanish: {summarise}"))
    wf.connect("summarise", "translate")
    result = await wf.run({"input": "Long article text..."})
    print(result.output)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable

from openjiuwen.sdk.errors import SdkError

if TYPE_CHECKING:
    from openjiuwen.sdk.config import ModelConfig
    from openjiuwen.sdk.tools import SdkTool

# Keep workflow_bridge importable without the runtime.
from openjiuwen.sdk._internal import workflow_bridge as _wb


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class WorkflowError(SdkError):
    """Raised when a workflow build or run fails."""


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


@dataclass
class WorkflowNode:
    """Abstract base for SDK workflow nodes. Do not instantiate directly."""


@dataclass
class LLMNode(WorkflowNode):
    """An LLM inference step.

    Args:
        prompt_template: Jinja/f-string template; use ``{node_id}`` to
            reference a previous node's output, ``{input}`` for the workflow
            input dict value named ``input``.
        name:            Optional display name (defaults to node ID).
        max_tokens:      Cap on generated tokens for this step.
    """

    prompt_template: str
    name: str | None = None
    max_tokens: int | None = None


@dataclass
class ToolNode(WorkflowNode):
    """A tool-call step.

    Args:
        tool:  An :class:`~openjiuwen.sdk.tools.SdkTool` instance (from
               ``@tool``).
        name:  Optional display name (defaults to node ID).
    """

    tool: "SdkTool"
    name: str | None = None


@dataclass
class ConditionNode(WorkflowNode):
    """A branching step evaluated at runtime.

    Args:
        condition:    Callable ``() -> bool``; receives no arguments (read
                      workflow state from closure if needed).
        true_target:  Node ID to route to when condition is True.
        false_target: Node ID to route to when condition is False.
        name:         Optional display name.
    """

    condition: Callable[[], bool]
    true_target: str
    false_target: str
    name: str | None = None


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class WorkflowResult:
    """Outcome of a synchronous workflow run."""

    output: dict[str, Any]
    state: str  # "completed" | "input_required" | "error"
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Workflow facade
# ---------------------------------------------------------------------------


class Workflow:
    """Fluent builder + executor for JiuwenSwarm DAG workflows.

    Create an instance via :meth:`create`, add nodes, connect them, then
    call :meth:`run` (blocking) or :meth:`stream` (async generator).

    Example::

        wf = Workflow.create("pipeline", model=ModelConfig(api_key="sk-…"))
        wf.add_node("step1", LLMNode("Summarise: {input}"))
        wf.add_node("step2", LLMNode("Translate to French: {step1}"))
        wf.connect("step1", "step2")
        result = await wf.run({"input": "Hello world"})
        print(result.output)
    """

    def __init__(self, name: str, *, workflow_id: str | None = None) -> None:
        self._name = name
        self._workflow_id = workflow_id or f"wf-{uuid.uuid4().hex[:8]}"
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: list[tuple[str, str]] = []
        self._conditional_edges: list[tuple[str, Callable[[], bool], str, str]] = []
        self._model_cfg: "ModelConfig | None" = None
        self._runtime_wf: Any = None  # compiled once on first run

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        *,
        model: "ModelConfig | None" = None,
        workflow_id: str | None = None,
    ) -> "Workflow":
        """Create a new Workflow.

        Args:
            name:        Human-readable workflow name.
            model:       LLM config used for :class:`LLMNode` steps.
                         Falls back to :meth:`ModelConfig.from_env` when
                         omitted.
            workflow_id: Optional stable ID; auto-generated if omitted.
        """
        wf = cls(name, workflow_id=workflow_id)
        if model is not None:
            wf._model_cfg = model
        else:
            from openjiuwen.sdk.config import ModelConfig

            wf._model_cfg = ModelConfig.from_env()
        return wf

    # ------------------------------------------------------------------
    # Builder API
    # ------------------------------------------------------------------

    def add_node(self, node_id: str, node: WorkflowNode) -> "Workflow":
        """Add a node to the graph. Returns ``self`` for chaining."""
        if not isinstance(node, WorkflowNode):
            raise TypeError(f"Expected WorkflowNode, got {type(node).__name__}")
        if node_id in self._nodes:
            raise WorkflowError(f"Node '{node_id}' already exists.")
        self._nodes[node_id] = node
        self._runtime_wf = None  # invalidate compiled graph
        return self

    def connect(self, src: str, dst: str) -> "Workflow":
        """Add a directed data-flow edge from *src* to *dst*. Returns ``self``."""
        self._edges.append((src, dst))
        self._runtime_wf = None
        return self

    def branch(
        self,
        src: str,
        condition: Callable[[], bool],
        *,
        true_target: str,
        false_target: str,
    ) -> "Workflow":
        """Add a conditional edge from *src*. Returns ``self``."""
        self._conditional_edges.append((src, condition, true_target, false_target))
        self._runtime_wf = None
        return self

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _compile(self) -> Any:
        if self._runtime_wf is not None:
            return self._runtime_wf
        try:
            self._runtime_wf = _wb.build_runtime_workflow(
                workflow_id=self._workflow_id,
                name=self._name,
                description="",
                nodes=self._nodes,
                edges=self._edges,
                conditional_edges=self._conditional_edges,
                model_cfg=self._model_cfg,
            )
        except Exception as exc:
            raise WorkflowError(f"Failed to compile workflow '{self._name}': {exc}") from exc
        return self._runtime_wf

    async def run(self, inputs: dict[str, Any]) -> WorkflowResult:
        """Execute the workflow and return the final output.

        Args:
            inputs: Key-value dict passed to the workflow's start node.

        Returns:
            :class:`WorkflowResult` with ``output`` and ``state``.
        """
        rt_wf = self._compile()
        try:
            output, state = await _wb.run_workflow(rt_wf, inputs)
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError(f"Workflow '{self._name}' failed: {exc}") from exc
        return WorkflowResult(
            output=output,
            state=state,
            session_id=self._workflow_id,
        )

    async def stream(self, inputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """Stream workflow output, yielding one chunk dict per token/event.

        Args:
            inputs: Key-value dict passed to the workflow's start node.

        Yields:
            Dicts with at least one of ``"text"``, ``"data"``, or ``"chunk"``
            keys.
        """
        rt_wf = self._compile()
        try:
            async for chunk in _wb.stream_workflow(rt_wf, inputs):
                yield chunk
        except WorkflowError:
            raise
        except Exception as exc:
            raise WorkflowError(f"Streaming workflow '{self._name}' failed: {exc}") from exc

    def draw(self) -> str:
        """Return a Mermaid diagram string for this workflow.

        The diagram only reflects nodes/edges registered via :meth:`add_node`
        and :meth:`connect`. Conditional branches are shown as dashed lines.
        """
        lines = ["graph TD", f"    __start__([Start]) --> {next(iter(self._nodes), '__end__')}"]
        for src, dst in self._edges:
            lines.append(f"    {src} --> {dst}")
        for src, _, true_tgt, false_tgt in self._conditional_edges:
            lines.append(f"    {src} -->|true| {true_tgt}")
            lines.append(f"    {src} -.->|false| {false_tgt}")
        last = list(self._nodes)[-1] if self._nodes else "__start__"
        lines.append(f"    {last} --> __end__([End])")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Workflow(name={self._name!r}, nodes={list(self._nodes)!r})"

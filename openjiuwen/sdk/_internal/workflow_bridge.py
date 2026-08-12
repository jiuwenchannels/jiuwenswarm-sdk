"""Internal bridge between the SDK workflow facade and the runtime DAG engine.

All harness/core imports live inside functions so they are importable without
the runtime installed and patchable in unit tests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from openjiuwen.sdk.workflow import LLMNode, ToolNode, WorkflowNode

# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------


def make_workflow_card(workflow_id: str, name: str, description: str = "") -> Any:
    """Wrap WorkflowCard construction (patchable)."""
    from openjiuwen.core.workflow import WorkflowCard

    return WorkflowCard(id=workflow_id, name=name, description=description)


def create_workflow_session() -> Any:
    """Wrap create_workflow_session from core (patchable)."""
    from openjiuwen.core.workflow import create_workflow_session as _fn

    return _fn()


def build_runtime_workflow(
    workflow_id: str,
    name: str,
    description: str,
    nodes: dict[str, "WorkflowNode"],
    edges: list[tuple[str, str]],
    conditional_edges: list[tuple[str, Any, str, str]],
    model_cfg: Any,
) -> Any:
    """Construct and return a compiled runtime Workflow (patchable)."""
    from openjiuwen.core.workflow import (
        End,
        FuncCondition,
        LLMCompConfig,
        LLMComponent,
        Start,
        Workflow,
    )

    card = make_workflow_card(workflow_id, name, description)
    flow = Workflow(card=card)

    # Always inject implicit start/end if the user didn't add them
    if "__start__" not in nodes:
        flow.set_start_comp("__start__", Start())
    if "__end__" not in nodes:
        flow.set_end_comp("__end__", End())

    # Add user-defined nodes
    for node_id, node in nodes.items():
        comp = _node_to_component(node, model_cfg)
        if comp is not None:
            flow.add_workflow_comp(node_id, comp)

    # Wire edges
    # Connect __start__ to the first node that has no incoming edge
    incoming = {dst for _, dst in edges}
    source_nodes = [n for n in nodes if n not in incoming]
    for src_node in source_nodes:
        flow.add_connection("__start__", src_node)

    # Connect the last node (no outgoing) to __end__
    outgoing = {src for src, _ in edges}
    sink_nodes = [n for n in nodes if n not in outgoing and n not in {t for _, _, t, _ in conditional_edges} and n not in {f for _, _, _, f in conditional_edges}]
    for sink_node in sink_nodes:
        flow.add_connection(sink_node, "__end__")

    for src, dst in edges:
        flow.add_connection(src, dst)

    for src, condition, true_target, false_target in conditional_edges:
        from openjiuwen.core.workflow import BranchComponent

        branch = BranchComponent()
        branch.add_branch(FuncCondition(condition), true_target)
        branch.add_branch(FuncCondition(lambda: True), false_target)
        flow.add_workflow_comp(f"{src}_branch", branch)
        flow.add_connection(src, f"{src}_branch")
        flow.add_conditional_connection(f"{src}_branch", branch.router())

    return flow


def _node_to_component(node: "WorkflowNode", model_cfg: Any) -> Any:
    """Translate an SDK WorkflowNode to a runtime component."""
    # Import here to avoid runtime dep at module load
    from openjiuwen.sdk.workflow import ConditionNode, LLMNode, ToolNode

    if isinstance(node, LLMNode):
        from openjiuwen.core.workflow import LLMCompConfig, LLMComponent

        model = _build_workflow_model(model_cfg) if model_cfg is not None else None
        cfg = LLMCompConfig(model=model, prompt_template=node.prompt_template)
        return LLMComponent(config=cfg)

    if isinstance(node, ToolNode):
        from openjiuwen.core.workflow import ToolComponent, ToolComponentConfig

        cfg = ToolComponentConfig(tool_id=node.tool.name)
        return ToolComponent(config=cfg)

    return None


def _build_workflow_model(cfg: Any) -> Any:
    from openjiuwen.core.foundation.llm import init_model

    return init_model(
        provider=cfg._normalised_provider,
        model_name=cfg.model,
        api_key=cfg.api_key or "",
        api_base=cfg.api_base or "",
        temperature=cfg.temperature if cfg.temperature is not None else 0.95,
        timeout=cfg.timeout,
        max_retries=cfg.max_retries,
        max_tokens=cfg.max_tokens,
    )


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------


async def run_workflow(
    runtime_workflow: Any,
    inputs: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Invoke a compiled runtime workflow and return (output_dict, state_str)."""
    session = create_workflow_session()

    result = await runtime_workflow.invoke(inputs=inputs, session=session)

    state = "completed"
    if hasattr(result, "state"):
        state = str(result.state.value).lower() if hasattr(result.state, "value") else str(result.state).lower()

    output: dict[str, Any] = {}
    if hasattr(result, "result"):
        raw = result.result
        output = raw if isinstance(raw, dict) else {"output": raw}
    else:
        output = {"output": str(result)}

    return output, state


async def stream_workflow(
    runtime_workflow: Any,
    inputs: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """Stream a compiled runtime workflow, yielding chunk dicts."""
    session = create_workflow_session()

    async for chunk in runtime_workflow.stream(inputs=inputs, session=session):
        if hasattr(chunk, "payload"):
            yield {"text": str(chunk.payload)}
        elif hasattr(chunk, "data"):
            yield {"data": chunk.data}
        elif isinstance(chunk, dict):
            yield chunk
        else:
            yield {"chunk": str(chunk)}

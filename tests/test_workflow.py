"""Tests for openjiuwen.sdk.workflow — Workflow facade and node types."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjiuwen.sdk.workflow import (
    ConditionNode,
    LLMNode,
    ToolNode,
    Workflow,
    WorkflowError,
    WorkflowNode,
    WorkflowResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_runtime_workflow(output: dict | None = None, state: str = "completed") -> MagicMock:
    """Return a mock runtime Workflow."""
    wf = MagicMock()

    async def _invoke(inputs, session, **kw):
        from types import SimpleNamespace
        result = SimpleNamespace()
        result.result = output or {"text": "hello"}
        result.state = SimpleNamespace(value=state)
        return result

    async def _stream(inputs, session, **kw):
        yield {"text": "tok1"}
        yield {"text": "tok2"}

    wf.invoke = _invoke
    wf.stream = _stream
    return wf


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_workflow_bridge(request):
    """Patch all workflow_bridge callables."""
    state = getattr(request, "param", "completed")
    fake_rt = _make_fake_runtime_workflow(state=state)
    fake_sess = MagicMock()

    with (
        patch("openjiuwen.sdk._internal.workflow_bridge.build_runtime_workflow", return_value=fake_rt),
        patch("openjiuwen.sdk._internal.workflow_bridge.create_workflow_session", return_value=fake_sess),
        patch("openjiuwen.sdk._internal.workflow_bridge.make_workflow_card", return_value=MagicMock()),
    ):
        yield {"runtime_wf": fake_rt, "session": fake_sess}


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


class TestWorkflowNodes:
    def test_llm_node_fields(self):
        node = LLMNode("Summarise: {input}")
        assert node.prompt_template == "Summarise: {input}"
        assert node.name is None
        assert node.max_tokens is None

    def test_llm_node_with_options(self):
        node = LLMNode("Translate: {input}", name="translator", max_tokens=512)
        assert node.name == "translator"
        assert node.max_tokens == 512

    def test_llm_node_is_workflow_node(self):
        assert isinstance(LLMNode("x"), WorkflowNode)

    def test_tool_node_fields(self):
        mock_tool = MagicMock()
        mock_tool.name = "search"
        node = ToolNode(tool=mock_tool)
        assert node.tool is mock_tool
        assert node.name is None

    def test_condition_node_fields(self):
        cond = lambda: True  # noqa: E731
        node = ConditionNode(condition=cond, true_target="yes", false_target="no")
        assert node.condition is cond
        assert node.true_target == "yes"
        assert node.false_target == "no"


# ---------------------------------------------------------------------------
# Workflow.create and builder API
# ---------------------------------------------------------------------------


class TestWorkflowCreate:
    def test_create_returns_workflow(self):
        wf = Workflow.create("pipeline")
        assert isinstance(wf, Workflow)

    def test_create_sets_name(self):
        wf = Workflow.create("my-wf")
        assert wf._name == "my-wf"

    def test_create_with_model(self):
        from unittest.mock import MagicMock
        mock_model = MagicMock()
        wf = Workflow.create("wf", model=mock_model)
        assert wf._model_cfg is mock_model

    def test_add_node_returns_self(self):
        wf = Workflow.create("wf")
        result = wf.add_node("step1", LLMNode("prompt"))
        assert result is wf

    def test_connect_returns_self(self):
        wf = Workflow.create("wf")
        wf.add_node("a", LLMNode("a"))
        wf.add_node("b", LLMNode("b"))
        result = wf.connect("a", "b")
        assert result is wf

    def test_duplicate_node_raises(self):
        wf = Workflow.create("wf")
        wf.add_node("step1", LLMNode("p"))
        with pytest.raises(WorkflowError, match="already exists"):
            wf.add_node("step1", LLMNode("p2"))

    def test_add_node_wrong_type_raises(self):
        wf = Workflow.create("wf")
        with pytest.raises(TypeError):
            wf.add_node("bad", "not a node")  # type: ignore

    def test_chain_builder(self):
        wf = (
            Workflow.create("chain")
            .add_node("a", LLMNode("a"))
            .add_node("b", LLMNode("b"))
            .connect("a", "b")
        )
        assert list(wf._nodes) == ["a", "b"]
        assert ("a", "b") in wf._edges

    def test_branch_records_conditional_edge(self):
        cond = lambda: True  # noqa: E731
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("x"))
        wf.add_node("true_path", LLMNode("y"))
        wf.add_node("false_path", LLMNode("z"))
        wf.branch("step", cond, true_target="true_path", false_target="false_path")
        assert len(wf._conditional_edges) == 1
        src, fn, tt, ft = wf._conditional_edges[0]
        assert src == "step"
        assert fn is cond

    def test_repr(self):
        wf = Workflow.create("my-wf")
        wf.add_node("step", LLMNode("p"))
        assert "my-wf" in repr(wf)
        assert "step" in repr(wf)


# ---------------------------------------------------------------------------
# Workflow.run
# ---------------------------------------------------------------------------


class TestWorkflowRun:
    @pytest.mark.asyncio
    async def test_run_returns_workflow_result(self, mock_workflow_bridge):
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("prompt"))
        result = await wf.run({"input": "hello"})
        assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_run_result_has_output(self, mock_workflow_bridge):
        mock_workflow_bridge["runtime_wf"].invoke = AsyncMock(
            return_value=_result_obj({"answer": "42"}, "completed")
        )
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("q"))
        result = await wf.run({"input": "x"})
        assert isinstance(result.output, dict)

    @pytest.mark.asyncio
    async def test_run_state_completed(self, mock_workflow_bridge):
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("q"))
        result = await wf.run({"input": "x"})
        assert result.state == "completed"

    @pytest.mark.asyncio
    async def test_run_wraps_exception_in_workflow_error(self, mock_workflow_bridge):
        from openjiuwen.sdk._internal import workflow_bridge as wb
        with patch.object(wb, "run_workflow", side_effect=RuntimeError("boom")):
            wf = Workflow.create("wf")
            wf.add_node("step", LLMNode("q"))
            wf._runtime_wf = mock_workflow_bridge["runtime_wf"]  # skip compile
            with pytest.raises(WorkflowError, match="boom"):
                await wf.run({})

    @pytest.mark.asyncio
    async def test_run_compile_caches_runtime_wf(self, mock_workflow_bridge):
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("p"))
        await wf.run({"input": "a"})
        first = wf._runtime_wf
        await wf.run({"input": "b"})
        assert wf._runtime_wf is first  # same object — not recompiled


# ---------------------------------------------------------------------------
# Workflow.stream
# ---------------------------------------------------------------------------


class TestWorkflowStream:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, mock_workflow_bridge):
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("p"))
        chunks = [c async for c in wf.stream({"input": "x"})]
        assert len(chunks) == 2
        assert all(isinstance(c, dict) for c in chunks)
        assert chunks[0].get("text") == "tok1"
        assert chunks[1].get("text") == "tok2"

    @pytest.mark.asyncio
    async def test_stream_wraps_exception(self, mock_workflow_bridge):
        from openjiuwen.sdk._internal import workflow_bridge as wb
        with patch.object(wb, "stream_workflow", side_effect=RuntimeError("stream fail")):
            wf = Workflow.create("wf")
            wf.add_node("step", LLMNode("p"))
            wf._runtime_wf = mock_workflow_bridge["runtime_wf"]
            with pytest.raises(WorkflowError, match="stream fail"):
                async for _ in wf.stream({}):
                    pass


# ---------------------------------------------------------------------------
# Workflow.draw
# ---------------------------------------------------------------------------


class TestWorkflowDraw:
    def test_draw_returns_mermaid_string(self):
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("p"))
        diagram = wf.draw()
        assert "graph TD" in diagram
        assert "step" in diagram

    def test_draw_includes_edges(self):
        wf = Workflow.create("wf")
        wf.add_node("a", LLMNode("a"))
        wf.add_node("b", LLMNode("b"))
        wf.connect("a", "b")
        diagram = wf.draw()
        assert "a --> b" in diagram

    def test_draw_includes_conditional_edges(self):
        wf = Workflow.create("wf")
        wf.add_node("step", LLMNode("p"))
        wf.add_node("yes", LLMNode("y"))
        wf.add_node("no", LLMNode("n"))
        wf.branch("step", lambda: True, true_target="yes", false_target="no")
        diagram = wf.draw()
        assert "yes" in diagram
        assert "no" in diagram


# ---------------------------------------------------------------------------
# WorkflowResult
# ---------------------------------------------------------------------------


class TestWorkflowResult:
    def test_fields(self):
        r = WorkflowResult(output={"text": "hi"}, state="completed")
        assert r.output == {"text": "hi"}
        assert r.state == "completed"
        assert r.session_id is None
        assert r.metadata == {}

    def test_metadata_default(self):
        r = WorkflowResult(output={}, state="error")
        assert r.metadata == {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_obj(output: dict, state: str):
    from types import SimpleNamespace
    r = SimpleNamespace()
    r.result = output
    r.state = SimpleNamespace(value=state)
    return r

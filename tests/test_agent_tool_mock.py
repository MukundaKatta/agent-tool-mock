"""Tests for agent-tool-mock."""

from __future__ import annotations

import pytest

from agent_tool_mock import MockTool, MockToolSet, ToolCallRecord

# ---------------------------------------------------------------------------
# ToolCallRecord
# ---------------------------------------------------------------------------


def test_call_record_succeeded():
    r = ToolCallRecord("search", {"q": "hi"}, "result", None)
    assert r.succeeded is True


def test_call_record_failed():
    err = ValueError("oops")
    r = ToolCallRecord("search", {}, None, err)
    assert r.succeeded is False
    assert r.raised is err


# ---------------------------------------------------------------------------
# MockTool — construction
# ---------------------------------------------------------------------------


def test_mock_tool_default_return():
    tool = MockTool("ping")
    assert tool() is None


def test_mock_tool_return_value():
    tool = MockTool("search", return_value=["a", "b"])
    assert tool() == ["a", "b"]


def test_mock_tool_repr():
    tool = MockTool("search")
    assert "MockTool" in repr(tool)
    assert "search" in repr(tool)


# ---------------------------------------------------------------------------
# MockTool — call count
# ---------------------------------------------------------------------------


def test_mock_tool_call_count_zero():
    tool = MockTool("search")
    assert tool.call_count() == 0


def test_mock_tool_call_count_increments():
    tool = MockTool("search", return_value="ok")
    tool()
    tool()
    assert tool.call_count() == 2


def test_mock_tool_calls_returns_copy():
    tool = MockTool("search", return_value="ok")
    tool()
    copy = tool.calls()
    copy.clear()
    assert tool.call_count() == 1


# ---------------------------------------------------------------------------
# MockTool — call_args
# ---------------------------------------------------------------------------


def test_mock_tool_call_args_last():
    tool = MockTool("search", return_value="ok")
    tool(query="hello")
    assert tool.call_args() == {"query": "hello"}


def test_mock_tool_call_args_by_index():
    tool = MockTool("search", return_value="ok")
    tool(query="first")
    tool(query="second")
    assert tool.call_args(0) == {"query": "first"}
    assert tool.call_args(1) == {"query": "second"}


def test_mock_tool_call_args_not_called_raises():
    tool = MockTool("search")
    with pytest.raises(IndexError):
        tool.call_args()


# ---------------------------------------------------------------------------
# MockTool — side_effect callable
# ---------------------------------------------------------------------------


def test_mock_tool_side_effect_callable():
    tool = MockTool("add", side_effect=lambda x, y: x + y)
    assert tool(x=3, y=4) == 7


def test_mock_tool_side_effect_records_result():
    tool = MockTool("double", side_effect=lambda n: n * 2)
    tool(n=5)
    assert tool.calls()[0].result == 10


# ---------------------------------------------------------------------------
# MockTool — side_effect exception
# ---------------------------------------------------------------------------


def test_mock_tool_side_effect_exception_instance():
    tool = MockTool("boom", side_effect=ValueError("bad"))
    with pytest.raises(ValueError, match="bad"):
        tool()


def test_mock_tool_side_effect_exception_class():
    tool = MockTool("boom", side_effect=RuntimeError)
    with pytest.raises(RuntimeError):
        tool()


def test_mock_tool_side_effect_exception_records_raised():
    err = ValueError("boom")
    tool = MockTool("boom", side_effect=err)
    try:
        tool()
    except ValueError:
        pass
    assert tool.calls()[0].raised is err
    assert tool.calls()[0].succeeded is False


def test_mock_tool_exception_increments_count():
    tool = MockTool("boom", side_effect=RuntimeError)
    try:
        tool()
    except RuntimeError:
        pass
    assert tool.call_count() == 1


# ---------------------------------------------------------------------------
# MockTool — configure
# ---------------------------------------------------------------------------


def test_mock_tool_configure_return_value():
    tool = MockTool("search", return_value="old")
    tool.configure(return_value="new")
    assert tool() == "new"


def test_mock_tool_configure_does_not_reset_calls():
    tool = MockTool("search", return_value="old")
    tool()
    tool.configure(return_value="new")
    assert tool.call_count() == 1


# ---------------------------------------------------------------------------
# MockTool — assertions
# ---------------------------------------------------------------------------


def test_assert_called_passes():
    tool = MockTool("search", return_value="ok")
    tool()
    tool.assert_called()


def test_assert_called_fails_when_not_called():
    tool = MockTool("search")
    with pytest.raises(AssertionError):
        tool.assert_called()


def test_assert_called_times():
    tool = MockTool("search", return_value="ok")
    tool()
    tool()
    tool.assert_called(times=2)


def test_assert_called_times_fails():
    tool = MockTool("search", return_value="ok")
    tool()
    with pytest.raises(AssertionError):
        tool.assert_called(times=3)


def test_assert_called_once():
    tool = MockTool("search", return_value="ok")
    tool()
    tool.assert_called_once()


def test_assert_not_called():
    tool = MockTool("search")
    tool.assert_not_called()


def test_assert_not_called_fails():
    tool = MockTool("search", return_value="ok")
    tool()
    with pytest.raises(AssertionError):
        tool.assert_not_called()


def test_assert_called_with():
    tool = MockTool("search", return_value="ok")
    tool(query="python", limit=10)
    tool.assert_called_with(query="python", limit=10)


def test_assert_called_with_wrong_value_fails():
    tool = MockTool("search", return_value="ok")
    tool(query="python")
    with pytest.raises(AssertionError):
        tool.assert_called_with(query="ruby")


def test_assert_called_with_missing_key_fails():
    tool = MockTool("search", return_value="ok")
    tool(query="python")
    with pytest.raises(AssertionError):
        tool.assert_called_with(limit=5)


def test_assert_called_with_index_kwarg():
    # 'index' is positional-only, so it may also be a real tool kwarg.
    tool = MockTool("paginate", return_value="ok")
    tool(index=3, query="hi")
    tool.assert_called_with(index=3)
    tool.assert_called_with(index=3, query="hi")
    with pytest.raises(AssertionError):
        tool.assert_called_with(index=4)


def test_assert_called_with_positional_index_and_kwarg():
    tool = MockTool("paginate", return_value="ok")
    tool(index=1)
    tool(index=2)
    tool.assert_called_with(0, index=1)
    tool.assert_called_with(1, index=2)


def test_call_args_index_is_positional_only():
    tool = MockTool("paginate", return_value="ok")
    tool(index=7)
    # Passed as a keyword, 'index' is a recorded kwarg, not the selector.
    assert tool.call_args()["index"] == 7


# ---------------------------------------------------------------------------
# MockTool — reset
# ---------------------------------------------------------------------------


def test_reset_clears_calls():
    tool = MockTool("search", return_value="ok")
    tool()
    tool.reset()
    assert tool.call_count() == 0


def test_reset_keeps_return_value():
    tool = MockTool("search", return_value="ok")
    tool()
    tool.reset()
    assert tool() == "ok"


# ---------------------------------------------------------------------------
# MockToolSet — basic
# ---------------------------------------------------------------------------


def test_mock_tool_set_empty():
    ts = MockToolSet()
    assert len(ts) == 0


def test_mock_tool_set_add():
    ts = MockToolSet()
    ts.add("search", return_value="ok")
    assert "search" in ts


def test_mock_tool_set_getitem():
    ts = MockToolSet()
    ts.add("search")
    assert isinstance(ts["search"], MockTool)


def test_mock_tool_set_getitem_missing_raises():
    ts = MockToolSet()
    with pytest.raises(KeyError):
        ts["nope"]


def test_mock_tool_set_contains():
    ts = MockToolSet()
    ts.add("a")
    assert "a" in ts
    assert "b" not in ts


def test_mock_tool_set_names_sorted():
    ts = MockToolSet()
    ts.add("z")
    ts.add("a")
    ts.add("m")
    assert ts.names() == ["a", "m", "z"]


def test_mock_tool_set_repr():
    ts = MockToolSet()
    assert "MockToolSet" in repr(ts)


# ---------------------------------------------------------------------------
# MockToolSet — dispatch
# ---------------------------------------------------------------------------


def test_mock_tool_set_dispatch():
    ts = MockToolSet()
    ts.add("add", side_effect=lambda x, y: x + y)
    assert ts.dispatch("add", x=2, y=3) == 5


def test_mock_tool_set_dispatch_unknown_raises():
    ts = MockToolSet()
    with pytest.raises(KeyError):
        ts.dispatch("nope")


def test_mock_tool_set_dispatch_records_call():
    ts = MockToolSet()
    ts.add("search", return_value="ok")
    ts.dispatch("search", query="hi")
    ts["search"].assert_called_once()


# ---------------------------------------------------------------------------
# MockToolSet — register
# ---------------------------------------------------------------------------


def test_mock_tool_set_register():
    ts = MockToolSet()
    mock = MockTool("custom", return_value=42)
    ts.register(mock)
    assert ts["custom"] is mock


# ---------------------------------------------------------------------------
# MockToolSet — reset_all
# ---------------------------------------------------------------------------


def test_mock_tool_set_reset_all():
    ts = MockToolSet()
    ts.add("a", return_value=1)
    ts.add("b", return_value=2)
    ts.dispatch("a")
    ts.dispatch("b")
    ts.reset_all()
    ts["a"].assert_not_called()
    ts["b"].assert_not_called()


# ---------------------------------------------------------------------------
# MockToolSet — constructor with tools
# ---------------------------------------------------------------------------


def test_mock_tool_set_from_list():
    mocks = [MockTool("x", return_value=1), MockTool("y", return_value=2)]
    ts = MockToolSet(mocks)
    assert "x" in ts and "y" in ts
    assert ts.dispatch("x") == 1


# ---------------------------------------------------------------------------
# Misc — direct call, configure edge cases
# ---------------------------------------------------------------------------


def test_side_effect_takes_priority_over_return_value():
    tool = MockTool("x", return_value="rv", side_effect=lambda: "se")
    assert tool() == "se"


def test_configure_clears_side_effect_by_default():
    tool = MockTool("x", side_effect=lambda: "se")
    tool.configure(return_value="rv")
    assert tool() == "rv"


def test_mock_tool_set_dispatch_forwards_kwargs():
    ts = MockToolSet()
    ts.add("echo", side_effect=lambda msg: msg)
    assert ts.dispatch("echo", msg="hello") == "hello"
    ts["echo"].assert_called_with(msg="hello")

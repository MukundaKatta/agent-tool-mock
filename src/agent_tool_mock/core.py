"""Mock tool implementations for testing AI agent loops.

:class:`MockTool` wraps a tool name with a canned return value or callable
side-effect and records every invocation for later assertion.
:class:`MockToolSet` manages multiple mocks by name, acting as a drop-in
replacement for a real tool-dispatch layer in unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCallRecord:
    """A single recorded invocation of a mock tool.

    Attributes:
        tool_name: The name of the tool that was called.
        kwargs: The keyword arguments passed to the tool.
        result: The value that was returned (``None`` if an exception was raised).
        raised: The exception that was raised, or ``None`` on success.
    """

    tool_name: str
    kwargs: dict[str, Any]
    result: Any
    raised: Exception | None

    @property
    def succeeded(self) -> bool:
        """``True`` when the call completed without raising."""
        return self.raised is None


class MockTool:
    """A mock tool that records calls and returns a configured value.

    Args:
        name: The tool name (used for error messages).
        return_value: Value returned on every call.  Ignored when
            *side_effect* is set.
        side_effect: A callable invoked with ``**kwargs`` whose return value
            is used as the result, **or** an exception instance / class that
            is raised on every call.

    Example::

        tool = MockTool("search", return_value=["result1", "result2"])
        result = tool(query="python")   # ["result1", "result2"]
        tool.assert_called_once()
        tool.assert_called_with(query="python")
    """

    def __init__(
        self,
        name: str,
        *,
        return_value: Any = None,
        side_effect: Any = None,
    ) -> None:
        self.name = name
        self._return_value = return_value
        self._side_effect = side_effect
        self._calls: list[ToolCallRecord] = []

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    def __call__(self, **kwargs: Any) -> Any:
        """Invoke the mock and record the call."""
        result = None
        try:
            if self._side_effect is not None:
                # Exception instance or class → raise it
                if isinstance(self._side_effect, BaseException):
                    raise self._side_effect
                if isinstance(self._side_effect, type) and issubclass(
                    self._side_effect, BaseException
                ):
                    raise self._side_effect()
                # Callable → call it
                result = self._side_effect(**kwargs)
            else:
                result = self._return_value
        except Exception as exc:
            self._calls.append(ToolCallRecord(self.name, dict(kwargs), None, exc))
            raise
        self._calls.append(ToolCallRecord(self.name, dict(kwargs), result, None))
        return result

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(
        self,
        *,
        return_value: Any = None,
        side_effect: Any = None,
    ) -> None:
        """Reconfigure the mock without resetting recorded calls.

        Args:
            return_value: New canned return value.
            side_effect: New side effect callable or exception.
        """
        self._return_value = return_value
        self._side_effect = side_effect

    # ------------------------------------------------------------------
    # Recorded call inspection
    # ------------------------------------------------------------------

    def call_count(self) -> int:
        """Return the number of times this mock has been called."""
        return len(self._calls)

    def calls(self) -> list[ToolCallRecord]:
        """Return a copy of all recorded :class:`ToolCallRecord` objects."""
        return list(self._calls)

    def call_args(self, index: int = -1) -> dict[str, Any]:
        """Return the kwargs dict for the call at *index* (default: last call).

        Args:
            index: Position in the call list.

        Raises:
            IndexError: If the mock has not been called or index is out of range.
        """
        if not self._calls:
            raise IndexError(f"Mock {self.name!r} has not been called.")
        return dict(self._calls[index].kwargs)

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def assert_called(self, *, times: int | None = None) -> None:
        """Assert that the mock was called at least once (or exactly *times*).

        Args:
            times: If given, assert exactly this many calls.

        Raises:
            AssertionError: On failure.
        """
        if times is None:
            assert self._calls, f"Expected {self.name!r} to be called but it was not."
        else:
            actual = len(self._calls)
            assert actual == times, (
                f"Expected {self.name!r} to be called {times} time(s), got {actual}."
            )

    def assert_called_once(self) -> None:
        """Assert that the mock was called exactly once."""
        self.assert_called(times=1)

    def assert_not_called(self) -> None:
        """Assert that the mock was never called."""
        assert not self._calls, (
            f"Expected {self.name!r} NOT to be called but it was called"
            f" {len(self._calls)} time(s)."
        )

    def assert_called_with(self, index: int = -1, **expected: Any) -> None:
        """Assert that the call at *index* used *expected* kwargs.

        Args:
            index: Which call to inspect (default: last).
            **expected: Expected keyword argument values.

        Raises:
            AssertionError: If any expected kwarg is absent or has wrong value.
        """
        actual = self.call_args(index)
        for key, val in expected.items():
            assert key in actual, (
                f"Expected kwarg {key!r} in call to {self.name!r},"
                f" got keys {list(actual.keys())}."
            )
            assert actual[key] == val, (
                f"Expected {self.name!r} called with {key}={val!r},"
                f" got {key}={actual[key]!r}."
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all recorded call history."""
        self._calls.clear()

    def __repr__(self) -> str:
        return f"MockTool(name={self.name!r}, calls={len(self._calls)})"


class MockToolSet:
    """A collection of :class:`MockTool` instances accessed by name.

    Args:
        tools: Optional iterable of :class:`MockTool` instances to pre-register.

    Example::

        tools = MockToolSet()
        tools.add("search", return_value=["hit1"])
        tools.add("fetch", return_value="page content")

        result = tools.dispatch("search", query="test")  # ["hit1"]
        tools["search"].assert_called_once()
    """

    def __init__(self, tools: list[MockTool] | None = None) -> None:
        self._mocks: dict[str, MockTool] = {}
        for t in tools or []:
            self._mocks[t.name] = t

    def add(
        self,
        name: str,
        *,
        return_value: Any = None,
        side_effect: Any = None,
    ) -> MockTool:
        """Register a new mock tool and return it.

        Args:
            name: Tool name.
            return_value: Canned return value.
            side_effect: Callable or exception to use as side effect.

        Returns:
            The new :class:`MockTool`.
        """
        mock = MockTool(name, return_value=return_value, side_effect=side_effect)
        self._mocks[name] = mock
        return mock

    def register(self, mock: MockTool) -> None:
        """Register an existing :class:`MockTool` instance."""
        self._mocks[mock.name] = mock

    def __getitem__(self, name: str) -> MockTool:
        if name not in self._mocks:
            raise KeyError(f"No mock registered for tool {name!r}.")
        return self._mocks[name]

    def __contains__(self, name: str) -> bool:
        return name in self._mocks

    def dispatch(self, name: str, **kwargs: Any) -> Any:
        """Call the mock for *name* with *kwargs*.

        Args:
            name: Tool name to dispatch.
            **kwargs: Arguments forwarded to the mock.

        Raises:
            KeyError: If no mock is registered for *name*.
        """
        return self[name](**kwargs)

    def names(self) -> list[str]:
        """Return sorted list of registered mock names."""
        return sorted(self._mocks)

    def reset_all(self) -> None:
        """Reset call history on all registered mocks."""
        for mock in self._mocks.values():
            mock.reset()

    def __len__(self) -> int:
        return len(self._mocks)

    def __repr__(self) -> str:
        return f"MockToolSet(tools={self.names()!r})"

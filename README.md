# agent-tool-mock

Mock tool implementations for testing AI agent loops.

Record calls, configure canned return values, inject exceptions, and assert invocation patterns — without any external dependencies.

## Install

```bash
pip install agent-tool-mock
```

## Quick start

```python
from agent_tool_mock import MockTool, MockToolSet

# Single mock
search = MockTool("search", return_value=["result1", "result2"])
result = search(query="python")   # ["result1", "result2"]
search.assert_called_once()
search.assert_called_with(query="python")

# Collection of mocks
tools = MockToolSet()
tools.add("search", return_value=["hit"])
tools.add("fetch", side_effect=lambda url: f"content of {url}")

result = tools.dispatch("fetch", url="https://example.com")
tools["search"].assert_not_called()
tools["fetch"].assert_called_once()
```

## API

### `MockTool(name, *, return_value=None, side_effect=None)`

- `return_value`: Returned on every call.
- `side_effect`: A callable (called with `**kwargs`) **or** an exception instance/class (raised on every call).

#### Invocation

```python
tool(**kwargs)             # calls the mock; records and returns/raises
```

#### Inspection

```python
tool.call_count()          # int
tool.calls()               # list[ToolCallRecord] (copy)
tool.call_args(index=-1)   # dict of kwargs for the given call
```

#### Assertions

```python
tool.assert_called()               # called at least once
tool.assert_called(times=2)        # called exactly 2 times
tool.assert_called_once()          # shorthand for times=1
tool.assert_not_called()
tool.assert_called_with(key=val)   # last call had these kwargs
tool.assert_called_with(index=0, key=val)  # specific call
```

#### Reconfigure / Reset

```python
tool.configure(return_value="new")   # change return without resetting calls
tool.reset()                          # clear call history
```

### `MockToolSet`

```python
ts = MockToolSet()
ts.add("search", return_value=["hit"])   # returns MockTool
ts.register(existing_mock)
ts.dispatch("search", query="hi")        # calls and records
ts["search"]                             # access mock by name
ts.names()                               # sorted list of names
ts.reset_all()                           # reset all call histories
len(ts)                                  # count
```

### `ToolCallRecord`

```python
record.tool_name   # str
record.kwargs      # dict[str, Any]
record.result      # return value (None if exception raised)
record.raised      # Exception | None
record.succeeded   # bool
```

## License

MIT

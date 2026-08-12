# Examples

Each file is a runnable Python script demonstrating one aspect of the SDK.

## Prerequisites

```bash
pip install openjiuwen-sdk[runtime]   # in-process examples
pip install openjiuwen-sdk            # remote/A2A examples only
pip install httpx                     # custom_tools.py
```

Set at least one environment variable before running:

```bash
export JIUWENSWARM_API_KEY=sk-your-openai-key
# or
export OPENAI_API_KEY=sk-your-openai-key
```

## Files

| File | Feature |
|------|---------|
| `quick_start.py` | 10-line hello world — in-process and remote mode |
| `streaming.py` | Stream tokens with async-for and event callbacks |
| `session_management.py` | Session CRUD, multi-turn conversation, history |
| `custom_tools.py` | `@tool` decorator — sync, async, enum constraints, direct invocation |
| `workflow_dag.py` | Multi-step DAG — linear, conditional branch, streaming |
| `multi_agent_team.py` | Three-agent team — researcher, writer, reviewer |
| `hooks_lifecycle.py` | All lifecycle hooks in decorator and constructor form |
| `a2a_remote_agent.py` | A2A protocol — run, stream, cancel, local+remote composition |

## Running an example

```bash
python examples/quick_start.py
python examples/streaming.py
python examples/custom_tools.py
# etc.
```

Examples that connect to a remote server or A2A service handle `ConnectionError`
gracefully and print a message when the service is not running.

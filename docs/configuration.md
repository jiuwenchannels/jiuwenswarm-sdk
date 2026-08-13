# Configuration Reference

All configuration for the SDK flows through two frozen dataclasses
(`ModelConfig`, `RemoteConfig`) and a set of environment variables.
Neither class takes positional arguments — use keyword arguments only.

---

## Environment variables

| Variable | Read by | Default | Description |
|----------|---------|---------|-------------|
| `JIUWENSWARM_API_KEY` | `ModelConfig.from_env()` | — | Primary API key. Used for any provider. Takes precedence over provider-specific keys. |
| `OPENAI_API_KEY` | `ModelConfig.from_env()` | — | OpenAI API key. Used when `provider="openai"` and `JIUWENSWARM_API_KEY` is not set. |
| `ANTHROPIC_API_KEY` | `ModelConfig.from_env()` | — | Anthropic API key. Used when `provider="anthropic"` and `JIUWENSWARM_API_KEY` is not set. |
| `JIUWENSWARM_URL` | `RemoteConfig.from_env()` | `ws://localhost:19000` | WebSocket server URL for remote mode. |
| `JIUWENSWARM_TOKEN` | `RemoteConfig.from_env()` | — | Bearer auth token for remote WebSocket connection. |
| `JIUWENSWARM_MODEL` | `SdkConfig.from_env()` | `gpt-4o` | Default model name when no `ModelConfig` is provided explicitly. |
| `OPENJIUWEN_TEAM_JOIN` | MCP server (`§29`) | — | Team discovery URL used by the MCP subprocess. Example: `team://my-team@localhost:9000`. |

---

## `ModelConfig`

Controls the LLM used in **in-process** mode (`Agent.create()`).

```python
@dataclass(frozen=True)
class ModelConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float | None = None   # runtime default: 0.95
    max_tokens: int | None = None
    timeout: float = 60.0
    max_retries: int = 3
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | `str` | `"openai"` | LLM provider. Built-in: `"openai"`, `"anthropic"`, `"siliconflow"`. Custom providers can be registered. |
| `model` | `str` | `"gpt-4o"` | Model name as accepted by the provider's API. |
| `api_key` | `str \| None` | `None` | API key. Falls back to env vars when `None`. |
| `api_base` | `str \| None` | `None` | Override the base URL (useful for proxies or self-hosted models). |
| `temperature` | `float \| None` | `None` | Sampling temperature. `None` uses the runtime default (0.95). |
| `max_tokens` | `int \| None` | `None` | Maximum tokens to generate. `None` uses provider default. |
| `timeout` | `float` | `60.0` | Request timeout in seconds. |
| `max_retries` | `int` | `3` | Number of retry attempts on transient errors. |

### Constructor

```python
cfg = ModelConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-...",
    temperature=0.7,
    max_tokens=4096,
)
```

### `from_env()` classmethod

```python
cfg = ModelConfig.from_env()
```

Reads `JIUWENSWARM_API_KEY` (or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`),
`JIUWENSWARM_MODEL`. All other fields use their defaults.

---

## `RemoteConfig`

Controls the WebSocket connection in **remote** mode (`Agent.connect()`).

```python
@dataclass(frozen=True)
class RemoteConfig:
    url: str = "ws://localhost:19000"
    auth_token: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `str` | `"ws://localhost:19000"` | WebSocket server URL including protocol (`ws://` or `wss://`). |
| `auth_token` | `str \| None` | `None` | Bearer token sent in the `connect` envelope. Optional in dev mode. |
| `timeout` | `float` | `30.0` | Connection and response timeout in seconds. |
| `max_retries` | `int` | `3` | Reconnect attempts on transient connection failures. |

### Constructor

```python
cfg = RemoteConfig(
    url="wss://my-server.example.com:19000",
    auth_token="token-abc123",
    timeout=60.0,
)
```

### `from_env()` classmethod

```python
cfg = RemoteConfig.from_env()
```

Reads `JIUWENSWARM_URL` and `JIUWENSWARM_TOKEN`.

---

## `SdkConfig`

Top-level convenience config. Used when you want a single object for
both LLM settings and remote settings.

```python
@dataclass(frozen=True)
class SdkConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    remote: RemoteConfig = field(default_factory=RemoteConfig)
```

```python
cfg = SdkConfig.from_env()
agent = await Agent.create("name", model=cfg.model)
```

---

## Usage patterns

### Minimal in-process (env vars)

```bash
export OPENAI_API_KEY=sk-...
```

```python
agent = await Agent.create("my-agent")  # ModelConfig.from_env() used automatically
```

### Explicit model

```python
agent = await Agent.create(
    "my-agent",
    model=ModelConfig(provider="anthropic", model="claude-3-5-sonnet-20241022"),
)
```

### Remote connection

```python
agent = await Agent.connect(
    "remote-agent",
    config=RemoteConfig(url="wss://prod.example.com:19000", auth_token="tok"),
)
```

### Custom provider base URL (e.g. local Ollama)

```python
agent = await Agent.create(
    "local-agent",
    model=ModelConfig(
        provider="openai",
        model="llama3",
        api_base="http://localhost:11434/v1",
        api_key="ollama",
    ),
)
```

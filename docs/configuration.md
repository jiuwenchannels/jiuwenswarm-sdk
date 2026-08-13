# Configuration Reference

---

## Environment variables

### Python SDK

| Variable | Read by | Default | Description |
|----------|---------|---------|-------------|
| `JIUWENSWARM_API_KEY` | `ModelConfig.from_env()` | — | Primary LLM API key. Any provider. Takes precedence over provider-specific keys. |
| `OPENAI_API_KEY` | `ModelConfig.from_env()` | — | OpenAI key. Used when `provider="openai"` and `JIUWENSWARM_API_KEY` is not set. |
| `ANTHROPIC_API_KEY` | `ModelConfig.from_env()` | — | Anthropic key. Used when `provider="anthropic"`. |
| `JIUWENSWARM_PROVIDER` | `ModelConfig.from_env()` | `"openai"` | Default LLM provider. |
| `JIUWENSWARM_MODEL` | `ModelConfig.from_env()` | `"gpt-4o"` | Default model name. |
| `JIUWENSWARM_URL` | `RemoteConfig.from_env()` | `ws://localhost:19000` | WebSocket server URL for `Agent.connect()`. |
| `JIUWENSWARM_TOKEN` | `RemoteConfig.from_env()` | — | Bearer auth token for remote connection. |

### Gateway server

| Variable | Description |
|----------|-------------|
| `JIUWENSWARM_GATEWAY_TOKEN` | Server-side bearer token. Requests without it receive 401. Unset = auth disabled. |
| `JIUWENSWARM_GATEWAY_HOST` | Bind address (default `0.0.0.0`). |
| `JIUWENSWARM_GATEWAY_PORT_REST` | REST server port (default `19001`). |
| `JIUWENSWARM_GATEWAY_PORT_WS` | WebSocket server port (default `19000`). |

### MCP server

| Variable | Description |
|----------|-------------|
| `OPENJIUWEN_TEAM_JOIN` | Team discovery URL. Example: `team://my-team@localhost:9000`. Read by `python -m openjiuwen.agent_teams.mcp`. |

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

    @classmethod
    def from_env(cls) -> "ModelConfig": ...
```

| Field | Default | Description |
|-------|---------|-------------|
| `provider` | `"openai"` | `"openai"` \| `"anthropic"` \| `"siliconflow"` \| any registered provider |
| `model` | `"gpt-4o"` | Model name accepted by the provider's API |
| `api_key` | `None` | Falls back to env vars when `None` |
| `api_base` | `None` | Override base URL — useful for proxies, Ollama, self-hosted models |
| `temperature` | `None` | Sampling temperature. `None` = runtime default (0.95) |
| `max_tokens` | `None` | Max tokens to generate. `None` = provider default |
| `timeout` | `60.0` | Request timeout in seconds |
| `max_retries` | `3` | Retry attempts on transient errors |

```python
# Examples
cfg = ModelConfig()                              # gpt-4o from OPENAI_API_KEY
cfg = ModelConfig.from_env()                     # reads all env vars

cfg = ModelConfig(provider="anthropic", model="claude-3-5-sonnet-20241022")
cfg = ModelConfig(provider="openai", api_base="http://localhost:11434/v1",
                  model="llama3", api_key="ollama")   # local Ollama
```

---

## `RemoteConfig`

Controls the connection in **remote** mode (`Agent.connect()`).

```python
@dataclass(frozen=True)
class RemoteConfig:
    server_url: str = "ws://localhost:19000/v1/ws"
    auth_token: str | None = None
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "RemoteConfig": ...
```

| Field | Default | Description |
|-------|---------|-------------|
| `server_url` | `ws://localhost:19000/v1/ws` | WebSocket (`ws://` \| `wss://`) or HTTP (`http://` \| `https://`) base URL |
| `auth_token` | `None` | Bearer token. Optional in dev mode. |
| `timeout` | `60.0` | Connection and response timeout in seconds |
| `max_retries` | `3` | Reconnect attempts on transient failures |

```python
cfg = RemoteConfig.from_env()
cfg = RemoteConfig(server_url="wss://prod.example.com:19000/v1/ws", auth_token="tok")
```

---

## `SdkConfig`

Top-level convenience wrapper holding both `ModelConfig` and `RemoteConfig`.

```python
@dataclass(frozen=True)
class SdkConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    remote: RemoteConfig = field(default_factory=RemoteConfig)

    @classmethod
    def from_env(cls) -> "SdkConfig": ...
```

```python
cfg = SdkConfig.from_env()
agent = await Agent.create("name", model=cfg.model)
```

---

## `GatewayConfig`

Passed to `build_gateway_app()`. All fields have env var fallbacks.

```python
@dataclass(frozen=True)
class GatewayConfig:
    host: str = "0.0.0.0"
    port_rest: int = 19001
    port_ws: int = 19000
    auth_token: str | None = None      # None = auth disabled
    log_level: str = "info"
    cors_origins: list[str] = field(default_factory=list)
```

---

## TypeScript `ClientConfig`

```typescript
interface ClientConfig {
  url: string;                          // "ws://host:19000/v1/ws"
  authToken?: string;
  onToken?: (text: string) => void;
  onDone?: (sessionId: string) => void;
  onError?: (message: string) => void;
  onToolCall?: (call: ToolCallEnvelope) => Promise<string>;
  reconnect?: ReconnectConfig | false;  // false = disable auto-reconnect
}

interface ReconnectConfig {
  maxAttempts?: number;      // default: Infinity
  initialDelayMs?: number;   // default: 1000
  maxDelayMs?: number;       // default: 30_000
  factor?: number;           // default: 2 (exponential)
}
```

---

## `OtelTracerConfig`

```python
@dataclass(frozen=True)
class OtelTracerConfig:
    endpoint: str = "http://localhost:4317"   # gRPC OTLP collector
    service_name: str = "jiuwenswarm"
    sample_rate: float = 1.0
    redact_llm_content: bool = False          # strip prompts/responses from spans (PII)
    resource_attributes: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
```

---

## `RLConfig`

```python
@dataclass(frozen=True)
class RLConfig:
    algorithm: str = "ppo"              # "ppo" | "dpo" | "grpo"
    reward_fn: Callable[[str], float] | None = None
    learning_rate: float = 1e-5
    rollouts_per_step: int = 4          # collect this many rollouts before a weight update
    online: bool = True                 # False = offline/trajectory-export mode
    max_trajectory_len: int = 50
```

---

## `MultiRolloutConfig`

```python
@dataclass(frozen=True)
class MultiRolloutConfig:
    n: int = 3                      # number of parallel rollouts
    temperature: float | None = None
    concurrency: int = 3            # max simultaneous agent calls
    timeout: float | None = None
```

---

## `WorkspaceConfig`

```python
@dataclass(frozen=True)
class WorkspaceConfig:
    root: str = "."
    sandbox: bool = False           # True = block paths outside root
    sandbox_image: str = "python:3.11-slim"
    max_file_size: int = 10 * 1024 * 1024   # bytes; 0 = unlimited
    allowed_extensions: tuple[str, ...] = ()  # empty = all extensions allowed
```

---

## Common patterns

```python
# Minimal in-process (env vars only)
export OPENAI_API_KEY=sk-...
agent = await Agent.create("my-agent")

# Explicit model
agent = await Agent.create(
    "my-agent",
    model=ModelConfig(provider="anthropic", model="claude-3-5-sonnet-20241022"),
)

# Remote connection
agent = await Agent.connect(
    "wss://prod.example.com:19000/v1/ws",
    auth_token=os.environ["JIUWENSWARM_TOKEN"],
)

# TypeScript — minimal
const client = new JiuwenSwarmClient({ url: "ws://localhost:19000/v1/ws" });

# TypeScript — with reconnect tuning
const client = new JiuwenSwarmClient({
  url: "wss://prod.example.com:19000/v1/ws",
  authToken: process.env.JIUWENSWARM_TOKEN,
  reconnect: { maxAttempts: 5, initialDelayMs: 2000, factor: 2 },
});

# Gateway — start with auth
python -m openjiuwen.gateway \
  --auth-token "$(cat /run/secrets/gateway_token)" \
  --port-rest 19001 --port-ws 19000
```

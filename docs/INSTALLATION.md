# Installation Guide — JiuwenSwarm SDK

---

## Access Modes at a Glance

| Mode | Package | Transport | Typical Use |
|---|---|---|---|
| **Python in-process** | `openjiuwen-sdk[runtime]` | None (in-process) | Scripts, notebooks, CLI tools |
| **Python remote** | `openjiuwen-sdk` | WebSocket / REST | Any Python app talking to a running server |
| **TypeScript / JavaScript** | `@jiuwenswarm/sdk` | WebSocket | Browser, Node.js, React / React Native |
| **REST / cURL** | None | HTTP | Any language via plain HTTP client |

All modes connect to the same JiuwenSwarm server runtime and share the same
session, agent, and tool semantics.

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required for the Python SDK and gateway |
| pip | 23+ | `pip --version` to verify |
| Node.js | 18+ | Required for the TypeScript SDK only |
| npm | 9+ | Bundled with Node.js |
| JiuwenSwarm server | any current | Required for remote / TypeScript modes |

---

## Part A — Python SDK

### A1. Install from PyPI (recommended)

**Remote mode only** (connects to a running JiuwenSwarm server):

```bash
pip install openjiuwen-sdk
```

**In-process mode** (runs the full runtime inside your Python process):

```bash
pip install "openjiuwen-sdk[runtime]"
```

**With the REST/WebSocket gateway server** (to host the server yourself):

```bash
pip install "openjiuwen-sdk[gateway]"
```

**Everything at once:**

```bash
pip install "openjiuwen-sdk[all]"
```

### A2. Install from source (development / monorepo)

```bash
git clone <repo-url> openjiuwenchannels
cd openjiuwenchannels/jiuwenswarm-sdk
pip install -e ".[dev]"
```

`-e` installs in editable mode so local changes take effect immediately.
`[dev]` adds pytest, ruff, pyright, and other developer tools.

### A3. Verify the Python installation

```python
python -c "import openjiuwen.sdk; print('ok')"
```

---

## Part B — TypeScript / JavaScript SDK

### B1. Install from npm

```bash
npm install @jiuwenswarm/sdk
```

For Node.js (server-side), also install the optional `ws` peer dependency:

```bash
npm install @jiuwenswarm/sdk ws
```

Browser bundlers (Vite, webpack, esbuild) use the native `WebSocket` API
and do not need `ws`.

### B2. Install from source (monorepo)

If you have the `openjiuwenchannels` repository, reference the local package:

```json
"@jiuwenswarm/sdk": "file:../jiuwenswarm-sdk/packages/sdk"
```

Then build the SDK once before running your project:

```bash
cd jiuwenswarm-sdk/packages/sdk
npm install
npm run build
```

### B3. Verify the TypeScript installation

```typescript
import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";
console.log(typeof JiuwenSwarmClient); // "function"
```

---

## Part C — Starting the JiuwenSwarm Server

The Python in-process mode needs no server. For all other modes (Python
remote, TypeScript, REST) a JiuwenSwarm server must be reachable.

**Option 1 — Desktop installer (Windows / macOS / HarmonyOS)**

Download and run the installer from [openjiuwen.com](https://openjiuwen.com).
The gateway starts automatically on port 19000.

**Option 2 — pip (gateway extra)**

```bash
pip install "openjiuwen-sdk[gateway]"
jiuwenswarm-start
```

**Option 3 — from source**

```bash
cd jiuwenswarm-sdk
pip install -e ".[gateway]"
jiuwenswarm-start
```

After any of the above the WebSocket gateway is available at:

```
ws://localhost:19000/v1/ws
```

Verify it is up:

```bash
curl http://localhost:19001/v1/health
# expected: {"status":"ok",...}
```

---

## Part D — Environment Variables

Copy the template and fill in the required values:

```bash
cp .env.example .env
```

Minimum settings for **remote / TypeScript / REST** usage:

```dotenv
# URL of the JiuwenSwarm WebSocket gateway
JIUWENSWARM_URL=ws://localhost:19000

# Bearer auth token — leave empty if the server runs without auth
JIUWENSWARM_TOKEN=
```

Minimum settings for **in-process** usage (LLM credentials):

```dotenv
JIUWENSWARM_PROVIDER=openai
JIUWENSWARM_API_KEY=sk-...
JIUWENSWARM_MODEL=gpt-4o
```

Gateway server settings (only needed when hosting the gateway yourself):

```dotenv
JIUWENSWARM_GATEWAY_HOST=0.0.0.0
JIUWENSWARM_GATEWAY_PORT_WS=19000
JIUWENSWARM_GATEWAY_PORT_REST=19001
JIUWENSWARM_GATEWAY_TOKEN=   # optional bearer token
```

See [`docs/configuration.md`](configuration.md) for the full reference.

---

## Part E — Running the Examples

### Python examples

```bash
cd jiuwenswarm-sdk
pip install -e ".[dev]"
cp .env.example .env   # fill in credentials / URL

# Remote mode examples
python examples/python/remote/basic_chat.py
python examples/python/remote/streaming.py

# In-process mode examples
python examples/python/in_process/basic_chat.py
```

### TypeScript examples

```bash
cd jiuwenswarm-sdk/packages/sdk
npm install
npm run build
cd ../../examples/typescript

# Node.js
npx ts-node basic_chat.ts

# Or compile and run
tsc basic_chat.ts && node basic_chat.js
```

### REST / cURL examples

With the gateway running on port 19001:

```bash
# List sessions
curl http://localhost:19001/v1/sessions

# Create a session and send a message
SESSION=$(curl -s -X POST http://localhost:19001/v1/sessions | jq -r '.id')
curl -X POST http://localhost:19001/v1/sessions/$SESSION/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello"}'
```

See `examples/rest/` for complete cURL scripts.

---

## Part F — Development Setup

After cloning the repository, install all dependencies for both Python and
TypeScript in one step:

```bash
make install
```

This runs `pip install -e ".[dev]"` and `cd packages/sdk && npm install`.

### Run the full test suite

```bash
make test        # Python tests (pytest)
make test-ts     # TypeScript tests (vitest)
```

Or run directly:

```bash
python -m pytest tests/ -q
cd packages/sdk && npm test
```

### Lint and type-check

```bash
make check       # ruff + mypy (Python)
make type-check  # mypy only (Python) / tsc --noEmit (TypeScript)
make fix         # auto-fix Python lint and formatting
```

### Build the TypeScript package

```bash
make build
# or
cd packages/sdk && npm run build
```

Output lands in `packages/sdk/dist/`.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'openjiuwen'`**
: Run `pip install openjiuwen-sdk` (or `pip install -e .` from source).
  Confirm the correct virtual environment is active.

**`ImportError: openjiuwen.core not found` when using in-process mode**
: The `runtime` extra is required: `pip install "openjiuwen-sdk[runtime]"`.

**WebSocket connection refused (`ws://localhost:19000`)**
: The JiuwenSwarm server is not running. Start it with `jiuwenswarm-start`
  or via the desktop installer. Verify with
  `curl http://localhost:19001/v1/health`.

**`npm install` fails on `@jiuwenswarm/sdk` (local `file:` reference)**
: Build the SDK first: `cd jiuwenswarm-sdk/packages/sdk && npm install && npm run build`.
  The dependent project's `npm install` will then succeed.

**TypeScript: `Cannot find module '@jiuwenswarm/sdk'`**
: Ensure `npm run build` has been run in `packages/sdk/` so that `dist/`
  exists. Check that `tsconfig.json` in your project resolves `node_modules`.

**Python tests fail with `event loop closed` errors**
: pytest-asyncio requires `asyncio_mode = "auto"` in `pyproject.toml`.
  This is already set in the SDK; confirm you have not overridden it locally.

**`JIUWENSWARM_API_KEY` not picked up**
: The SDK reads environment variables at import time from `os.environ`.
  Export the variable before starting Python, or use `python-dotenv` /
  `load_dotenv()` before importing the SDK.

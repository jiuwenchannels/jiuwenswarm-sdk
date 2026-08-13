# Roadmap

This document tracks every remaining implementation task required to reach
the v1.0.0 release. When the last item here is checked off, the roadmap
section becomes empty and v1.0.0 ships.

Features planned *beyond* v1.0.0 are collected at the bottom under
**Future / v2**.

---

## Phase 4 — TypeScript SDK (`@jiuwenswarm/sdk`)

### Project setup

| Task | File | Done when |
|---|---|---|
| `package.json` with `name`, `main`, `module`, `types`, `exports`, `peerDependencies` | `packages/sdk/package.json` | `npm install` in `packages/sdk/` succeeds |
| `tsconfig.json` | `packages/sdk/tsconfig.json` | `npx tsc --noEmit` passes on the source tree |
| `tsup` for dual CJS + ESM output | `packages/sdk/tsup.config.ts` | `npm run build` produces `dist/index.cjs`, `dist/index.mjs`, `dist/index.d.ts` |
| `vitest` configuration | `packages/sdk/vitest.config.ts` | `npm test` runs and exits cleanly |

### Protocol types and validation

| Task | File | Done when |
|---|---|---|
| `InboundEnvelope`, `OutboundEnvelope`, `SessionInfo`, `AgentMode`, `ChatMessage` | `packages/sdk/src/protocol/types.ts` | Mirrors server protocol exactly; all fields typed |
| `MSG` constants object | `packages/sdk/src/protocol/constants.ts` | All envelope type strings as named constants |
| `parseEnvelope(raw)` | `packages/sdk/src/protocol/validate.ts` | Returns typed envelope or throws `ProtocolError` |
| Unit tests | `packages/sdk/tests/protocol.test.ts` | Valid and invalid payloads all covered |

### EventEmitter

| Task | File | Done when |
|---|---|---|
| Typed `EventEmitter` — no Node.js dependency | `packages/sdk/src/events/EventEmitter.ts` | `on`, `off`, `emit` work in browser and Node.js |
| Unit tests | `packages/sdk/tests/emitter.test.ts` | Register, fire, remove, multiple listeners |

### Reconnect scheduler

| Task | File | Done when |
|---|---|---|
| `ReconnectScheduler` — delay sequence 1→2→5→10→30 s | `packages/sdk/src/client/reconnect.ts` | Tracks attempts; computes delays; calls back at the right time; `cancel()` stops it |
| Unit tests | `packages/sdk/tests/reconnect.test.ts` | Delay sequence verified; cancel stops further callbacks |

### `JiuwenSwarmClient`

| Task | File | Done when |
|---|---|---|
| `connect()` / `disconnect()` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Opens WebSocket; sends `connect` on open; parses incoming envelopes; dispatches events |
| `send(message)` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Sends `chat` envelope; `token` events fire during streaming; `done` fires at end |
| `sendEnvelope(type, payload)` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Low-level send; serialises to JSON |
| `tool_call` auto-rejection | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Any `tool_call` envelope without `onToolCall` returns `{error: "not supported"}` immediately |
| WebSocket detection: browser → Node.js `ws` → `ConnectionError` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Correct adapter chosen at runtime; `ws` is optional peer dep |
| Unit tests (mock WebSocket) | `packages/sdk/tests/client.test.ts` | connect, send, token/done events, tool_call rejection, reconnect on close |

### `SessionManager`

| Task | File | Done when |
|---|---|---|
| `list()`, `create()`, `setActive()`, `refresh()`, `active` getter | `packages/sdk/src/session/SessionManager.ts` | Sessions populated from `sessions` envelope; active session persists across refresh |
| Unit tests | `packages/sdk/tests/session.test.ts` | All methods; active session persists across refresh |

### Barrel export and docs

| Task | File | Done when |
|---|---|---|
| Re-export all public symbols | `packages/sdk/src/index.ts` | `import { JiuwenSwarmClient, SessionManager } from "@jiuwenswarm/sdk"` resolves in CJS and ESM |
| TypeDoc configuration | `packages/sdk/typedoc.json` | `npm run docs` generates HTML in `packages/sdk/docs/` without errors |

### npm publish

| Task | File | Done when |
|---|---|---|
| `publishConfig` in `package.json` | `packages/sdk/package.json` | `npm publish --dry-run` shows correct contents: `dist/`, `README.md`, no `src/` |
| Publish `1.0.0` to registry | — | `npm install @jiuwenswarm/sdk` works from a fresh project |

---

## Project infrastructure

Non-feature tasks required before v1.0.0 ships.

| Task | File | Done when |
|---|---|---|
| `Makefile` with `install`, `test`, `check`, `type-check`, `fix` targets | `Makefile` | All commands referenced in README work out of the box |
| CI pipeline — Python: lint, type-check, unit tests | `.github/workflows/ci-python.yml` | Runs on every PR; fails on lint or test failure |
| CI pipeline — TypeScript: typecheck, vitest, build | `.github/workflows/ci-typescript.yml` | Runs on every PR against `packages/sdk/` |
| Publish pipeline — npm publish `@jiuwenswarm/sdk` on tag | `.github/workflows/publish-npm.yml` | `git tag v1.0.0 && git push --tags` triggers publish |
| `LICENSE` file | `LICENSE` | File exists; content matches `license` field in `pyproject.toml` |
| `.env.example` template | `.env.example` | Every env var from `docs/configuration.md` is listed with a placeholder value and one-line comment |
| TypeScript examples runner setup | `examples/typescript/package.json`, `examples/typescript/tsconfig.json` | `npm install && npx tsx 01_connect_and_chat.ts` runs in `examples/typescript/` |
| Clean `openjiuwen_sdk.egg-info/` from repo | — | Directory removed from git history; `*.egg-info/` confirmed in `.gitignore` |

---

## Future / v2

These features are intentionally deferred past v1.0.0:

| Feature | Reason |
|---|---|
| Migrate browser extension to `@jiuwenswarm/sdk` | Extension works; migration is additive polish |
| Migrate mobile app to `@jiuwenswarm/sdk` | Same — protocol duplication is acceptable for v1 |
| Go / Rust / Java native SDKs | REST API covers these languages adequately |
| Rate limiting and per-token quotas | Requires hosted multi-tenant mode |
| SDK dashboard and usage analytics | Requires hosted mode |
| Webhooks (async result delivery) | SSE covers synchronous use cases; hosted mode needed for fire-and-forget |
| OAuth 2.0 / OIDC in gateway | Requires multi-tenant auth design |
| WebSocket protocol v2 (binary framing, structured tool schemas) | Protocol is frozen at v1 for the lifetime of v1.0.0 |
| `RougeMetric`, `CodeExecutionMetric`, `SemanticSimilarityMetric`, `ToolUsageMetric` | Nice-to-have after ship |

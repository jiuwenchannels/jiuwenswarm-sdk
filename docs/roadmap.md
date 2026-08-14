# Roadmap

This document tracks every remaining implementation task required to reach
the v1.0.0 release. When the last item here is checked off, the roadmap
section becomes empty and v1.0.0 ships.

Features planned *beyond* v1.0.0 are collected at the bottom under
**Future / v2**.

---

> All v1.0.0 implementation tasks are complete. v1.0.0 is ready to ship.
> Run `git tag v1.0.0 && git push --tags` to trigger the publish pipeline.

---

## v2 Roadmap

Phases 1–15 are new work identified from jiuwenswarm, agent-core, and IDE gap analysis.
They are ordered by dependency and value; each is deliberately small-to-medium.
Phases 1–5 are independent of each other and can run in parallel.
Phases 6–7 can run in parallel. Phase 11 requires Phase 1. Phase 12 requires Phase 11.
Phases A–G (existing) follow after all numbered phases are complete.

---

## Phase 1 — E2A Protocol, Stream Control, and Usage Events

Covers the gap between the legacy gateway envelope format and the newer E2A format
already used by jiuwenswarm-ide and jiuwenswarm-jupyterlab.
Unlocks Phase 11 (TypeScript typed events).

### E2A envelope parser

| Task | File | Done when |
|---|---|---|
| `parse_e2a_envelope(env: dict) -> StreamEvent \| None` — handles `response_kind: "e2a.chunk/complete/error"` with `body.event_type` dispatching | `openjiuwen/sdk/core/stream.py` | All E2A chunk types (delta, reasoning, status, tool_call, tool_result, team.\*, done, error) map to the existing `StreamEvent` subclasses; returns `None` for ack/housekeeping |
| Export `parse_e2a_envelope` from `openjiuwen.sdk` and `openjiuwen.sdk.core` | `openjiuwen/sdk/__init__.py`, `openjiuwen/sdk/core/__init__.py` | `from openjiuwen.sdk import parse_e2a_envelope` works |
| Unit tests | `tests/unit/sdk/test_e2a_envelope.py` | All `response_kind` variants; `member_name` forwarded to `TeamEvent.agent_name`; unknown `response_kind` returns `None` |

### Usage events

| Task | File | Done when |
|---|---|---|
| `UsageEvent(StreamEvent)` dataclass: `input_tokens: int`, `output_tokens: int`, `cost_usd: float \| None` | `openjiuwen/sdk/core/stream.py` | Exported from `openjiuwen.sdk`; `type = "usage"` |
| `parse_e2a_envelope` maps `chat.usage_summary` / `chat.usage_metadata` payloads to `UsageEvent` | `openjiuwen/sdk/core/stream.py` | Both E2A and legacy `usage_summary` event types produce `UsageEvent` |
| `agent.on("usage", cb)` emitted by `stream_events()` whenever a `UsageEvent` is received | `openjiuwen/sdk/core/agent.py` | Callback receives `(input_tokens, output_tokens, cost_usd)` |
| Unit tests | `tests/unit/sdk/test_e2a_envelope.py` | `UsageEvent` fields correct; `on("usage")` fires |

### Stream interrupt and bidirectional answer

| Task | File | Done when |
|---|---|---|
| `AgentHandle.interrupt(session_id)` → sends `chat.interrupt` envelope to gateway | `openjiuwen/sdk/_internal/remote_bridge.py` | Fire-and-forget; no response awaited; no-op in in-process mode |
| `Agent.interrupt(session_id=None)` public method | `openjiuwen/sdk/core/agent.py` | `await agent.interrupt()` stops the current stream on the server |
| `Agent.answer(request_id, answers)` public method → sends `chat.answer` envelope | `openjiuwen/sdk/core/agent.py` | Enables bidirectional HITL: server sends `confirm_interrupt`, client replies |
| `connection.ack` handler in `_RemoteBridge.connect()` — stores server-assigned `session_id` | `openjiuwen/sdk/_internal/remote_bridge.py` | `agent.session_id` property available after `Agent.connect()` |
| Unit tests | `tests/unit/sdk/test_stream_control.py` | `interrupt()` sends correct envelope; `answer()` sends correct envelope; ack sets `session_id` |
| Docs | `docs/api-reference.md` | `Agent.interrupt()`, `Agent.answer()`, `UsageEvent`, `parse_e2a_envelope` documented |
| Example | `examples/python/33_interrupt_and_resume.py` | Shows: stream → interrupt mid-stream; then bidirectional confirm_interrupt → answer flow |

---

## Phase 2 — Skill Management API

Exposes `skills.list` and `skills.toggle` gateway methods that jiuwenswarm-ide
uses but are currently invisible to SDK users.

| Task | File | Done when |
|---|---|---|
| `Skill` dataclass: `skill_id: str`, `name: str`, `description: str`, `enabled: bool`, `trigger: str \| None` | `openjiuwen/sdk/core/skills.py` | New file; exported from `openjiuwen.sdk` |
| `AgentHandle.list_skills()` → sends `skills.list` envelope; returns `list[Skill]` | `openjiuwen/sdk/_internal/remote_bridge.py` | Works in remote mode; raises `RuntimeNotAvailableError` in in-process mode |
| `AgentHandle.toggle_skill(skill_id, enabled)` → sends `skills.toggle` | `openjiuwen/sdk/_internal/remote_bridge.py` | Returns updated `Skill` |
| `Agent.list_skills()` and `Agent.toggle_skill(skill_id, enabled)` public methods | `openjiuwen/sdk/core/agent.py` | `await agent.list_skills()` returns `list[Skill]` |
| Unit tests | `tests/unit/sdk/test_skills.py` | List parses response correctly; toggle returns updated skill; in-process mode raises |
| Docs | `docs/api-reference.md` | `Skill` dataclass, `Agent.list_skills()`, `Agent.toggle_skill()` documented |
| Example | `examples/python/34_skill_management.py` | Lists skills, disables one, re-enables; shows TypeScript equivalent snippet in comments |

---

## Phase 3 — Pre-built Tools: Web and Shell

Exposes the web and shell tools already implemented in `openjiuwen.harness.tools`
so SDK users don't have to rewrite them from scratch.

| Task | File | Done when |
|---|---|---|
| `WebFetchTool` — fetches a URL and returns cleaned markdown text; `@tool`-compatible | `openjiuwen/sdk/tools/web.py` | `url: str, timeout_s: float = 30.0` param; strips scripts/styles; returns text |
| `WebSearchTool(provider="free")` — free and paid search variants; returns list of `SearchResult(url, title, snippet)` | `openjiuwen/sdk/tools/web.py` | Provider selectable via param; results capped at `max_results` |
| `BashTool` — runs a shell command in a subprocess; returns stdout+stderr; timeout enforced | `openjiuwen/sdk/tools/shell.py` | `command: str, timeout_s: float = 30.0`; raises `ToolError` on timeout |
| `AskUserTool` — suspends agent and prompts user for input via `confirm_interrupt` mechanism | `openjiuwen/sdk/tools/interaction.py` | `question: str`; integrates with `Agent.answer()` from Phase 1 |
| `openjiuwen.sdk.tools` package `__init__.py` — re-exports all built-in tools | `openjiuwen/sdk/tools/__init__.py` | `from openjiuwen.sdk.tools import WebFetchTool, BashTool, AskUserTool` |
| Export from `openjiuwen.sdk` top-level | `openjiuwen/sdk/__init__.py` | All tools importable from root |
| Unit tests | `tests/unit/sdk/test_tools_web.py`, `test_tools_shell.py` | Fetch mock URL; search returns results; bash runs command; timeout kills process |
| Docs | `docs/api-reference.md` | New `## Built-in Tools` section with table of all tools |
| Example | `examples/python/35_builtin_tools.py` | Agent with `WebFetchTool` + `BashTool`; shows one-liner tool attachment |

---

## Phase 4 — Pre-built Tools: File System and Productivity

| Task | File | Done when |
|---|---|---|
| `ListDirTool` — lists directory contents with optional depth; `GlobTool` — finds files by pattern | `openjiuwen/sdk/tools/fs.py` | `path: str, depth: int = 1`; returns JSON list of entries with type/size |
| `TodoCreateTool`, `TodoListTool`, `TodoModifyTool` — in-session task tracking | `openjiuwen/sdk/tools/todo.py` | Stored in session metadata; survives across turns |
| `SendFileTool` — marks a file as a deliverable; returns download URL or path | `openjiuwen/sdk/tools/fs.py` | `file_path: str, display_name: str \| None`; raises `ToolError` if file does not exist |
| `SubagentSpawnTool`, `SubagentListTool`, `SubagentCancelTool` — launch and manage sub-agents | `openjiuwen/sdk/tools/subagent.py` | Spawn returns a `SubagentHandle` with `session_id`; integrates with `Session` |
| Add all tools to `openjiuwen.sdk.tools` exports | `openjiuwen/sdk/tools/__init__.py` | Single import point |
| Unit tests | `tests/unit/sdk/test_tools_fs.py`, `test_tools_todo.py` | Dir listing; glob patterns; todo CRUD; subagent spawn mocked |
| Example | `examples/python/36_filesystem_tools.py` | Agent that lists a directory, creates todos, spawns a subagent |

---

## Phase 5 — Pre-built Tools: Multimodal

| Task | File | Done when |
|---|---|---|
| `ImageOCRTool` — extracts text from an image file or URL | `openjiuwen/sdk/tools/multimodal.py` | `image: str` (path or URL); returns extracted text string |
| `VisualQuestionAnsweringTool` — answers a natural-language question about an image | `openjiuwen/sdk/tools/multimodal.py` | `image: str, question: str`; delegates to configured vision model |
| `AudioTranscriptionTool` — transcribes audio to text | `openjiuwen/sdk/tools/multimodal.py` | `audio: str` (path or URL); uses configured speech model |
| `AudioQuestionAnsweringTool` — answers a question about audio content | `openjiuwen/sdk/tools/multimodal.py` | `audio: str, question: str` |
| Factory helpers: `create_vision_tools()`, `create_audio_tools()` — return pre-configured lists | `openjiuwen/sdk/tools/multimodal.py` | Shortcut for `Agent.create(tools=create_vision_tools())` |
| Unit tests (mock model responses) | `tests/unit/sdk/test_tools_multimodal.py` | Each tool with mocked model call; factory lists contain correct tools |
| Docs + example | `docs/api-reference.md`, `examples/python/37_multimodal_tools.py` | Documented in Built-in Tools section; example shows image + audio pipeline |

---

## Phase 6 — Advanced Retrieval and Chunking

Exposes `HybridRetriever`, rerankers, and chunking strategies from
`openjiuwen.core.retrieval` that the basic SDK RAG does not reach.

| Task | File | Done when |
|---|---|---|
| `HybridRetriever(kb, bm25_weight=0.3)` — combines vector and BM25 sparse retrieval with RRF fusion | `openjiuwen/sdk/knowledge/retrieval.py` | Extends `Retriever` protocol; `retrieve(query, top_k)` returns fused `RetrievalResult` list |
| `ChatReranker` and `StandardReranker` — re-rank candidates using LLM or cross-encoder model | `openjiuwen/sdk/knowledge/retrieval.py` | `rerank(query, results)` returns sorted `RetrievalResult` list |
| `QueryRewriter` — transforms user query before retrieval (HyDE, step-back, etc.) | `openjiuwen/sdk/knowledge/retrieval.py` | `rewrite(query, strategy="hyde")` returns transformed query string |
| `HybridChunker(chunk_size, overlap)`, `TokenizerChunker(model)` | `openjiuwen/sdk/knowledge/chunking.py` | Implement `Chunker` protocol; usable in `KnowledgeBase.add_documents(chunker=...)` |
| `PreprocessingPipeline([URLEmailRemover(), WhitespaceNormalizer(), ...])` | `openjiuwen/sdk/knowledge/chunking.py` | Composable text preprocessors; applied before chunking |
| Export from `openjiuwen.sdk` and `openjiuwen.sdk.knowledge` | `__init__.py` files | All new classes importable |
| Unit tests | `tests/unit/sdk/test_hybrid_retrieval.py`, `test_chunking.py` | Hybrid fusion correct; reranker sorts by score; pipeline applies normalizers in order |
| Docs + example | `docs/api-reference.md`, `examples/python/38_hybrid_retrieval.py` | New retrieval section; example with HybridRetriever + ChatReranker |

---

## Phase 7 — Advanced Memory Types

Bridges the gap between the basic `add/search/clear` memory interface and the
richer memory modes in `openjiuwen.core.memory`.

| Task | File | Done when |
|---|---|---|
| `TripleMemory` — knowledge-graph-style memory: `add_triple(subject, predicate, object)`, `query_triples(subject)` | `openjiuwen/sdk/knowledge/memory.py` | Extends `Memory` base; stores and retrieves SPO triples |
| `TeamMemory(scope="team")` — shared memory readable/writable by all members of a team | `openjiuwen/sdk/knowledge/memory.py` | Passed to `Team.create(shared_memory=...)` |
| `DreamingMemory` — replays past sessions to synthesize new memory entries (background task) | `openjiuwen/sdk/knowledge/memory.py` | `await DreamingMemory.consolidate(sessions)` |
| `ExternalMemoryConfig(provider_url, auth_token)` — pluggable external memory backend | `openjiuwen/sdk/knowledge/memory.py` | Passed to `make_memory(external=ExternalMemoryConfig(...))` |
| `MemoryEngineConfig` — unified config for memory backend, search mode, token budget | `openjiuwen/sdk/knowledge/memory.py` | Fields: `backend`, `search_mode: "vector" \| "bm25" \| "hybrid"`, `max_tokens` |
| Unit tests | `tests/unit/sdk/test_advanced_memory.py` | Triple add/query round-trip; team memory shared across agent handles; dreaming mock |
| Docs + example | `docs/api-reference.md`, `examples/python/39_advanced_memory.py` | TripleMemory usage; team memory in multi-agent context |

---

## Phase 8 — Context Engine Processors

Exposes the concrete processor implementations so developers can build custom
context compression strategies rather than just using the defaults.

| Task | File | Done when |
|---|---|---|
| `MessageSummaryOffloader(threshold_tokens, summary_model)` — summarizes old messages when context exceeds threshold | `openjiuwen/sdk/control/context.py` | Implements `ContextProcessor` protocol; `process(messages, token_count)` returns trimmed list |
| `DialogueCompressor`, `FullCompactProcessor` — aggressive compression modes | `openjiuwen/sdk/control/context.py` | `CompactionMode.DIALOGUE` (per-turn summary) and `FULL` (entire context → one summary) |
| `ToolResultBudgetProcessor(max_tokens_per_result)` — truncates oversized tool outputs | `openjiuwen/sdk/control/context.py` | Truncates `tool_result` messages that exceed budget; appends `[truncated]` marker |
| `TokenCounter` — standalone token counting utility; model-aware | `openjiuwen/sdk/control/context.py` | `count(text, model="gpt-4o")` returns int; exported from `openjiuwen.sdk` |
| `ContextEngine.compose([proc1, proc2, ...])` class method — builds pipeline from list | `openjiuwen/sdk/control/context.py` | Simplifies multi-processor chains |
| Unit tests | `tests/unit/sdk/test_context_processors.py` | Each processor reduces token count correctly; truncation adds marker; `TokenCounter` matches tiktoken |
| Docs + example | `docs/api-reference.md`, `examples/python/40_context_processors.py` | Updated Context Engine section; example with custom compression pipeline |

---

## Phase 9 — Full Team Coordination API

Extends `Team` beyond basic `spawn()` and `stream()` to expose declarative
team specs, supervisor streams, and external team integration.

| Task | File | Done when |
|---|---|---|
| `TeamMemberSpec(name, role, system_prompt, tools, model)` — declarative member definition | `openjiuwen/sdk/agents/team.py` | Dataclass; used in `TeamSpec` |
| `TeamSpec(name, members, leader_model, mode)` — full team definition; passed to `Team.from_spec()` | `openjiuwen/sdk/agents/team.py` | `Team.from_spec(spec)` async class method creates the team |
| `team.subscribe(role="godview")` — returns `AsyncIterator[StreamEvent]` with all member outputs visible | `openjiuwen/sdk/agents/team.py` | GodView stream includes `TeamEvent` for every member; useful for monitoring dashboards |
| `team.cancel()` — coordinated cancellation across all running members | `openjiuwen/sdk/agents/team.py` | Sends `chat.interrupt` to all active member sessions; waits for clean shutdown |
| `ExternalTeamClient(server_url, team_name)` — connects to a team running in a remote gateway | `openjiuwen/sdk/agents/team.py` | `await ExternalTeamClient.connect(...)` returns a `Team`-compatible handle |
| Unit tests | `tests/unit/sdk/test_team_coordination.py` | `from_spec()` builds team with correct members; `cancel()` interrupts all; `subscribe()` yields all events |
| Docs + example | `docs/api-reference.md`, `examples/python/41_team_spec.py` | Updated Team section with `TeamSpec`; example with declarative spec + godview stream |

---

## Phase 10 — Agent Training Framework

Thin façade over `openjiuwen.agent_evolving` to expose prompt optimization,
signal detection, and training loops to SDK users.

| Task | File | Done when |
|---|---|---|
| `TrainingCase(prompt, expected_output, metadata)` and `TrainingDataset(cases)` | `openjiuwen/sdk/optimize/training.py` | Dataclasses; `TrainingDataset.from_jsonl(path)` loader |
| `InstructionOptimizer(agent, metric, n_iterations)` — improves agent's system prompt by running eval on `TrainingDataset` | `openjiuwen/sdk/optimize/training.py` | `.optimize(dataset)` returns `OptimizationResult(best_prompt, score_history)` |
| `ConversationSignalDetector` — detects implicit feedback signals in conversation history (corrections, praise, repetition) | `openjiuwen/sdk/optimize/training.py` | `.detect(session)` returns `list[EvolutionSignal(category, target, strength)]` |
| `SkillExperienceOptimizer(skill_path)` — improves a skill by replaying failures | `openjiuwen/sdk/optimize/training.py` | `.optimize(failure_log)` rewrites skill based on observed errors |
| Export from `openjiuwen.sdk` | `openjiuwen/sdk/__init__.py` | All training types importable from root |
| Unit tests (mock LLM calls) | `tests/unit/sdk/test_training.py` | Optimizer runs N iterations; signal detector identifies correction patterns; dataset loads from JSONL |
| Docs + example | `docs/api-reference.md`, `examples/python/42_training.py` | New `## Agent Training` section; example with `InstructionOptimizer` + eval metric |

---

## Phase 11 — TypeScript SDK: Typed Stream Events

Mirrors Phase 1's `StreamEvent` hierarchy in TypeScript so browser and Node
clients get the same typed observability as Python users.
Requires Phase 1 (E2A parser contract and event types must be stable).

| Task | File | Done when |
|---|---|---|
| `StreamEvent` discriminated union type + all subtypes: `DeltaEvent`, `ReasoningEvent`, `StatusEvent`, `ToolCallEvent`, `ToolResultEvent`, `TeamEvent`, `UsageEvent`, `DoneEvent`, `ErrorEvent` | `packages/sdk/src/protocol/events.ts` | Fully typed; `event.type` narrows the union |
| `parseStreamEvent(envelope: Record<string, unknown>): StreamEvent \| null` — handles both legacy and E2A format | `packages/sdk/src/protocol/events.ts` | Same dispatch logic as Python `parse_e2a_envelope` + `parse_gateway_envelope` |
| `client.streamEvents(prompt, options?): AsyncIterable<StreamEvent>` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Wraps existing `stream()` and applies `parseStreamEvent` to each envelope |
| `client.interrupt()` — sends `chat.interrupt` envelope | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Fire-and-forget; resolves immediately |
| Unit tests | `packages/sdk/tests/stream_events.test.ts` | Each event type parsed correctly; `interrupt()` sends correct payload |
| TypeScript example | `examples/typescript/07_stream_events.ts` | Shows `switch(event.type)` pattern mirroring the Python §31 example |

---

## Phase 12 — TypeScript SDK: Team Events, Skills, and HITL

Requires Phase 11 (typed events must exist before team events can be typed).

| Task | File | Done when |
|---|---|---|
| `TeamEvent` subtypes with team-specific `type` values: `"team.member.spawned"`, `"team.member.status_changed"`, `"team.task.created"`, `"team.task.completed"`, `"team.handoff"` | `packages/sdk/src/protocol/events.ts` | All values from IDE's `SwarmStateManager` covered |
| `SwarmStateManager` class — tracks live team state from a `streamEvents()` feed | `packages/sdk/src/swarm/SwarmStateManager.ts` | `members: Map<string, MemberState>`, `tasks: Map<string, TaskState>`; emits `"member_update"` / `"task_update"` events |
| `client.listSkills(): Promise<Skill[]>`, `client.toggleSkill(id, enabled): Promise<Skill>` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Mirrors Python Phase 2 |
| `client.sendAnswer(requestId, answers): Promise<void>` — HITL reply to `confirm_interrupt` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Used when server suspends for human confirmation |
| Unit tests | `packages/sdk/tests/team_events.test.ts`, `skills.test.ts` | `SwarmStateManager` updates on team events; skill toggle returns updated object |
| TypeScript examples | `examples/typescript/08_team_events.ts`, `examples/typescript/09_skills_and_hitl.ts` | Team stream with live member status display; skills list + toggle + HITL answer |

---

## Phase 13 — REST API: Extended Endpoints and Examples

| Task | File | Done when |
|---|---|---|
| `POST /v1/teams/{name}/run` — trigger a named team with a prompt; returns `{session_id, output}` | `openjiuwen/gateway/rest/teams.py` | Blocking endpoint; team identified by name registered in agent registry |
| `GET /v1/agents/{name}/skills` — list skills for a named agent | `openjiuwen/gateway/rest/agents.py` | Returns `[{skill_id, name, description, enabled, trigger}]` |
| `POST /v1/agents/{name}/skills/{id}/toggle` — enable or disable a skill | `openjiuwen/gateway/rest/agents.py` | Body: `{"enabled": bool}`; returns updated skill object |
| `POST /v1/sessions/{id}/interrupt` — stop an active session | `openjiuwen/gateway/rest/sessions.py` | Returns `204`; idempotent if session already done |
| `GET /v1/sessions/{id}/usage` — token and cost summary for a session | `openjiuwen/gateway/rest/sessions.py` | Returns `{input_tokens, output_tokens, cost_usd, turn_count}` |
| Unit tests | `tests/unit/gateway/test_rest_extended.py` | Each new endpoint; 404 for unknown agents/sessions |
| REST examples | `examples/rest/10_team_run.sh`, `examples/rest/11_skills.sh`, `examples/rest/12_interrupt_and_usage.sh` | cURL demonstrations of each new endpoint |
| Update `examples/README.md` | `examples/README.md` | New REST rows added to table |

---

## Phase 14 — Docs and Examples Reorganization

No code changes. Purely structural improvements to the example tree and docs.
Can run in parallel with any other phase.

| Task | File | Done when |
|---|---|---|
| Create subfolders under `examples/python/`: `core/`, `agents/`, `workflow/`, `memory_knowledge/`, `optimization/`, `observability/`, `infra/`, `advanced/` | `examples/python/` | All 42 examples moved to appropriate subfolders; symlinks or redirects for any old paths |
| Update `examples/README.md` — grouped table by subfolder with section headers | `examples/README.md` | Replaces flat table; navigable by topic |
| Update `docs/contributing.md` — new example folder structure | `docs/contributing.md` | `examples/python/` layout diagram updated |
| Add `stream.py` and `mode.py` to module layout in `docs/rat_sig/SIG.md` | `docs/rat_sig/SIG.md` | Module table row for each new file with one-line description |
| Add Phase 1–13 capabilities to `docs/rat_sig/RAT.md` demand section | `docs/rat_sig/RAT.md` | New subsection "Extended Requirements (v2)" listing each phase's motivation |
| Add `docs/rat_sig/SIG.md` module layout section for new SDK modules: `tools/`, `knowledge/retrieval.py`, `knowledge/chunking.py`, `optimize/training.py`, `agents/swarm_state.py` | `docs/rat_sig/SIG.md` | Each new file in the bridge table |

---

## Phase 15 — Symphony Capability Orchestration (Facade)

Lightweight façade over `openjiuwen.symphony` for skill-graph-based routing.
This is architecturally significant but deliberately scoped narrow for v2.

| Task | File | Done when |
|---|---|---|
| `SymphonyConfig(skills_dir, llm_model, cache_dir)` — configuration for the skill graph | `openjiuwen/sdk/symphony.py` | Dataclass; `from_env()` reads `JIUWENSWARM_SKILLS_DIR` |
| `Symphony.build(config)` async class method — scans `skills_dir`, fingerprints capabilities, builds graph | `openjiuwen/sdk/symphony.py` | Returns `Symphony` instance; progress callback optional |
| `symphony.retrieve(query, top_k=5)` — returns ranked list of `CapabilityMatch(name, score, description)` | `openjiuwen/sdk/symphony.py` | Uses `openjiuwen.symphony.retrieval.Retriever` under the hood |
| `symphony.route(prompt)` — selects best skill for a prompt and returns its callable | `openjiuwen/sdk/symphony.py` | Returns `Callable[[str], Awaitable[str]]` |
| Export from `openjiuwen.sdk` | `openjiuwen/sdk/__init__.py` | `from openjiuwen.sdk import Symphony, SymphonyConfig` |
| Unit tests (mock scanner and retriever) | `tests/unit/sdk/test_symphony.py` | Build with mock skills dir; retrieve returns sorted candidates; route calls selected skill |
| Docs + example | `docs/api-reference.md`, `examples/python/43_symphony.py` | New `## Symphony` section; example with skills dir, build, and route |

---

## Phase A — Additional Evaluation Metrics

Independent of Phases 1–15. No infrastructure dependencies. Adds to the existing
`openjiuwen/sdk/optimize/eval.py` module and the `MetricEvaluator` pipeline.

### `RougeMetric`

| Task | File | Done when |
|---|---|---|
| `RougeMetric(variants=["rouge1","rouge2","rougeL"])` using `rouge-score` library | `openjiuwen/sdk/optimize/eval.py` | Returns per-variant F1 scores; `passed` when mean F1 ≥ threshold |
| Add `rouge-score` to `[optimize]` optional extra | `pyproject.toml` | `pip install openjiuwen-sdk[optimize]` installs it |
| Unit tests | `tests/unit/sdk/test_eval_rouge.py` | 5+ cases: exact match, partial overlap, empty string, multi-sentence |

### `SemanticSimilarityMetric`

| Task | File | Done when |
|---|---|---|
| `SemanticSimilarityMetric(model="text-embedding-3-small", threshold=0.85)` | `openjiuwen/sdk/optimize/eval.py` | Computes cosine similarity between `expected` and `prediction` embeddings via the SDK's configured LLM provider; `passed` when similarity ≥ threshold |
| Lazy embedding call — only invoked during `evaluate()`, not at construction | `openjiuwen/sdk/optimize/eval.py` | No API call on `SemanticSimilarityMetric()` |
| Unit tests (mock embedding responses) | `tests/unit/sdk/test_eval_semantic.py` | Tests for high-similarity pass, low-similarity fail, threshold boundary |

### `ToolUsageMetric`

| Task | File | Done when |
|---|---|---|
| `ToolUsageMetric(required=["tool_a"], forbidden=["tool_b"])` | `openjiuwen/sdk/optimize/eval.py` | Inspects `EvalCase.metadata["tool_calls"]` list; fails if required tool absent or forbidden tool present |
| `EvalCase.metadata` schema for tool call recording | `openjiuwen/sdk/optimize/eval.py` | `{"tool_calls": [{"name": str, "args": dict, "result": str}]}` — documented |
| Unit tests | `tests/unit/sdk/test_eval_tool_usage.py` | Required present, required missing, forbidden present, empty call list |

### `CodeExecutionMetric`

| Task | File | Done when |
|---|---|---|
| `CodeExecutionMetric(language="python", timeout_s=5)` | `openjiuwen/sdk/optimize/eval.py` | Extracts fenced code block from `prediction`; executes in subprocess with `sys.executable`; compares stdout to `expected` |
| Sandboxing: subprocess runs with `resource` limits (max RSS, CPU time) on POSIX; `subprocess` timeout on all platforms | `openjiuwen/sdk/optimize/eval.py` | Runaway code is killed; `passed=False` with `error="timeout"` |
| Unit tests | `tests/unit/sdk/test_eval_code.py` | Correct output passes; wrong output fails; infinite loop times out; syntax error fails gracefully |

---

## Phase B — WebSocket Protocol v2

Introduces binary framing (MessagePack) and structured tool schemas.
Fully backwards-compatible: clients negotiate via the `connect` envelope.
Must be complete before Phase G (native SDKs) begins.

### Server-side (Python gateway)

| Task | File | Done when |
|---|---|---|
| Add `msgpack>=1.0` to `[gateway]` optional extra | `pyproject.toml` | Installed with gateway |
| `protocol_version` field in `connect` envelope: `"1"` (JSON) or `"2"` (msgpack) | `openjiuwen/gateway/ws/dispatcher.py` | Server reads the field and stores preferred encoding on `ConnectionState` |
| Binary WS frames: encode all outbound envelopes with msgpack when client requested v2 | `openjiuwen/gateway/ws/router.py` | `websocket.send_bytes(msgpack.packb(env))` for v2 clients; `send_text` for v1 |
| Receive binary frames from v2 clients | `openjiuwen/gateway/ws/router.py` | `websocket.iter_bytes()` for v2 path; existing text path for v1 |
| Structured tool schema in `tool_call` envelope: `parameters` follows JSON Schema draft-07 | `openjiuwen/gateway/ws/dispatcher.py` | `tool_call` includes `{"parameters": {"type":"object","properties":{...},"required":[...]}}` |
| Unit tests | `tests/unit/gateway/test_ws_v2.py` | v1 client gets text frames; v2 client gets binary frames; tool schema present |

### Client-side (TypeScript SDK)

| Task | File | Done when |
|---|---|---|
| Add `@msgpack/msgpack` dependency | `packages/sdk/package.json` | `npm install` succeeds |
| `ClientConfig.protocolVersion: 1 \| 2` (default: `1`) | `packages/sdk/src/protocol/types.ts` | Existing clients unaffected |
| Send `protocol_version: "2"` in `connect` envelope when configured | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Field present in the connect JSON payload |
| Switch to `ws.binaryType = "arraybuffer"` and msgpack decode when v2 | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Binary frames decoded correctly; `parseEnvelope` accepts `ArrayBuffer \| string` |
| `ToolCallEnvelope.parameters` typed as JSON Schema object | `packages/sdk/src/protocol/types.ts` | Field present in type; not present for v1 tool calls |
| Unit tests | `packages/sdk/tests/ws_v2.test.ts` | v2 client decodes msgpack; `parameters` field accessible |

---

## Phase C — OAuth 2.0 / OIDC in Gateway

Prerequisite for all hosted-mode features (D, E, F).
Introduces the concept of an authenticated **user** owning sessions and agents.

### OIDC discovery and token validation

| Task | File | Done when |
|---|---|---|
| `OAuthConfig` dataclass: `issuer_url`, `client_id`, `audience`, `jwks_cache_ttl_s` | `openjiuwen/gateway/config.py` | Integrated into `GatewayConfig` alongside existing `auth_token` |
| `JWKSCache` — fetches and caches JWKS from `{issuer_url}/.well-known/jwks.json` | `openjiuwen/gateway/auth.py` | Refreshes on TTL expiry; thread-safe |
| `OAuthMiddleware` — validates `Authorization: Bearer <jwt>` using JWKS; extracts `sub`, `email`, `scope` | `openjiuwen/gateway/auth.py` | Invalid/expired JWT → 401; missing → 401 (unless `auth=None`); sets `request.state.user` |
| `request.state.user: UserContext` — `{sub: str, email: str \| None, scopes: list[str]}` | `openjiuwen/gateway/auth.py` | Available in all route handlers |
| Unit tests (RS256 JWT fixture, mock JWKS endpoint) | `tests/unit/gateway/test_oauth.py` | Valid token passes; expired fails; wrong audience fails; missing fails |

### Session and agent isolation

| Task | File | Done when |
|---|---|---|
| `SessionStore` and `CheckpointStore` keyed by `(user_sub, id)` — users cannot access each other's sessions | `openjiuwen/gateway/_registry.py` | `GET /v1/sessions` returns only the caller's sessions |
| `AgentRegistry` per-user lazy instantiation | `openjiuwen/gateway/_registry.py` | Each user gets an isolated agent instance; no shared state across users |
| Update all REST routes to pass `user.sub` into store operations | `openjiuwen/gateway/rest/*.py` | 404 returned when accessing another user's resource (not 403, to avoid enumeration) |
| Unit tests | `tests/unit/gateway/test_user_isolation.py` | User A cannot read, modify, or delete User B's sessions, checkpoints, or knowledge bases |

### WS gateway user identity

| Task | File | Done when |
|---|---|---|
| `connect` envelope accepts `token` field (JWT) for browser clients that cannot set headers | `openjiuwen/gateway/ws/dispatcher.py` | Token validated on `connect`; `ConnectionState.user` populated |
| Reject `chat`/`create_session` before a valid `connect` when OAuth is enabled | `openjiuwen/gateway/ws/dispatcher.py` | Server sends `{"type":"error","message":"not authenticated"}` |
| Unit tests | `tests/unit/gateway/test_ws_auth.py` | Unauthenticated chat rejected; authenticated passes; wrong token rejected |

---

## Phase D — Rate Limiting and Per-Token Quotas

Requires Phase C (user identity). Requires a Redis instance for shared counters.

### Infrastructure

| Task | File | Done when |
|---|---|---|
| Add `redis[asyncio]>=5.0` to `[gateway]` optional extra | `pyproject.toml` | Installed with gateway |
| `RateLimitConfig` in `GatewayConfig`: `requests_per_minute`, `tokens_per_day`, `redis_url` | `openjiuwen/gateway/config.py` | Merged into gateway startup |
| `RedisCounterStore` — async increment/get/expire wrappers around `redis.asyncio` | `openjiuwen/gateway/ratelimit.py` | Key pattern: `rl:{user_sub}:rpm` and `rl:{user_sub}:tpd` |

### Request-level limiting

| Task | File | Done when |
|---|---|---|
| `RateLimitMiddleware` — checks + increments `requests_per_minute` counter; returns 429 with `Retry-After` header on exceed | `openjiuwen/gateway/ratelimit.py` | Sliding window (60 s TTL); applies to all `/v1/` routes except `/v1/health` |
| Unit tests (mock Redis) | `tests/unit/gateway/test_ratelimit.py` | Under limit passes; over limit → 429; header present |

### Token-level quotas

| Task | File | Done when |
|---|---|---|
| Token counter hook in streaming routes: count tokens emitted per response | `openjiuwen/gateway/rest/sessions.py`, `agents.py` | Each SSE token and WS `token` envelope increments `rl:{user_sub}:tpd` |
| `GET /v1/usage` — returns `{requests_today, tokens_today, quota_requests, quota_tokens}` | `openjiuwen/gateway/rest/usage.py` | Values read from Redis; resets at UTC midnight |
| 429 when daily token quota exceeded mid-stream: send error envelope, close stream | `openjiuwen/gateway/rest/sessions.py` | Partial response with error at quota boundary |
| Unit tests | `tests/unit/gateway/test_token_quota.py` | Under quota streams fully; over quota mid-stream gets error |

---

## Phase E — Webhooks

Requires Phase C (user identity) for ownership. Requires Phase D Redis for job queuing
(or a standalone queue; ARQ recommended as it builds on the existing Redis dep).

### Webhook registration

| Task | File | Done when |
|---|---|---|
| `WebhookSpec` model: `url`, `events: list[str]`, `secret: str` | `openjiuwen/gateway/webhooks.py` | Validated with pydantic; secret min 16 chars enforced |
| `POST /v1/webhooks` — register a webhook for the authenticated user | `openjiuwen/gateway/rest/webhooks.py` | Stored per-user in Redis (`wh:{user_sub}:{id}`); 201 response |
| `GET /v1/webhooks` — list user's webhooks | `openjiuwen/gateway/rest/webhooks.py` | Returns array; secret field masked (`wh_***`) |
| `DELETE /v1/webhooks/{id}` | `openjiuwen/gateway/rest/webhooks.py` | 204 on success; 404 if not owned by caller |
| Unit tests | `tests/unit/gateway/test_webhooks_crud.py` | CRUD lifecycle; secret masking; wrong-user 404 |

### Event delivery

| Task | File | Done when |
|---|---|---|
| ARQ worker task `deliver_webhook(event, payload, webhook_id)` — POST to `url` with `X-JiuwenSwarm-Signature: sha256=...` HMAC header | `openjiuwen/gateway/workers/webhook_worker.py` | Delivery attempted; 2xx = success; non-2xx = retry |
| Retry schedule: 30 s → 5 min → 30 min → 2 h → give up after 5 attempts | `openjiuwen/gateway/workers/webhook_worker.py` | Each failure re-enqueues with backoff; `dead_letter` key written on final failure |
| Events fired on: `session.done`, `agent.run.done`, `checkpoint.saved`, `eval.batch.done` | Gateway route files | `arq.create_pool` enqueue after each gateway operation |
| `GET /v1/webhooks/{id}/deliveries` — last 50 delivery attempts with status and response code | `openjiuwen/gateway/rest/webhooks.py` | Stored in Redis list; capped at 50 per webhook |
| Unit tests (mock httpx, mock ARQ) | `tests/unit/gateway/test_webhook_delivery.py` | Signature correct; retry on 500; no retry on 200; dead letter after 5 |

---

## Phase F — SDK Dashboard and Usage Analytics

Requires Phase C (auth), Phase D (usage counters), Phase E (webhook events).
Delivers a self-hosted web UI served by the gateway.

### Analytics backend

| Task | File | Done when |
|---|---|---|
| `AnalyticsEvent` — written to Redis Stream (`analytics:{user_sub}`) on each gateway operation | `openjiuwen/gateway/analytics.py` | Fields: `event`, `timestamp`, `session_id`, `agent_id`, `token_count`, `latency_ms` |
| `GET /v1/analytics/summary` — aggregated counts for `[from, to]` range: total requests, total tokens, p50/p95 latency, top agents | `openjiuwen/gateway/rest/analytics.py` | Reads from Redis Stream with `XRANGE`; computed in-process |
| `GET /v1/analytics/timeseries` — per-hour or per-day bucketed token + request counts | `openjiuwen/gateway/rest/analytics.py` | Returns `{timestamps: [], requests: [], tokens: []}` arrays |
| Unit tests (mock Redis Stream) | `tests/unit/gateway/test_analytics.py` | Aggregation correct; date range filtering works |

### Dashboard frontend

| Task | File | Done when |
|---|---|---|
| Single-page dashboard: `GET /dashboard` serves static HTML + JS bundle | `openjiuwen/gateway/dashboard/` | Built with Vite + vanilla TS (no framework dependency); bundled into the Python package |
| Session list view: title, agent, created time, message count | Dashboard | Fetches `GET /v1/sessions` |
| Usage chart: token consumption over time (last 7 days) | Dashboard | Fetches `/v1/analytics/timeseries`; renders with `Chart.js` |
| Webhook management UI: list, create, delete, delivery log | Dashboard | CRUD against `/v1/webhooks` |
| Auth flow: OIDC login button → redirect → JWT stored in `sessionStorage` | Dashboard | Works with any OIDC provider configured in `OAuthConfig` |
| `dashboard` optional extra: `pip install openjiuwen-sdk[gateway,dashboard]` includes built assets | `pyproject.toml` | Assets in `openjiuwen/gateway/dashboard/dist/` included in wheel |

---

## Phase G — Native SDKs (Go, Rust, Java)

Start after Phase B (WS protocol v2) is merged and stable.
All three implement the same WS v2 envelope protocol and REST client.
Each lives in a separate repository / package namespace.

### Go SDK (`github.com/jiuwenswarm/sdk-go`)

| Task | File | Done when |
|---|---|---|
| Module scaffold: `go.mod`, `go.sum` | `sdk-go/` | `go build ./...` succeeds |
| `Envelope` types and msgpack codec | `sdk-go/protocol/` | Encode/decode round-trips match Python reference |
| `Client` struct: `Connect()`, `Disconnect()`, `Send()`, `SendEnvelope()` | `sdk-go/client/client.go` | Connect/disconnect lifecycle; streaming via channel `<-chan string` |
| `SessionManager`: `List()`, `Create()`, `SetActive()`, `Refresh()`, `Active()` | `sdk-go/session/manager.go` | Mirrors Python/TS API |
| Auto-reconnect with exponential back-off | `sdk-go/client/reconnect.go` | Same delay sequence; context-cancellable |
| Unit tests | `sdk-go/*_test.go` | Mock WS server using `nhooyr.io/websocket`; all lifecycle paths covered |
| `go get github.com/jiuwenswarm/sdk-go` works | CI | Published to pkg.go.dev |

### Rust SDK (`crates.io/jiuwenswarm-sdk`)

| Task | File | Done when |
|---|---|---|
| Crate scaffold: `Cargo.toml`, `src/lib.rs` | `sdk-rust/` | `cargo build` succeeds |
| Envelope types with `serde` + `rmp-serde` (msgpack) | `sdk-rust/src/protocol.rs` | Derive `Serialize`/`Deserialize`; round-trip test passes |
| Async `Client` with `tokio-tungstenite` | `sdk-rust/src/client.rs` | `client.connect().await`; `client.send(msg).await` returns `impl Stream<Item=String>` |
| `SessionManager` | `sdk-rust/src/session.rs` | Same API shape as Go/TS |
| Auto-reconnect using `tokio::time::sleep` | `sdk-rust/src/client.rs` | Configurable back-off; cancellable via `CancellationToken` |
| Unit tests + doc tests | `sdk-rust/tests/` | Mock WS server with `tokio::net::TcpListener`; all paths |
| Published to `crates.io` | CI | `cargo add jiuwenswarm-sdk` works |

### Java SDK (`com.jiuwenswarm:sdk`)

| Task | File | Done when |
|---|---|---|
| Gradle project: `build.gradle.kts`, `settings.gradle.kts` | `sdk-java/` | `./gradlew build` succeeds |
| Envelope types with `jackson-dataformat-msgpack` | `sdk-java/src/main/java/.../protocol/` | Codec round-trip test passes |
| `JiuwenSwarmClient` using Java 21 virtual threads + `java.net.http.HttpClient` WebSocket API | `sdk-java/src/main/java/.../client/JiuwenSwarmClient.java` | `connect()` returns `CompletableFuture<Void>`; `send()` returns `CompletableFuture<Void>` with `Consumer<String>` token callback |
| `SessionManager` | `sdk-java/src/main/java/.../session/SessionManager.java` | Same lifecycle as Go/Rust/TS |
| Auto-reconnect using `ScheduledExecutorService` | `sdk-java/src/main/java/.../client/` | Configurable delays; `close()` cancels |
| Unit tests with JUnit 5 + WireMock | `sdk-java/src/test/` | All client lifecycle paths |
| Published to Maven Central | CI | `implementation("com.jiuwenswarm:sdk:2.0.0")` resolves |

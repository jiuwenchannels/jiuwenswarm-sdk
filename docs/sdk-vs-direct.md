# openjiuwen SDK vs openjiuwen (direct)

## What you're looking at

This document answers one question: **what does the `openjiuwen.sdk` façade
actually buy you over calling the underlying `openjiuwen` runtime directly?**

`openjiuwen` (agent-core) is the engine that powers JiuwenSwarm — it exposes
agents, tools, teams, workflows, memory, and retrieval, but as a set of raw
primitives: `ReActAgent`, `Runner`, `TeamAgentSpec`, the `swarmflow` workflow
DSL, and so on. These primitives are powerful, but they are not ergonomic. A
simple "run an agent and get an answer" takes ten lines of model plumbing before
you write a single word of your actual task.

The SDK is a thin, opinionated façade over those primitives. It does not add new
capabilities — it removes friction. Every example below is the *same task* shown
two ways:

- **Left column — `openjiuwen.sdk`:** the intent. A few lines that say what you
  want, in the way a developer naturally thinks about it.
- **Right column — `openjiuwen` (direct):** the cost of doing the same thing
  without the SDK, using the real agent-core APIs that exist today.

The gap between the two columns is the SDK's entire value proposition.

## How to read this

Every task in this document is drawn from a concrete developer need: single-agent
Q&A, web search, code review, multi-agent pipelines, memory, custom tools, bug
fixing, RAG, and multi-agent orchestration. Twelve tasks, each demonstrating
where the SDK's abstraction is thin (and where it isn't).

**Models throughout:** `gpt-4o` (OpenAI).

> Note on model plumbing: the direct path has no `model="openai/gpt-4o"`
> string shorthand. You must construct a `Model` from a `ModelClientConfig`
> (provider/key/base) + `ModelRequestConfig(model=...)`, then feed it into
> `ReActAgentConfig` or `create_deep_agent`. This is the single biggest source
> of boilerplate in every example below, and the SDK's most visible win.

---

## Example 1 — Single-agent Q&A

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent

async def main():
    agent = await Agent.create(
        "policy-bot",
        model="openai/gpt-4o",
        system_prompt="You are a company policy assistant. Answer concisely.",
    )
    reply = await agent.run("What is our parental leave policy?")
    print(reply)

asyncio.run(main())
```

```python
# ── openjiuwen (direct) ───────────────────────────────────────────────────────
import asyncio
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner import Runner
from openjiuwen.core.single_agent import ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.schema.agent_card import AgentCard

MODEL = Model(
    model_client_config=ModelClientConfig(
        client_provider="OpenAI",
        api_key="sk-...",
        api_base="https://api.openai.com/v1",
    ),
    model_config=ModelRequestConfig(model="gpt-4o"),
)

async def main():
    agent = ReActAgent(card=AgentCard(name="policy-bot", description="Policy assistant"))
    cfg = (
        ReActAgentConfig()
        .configure_model_client(
            provider="OpenAI",
            api_key="sk-...",
            api_base="https://api.openai.com/v1",
            model_name="gpt-4o",
        )
        .configure_prompt_template([
            {"role": "system",
             "content": "You are a company policy assistant. Answer concisely."},
        ])
    )
    agent.configure(cfg)

    res = await Runner.run_agent(
        agent=agent,
        inputs={"query": "What is our parental leave policy?", "conversation_id": "c1"},
    )
    print(res.get("output", res))

asyncio.run(main())
```

---

## Example 2 — Web search and summarise

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import web_search

async def main():
    agent = await Agent.create(
        "briefing-bot",
        model="openai/gpt-4o",
        tools=[web_search],
        system_prompt="Search the web and summarise in exactly 3 bullet points.",
    )
    summary = await agent.run("Latest news about enterprise AI adoption in 2025")
    print(summary)

asyncio.run(main())
```

```python
# ── openjiuwen (direct) ───────────────────────────────────────────────────────
import asyncio
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner import Runner
from openjiuwen.core.single_agent import ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.schema.agent_card import AgentCard
from openjiuwen.harness.tools.web import create_web_tools

MODEL = Model(
    model_client_config=ModelClientConfig(client_provider="OpenAI", api_key="sk-..."),
    model_config=ModelRequestConfig(model="gpt-4o"),
)

async def main():
    agent = ReActAgent(card=AgentCard(name="briefing-bot", description="Briefing bot"))
    cfg = (
        ReActAgentConfig()
        .configure_model_client(provider="OpenAI", api_key="sk-...", model_name="gpt-4o")
        .configure_prompt_template([
            {"role": "system",
             "content": "Search the web and summarise in exactly 3 bullet points."},
        ])
    )
    agent.configure(cfg)

    # Mount web-search tool instances manually (free search enabled by env).
    for tool in create_web_tools(language="en", agent_id="briefing-bot"):
        agent.ability_manager.add(tool.card)

    res = await Runner.run_agent(
        agent=agent,
        inputs={"query": "Latest news about enterprise AI adoption in 2025"},
    )
    print(res.get("output", res))

asyncio.run(main())
```

---

## Example 3 — Automated code review

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent

CODE = '''
def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
'''

async def main():
    reviewer = await Agent.create(
        "code-reviewer",
        model="openai/gpt-4o",
        system_prompt=(
            "You are a senior Python engineer. Review code and list issues as:\n"
            "[CRITICAL] / [WARNING] / [SUGGESTION] — one per line with explanation."
        ),
    )
    review = await reviewer.run(f"Review this code:\n```python{CODE}```")
    print(review)

asyncio.run(main())
```

```python
# ── openjiuwen (direct) ───────────────────────────────────────────────────────
import asyncio
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner import Runner
from openjiuwen.core.single_agent import ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.schema.agent_card import AgentCard

CODE = '''
def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
'''

MODEL = Model(
    model_client_config=ModelClientConfig(client_provider="OpenAI", api_key="sk-..."),
    model_config=ModelRequestConfig(model="gpt-4o"),
)

async def main():
    reviewer = ReActAgent(card=AgentCard(name="code-reviewer", description="Code reviewer"))
    cfg = (
        ReActAgentConfig()
        .configure_model_client(provider="OpenAI", api_key="sk-...", model_name="gpt-4o")
        .configure_prompt_template([
            {"role": "system",
             "content": (
                 "You are a senior Python engineer. Review code and list issues as:\n"
                 "[CRITICAL] / [WARNING] / [SUGGESTION] — one per line with explanation."
             )},
        ])
    )
    reviewer.configure(cfg)

    res = await Runner.run_agent(
        agent=reviewer,
        inputs={"query": f"Review this code:\n```python{CODE}```"},
    )
    print(res.get("output", res))

asyncio.run(main())
```

---

## Example 4 — Research + write pipeline (two agents)

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent, Team

async def main():
    researcher = await Agent.create(
        "researcher", model="openai/gpt-4o",
        system_prompt="Research topics thoroughly and return structured bullet-point findings.")
    writer = await Agent.create(
        "writer", model="openai/gpt-4o",
        system_prompt="Write engaging 500-word articles from research notes. Use subheadings.")
    team = await Team.create([researcher, writer], model="openai/gpt-4o")
    article = await team.spawn(
        "Research the business impact of AI agents in customer service, then write an article.")
    print(article)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — swarmflow workflow) ─────────────────────────────────
# research_write.py — a plain Python module the engine loads.
META = {
    "name": "research_write",
    "description": "Research a topic, then write an article from the findings.",
}

from swarmflow import agent  # noqa: E402


async def run(args):
    findings = await agent(
        "Research the business impact of AI agents in customer service.",
        label="researcher",
    )
    article = await agent(
        f"Write a 500-word article from these findings:\n{findings}",
        label="writer",
    )
    return article
```

```python
# driver.py — run the workflow against the real worker backend.
import asyncio
from openjiuwen.agent_teams.workflow.runner import run_swarmflow

async def main():
    result = await run_swarmflow(script_path="research_write.py", args={})
    print(result)

asyncio.run(main())
```

---

## Example 5 — Parallel competitive analysis

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import web_search
from openjiuwen.sdk.flows import parallel, pipeline, agent as flow_agent

COMPETITORS = ["Salesforce Einstein", "HubSpot AI", "Zendesk AI"]

async def main():
    await Agent.create("analyst", model="openai/gpt-4o", tools=[web_search],
        system_prompt="Research AI products. Return: pricing, key features, target market.")
    await Agent.create("synthesiser", model="openai/gpt-4o",
        system_prompt="Produce a markdown comparison table from multiple research summaries.")

    async with synthesiser.flow() as flow:
        profiles = await parallel(*[
            flow_agent("analyst", f"Research {c} — pricing, features, target market")
            for c in COMPETITORS
        ])
        table = await pipeline(
            flow_agent("synthesiser", f"Create comparison table from:\n{profiles}")
        )
    print(table)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — swarmflow workflow) ─────────────────────────────────
# competitive_analysis.py
META = {
    "name": "competitive_analysis",
    "description": "Research three competitors in parallel, then synthesise a table.",
}

from swarmflow import agent, parallel, pipeline  # noqa: E402

COMPETITORS = ["Salesforce Einstein", "HubSpot AI", "Zendesk AI"]


async def run(args):
    profiles = await parallel(*[
        agent(f"Research {c} — pricing, features, target market", label="analyst")
        for c in COMPETITORS
    ])
    table = await pipeline(
        agent(f"Create a markdown comparison table from:\n{profiles}", label="synthesiser"),
    )
    return table
```

```python
# driver.py
import asyncio
from openjiuwen.agent_teams.workflow.runner import run_swarmflow

asyncio.run(run_swarmflow(script_path="competitive_analysis.py", args={}))
```

---

## Example 6 — Customer support bot with persistent memory

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.memory import Memory, MemoryScope

async def support_session(user_id: str, message: str) -> str:
    memory = await Memory.create(scope=MemoryScope.USER, key=user_id)
    agent = await Agent.create(
        "support-bot", model="openai/gpt-4o", memory=memory,
        system_prompt="You are a friendly e-commerce support agent that remembers past issues.")
    return await agent.run(message)

async def main():
    r1 = await support_session("user-42", "My order #8821 hasn't arrived yet.")
    r2 = await support_session("user-42", "Any update on that?")
    print("Turn 1:", r1)
    print("Turn 2:", r2)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — LongTermMemory) ──────────────────────────────────────
import asyncio
from openjiuwen.core.memory.long_term_memory import LongTermMemory
from openjiuwen.core.memory.config.config import MemoryEngineConfig

async def main():
    # Configure and start a long-term memory engine (KV + vector + SQL backends).
    memory = LongTermMemory()
    memory.configure(MemoryEngineConfig(...))  # scopes: USER / SESSION / GLOBAL
    await memory.start()

    user_id = "user-42"
    # … agent runs write through the memory rails (add_message / recall).
    # The SDK hides: engine start/stop, scope config, and rail wiring onto the
    # ReActAgent. Direct usage requires mounting a memory rail (e.g.
    # ContextEvolutionRail / a MemoryRail) onto the agent and managing the
    # engine lifecycle yourself.

asyncio.run(main())
```

> The memory example is where the SDK's win is largest: `Memory.create(...)` hides
> engine construction, scope mapping, and rail mounting. A faithful direct
> reproduction is dozens of lines of setup (engine + store configs + rail) and is
> intentionally abbreviated here.

---

## Example 7 — Natural language to SQL with self-validation

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio, sqlite3
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import Tool

def run_sql(query: str) -> str:
    conn = sqlite3.connect("sales.db")
    try:
        return str(conn.execute(query).fetchall()[:20])
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

sql_tool = Tool(name="run_sql", fn=run_sql, description="Execute a SQL query against sales.db")

SCHEMA = "Tables: orders(id, customer_id, amount, created_at), customers(id, name, region)"

async def main():
    agent = await Agent.create(
        "sql-agent", model="openai/gpt-4o", tools=[sql_tool],
        system_prompt=f"You translate questions to SQL and interpret results.\nSchema:{SCHEMA}\n"
                      "Steps: 1) write SQL, 2) run it, 3) explain the result in plain English.",
    )
    answer = await agent.run("Which region generated the most revenue last quarter?")
    print(answer)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — custom Tool) ─────────────────────────────────────────
import asyncio, sqlite3
from openjiuwen.core.foundation.tool import Tool, ToolCard
from openjiuwen.core.runner import Runner
from openjiuwen.core.single_agent import ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.schema.agent_card import AgentCard

SCHEMA = "Tables: orders(id, customer_id, amount, created_at), customers(id, name, region)"

class RunSqlTool(Tool):
    def __init__(self, card: ToolCard):
        super().__init__(card)

    async def invoke(self, inputs, **kwargs):
        query = inputs.get("query") if isinstance(inputs, dict) else str(inputs)
        conn = sqlite3.connect("sales.db")
        try:
            return {"result": str(conn.execute(query).fetchall()[:20])}
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

async def main():
    agent = ReActAgent(card=AgentCard(name="sql-agent", description="SQL agent"))
    cfg = (
        ReActAgentConfig()
        .configure_model_client(provider="OpenAI", api_key="sk-...", model_name="gpt-4o")
        .configure_prompt_template([
            {"role": "system",
             "content": (
                 f"You translate questions to SQL and interpret results.\nSchema:{SCHEMA}\n"
                 "Steps: 1) write SQL, 2) run it, 3) explain the result in plain English."
             )},
        ])
    )
    agent.configure(cfg)

    sql_tool = RunSqlTool(ToolCard(
        name="run_sql", description="Execute a SQL query against sales.db",
        input_params={"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]},
    ))
    agent.ability_manager.add(sql_tool)

    res = await Runner.run_agent(
        agent=agent,
        inputs={"query": "Which region generated the most revenue last quarter?"},
    )
    print(res.get("output", res))

asyncio.run(main())
```

---

## Example 8 — Automatic bug fixer

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import code_interpreter

BUGGY_CODE = '''
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total =+ n
    return total / len(numbers)
'''

async def main():
    fixer = await Agent.create(
        "bug-fixer", model="openai/gpt-4o", tools=[code_interpreter],
        system_prompt=(
            "You are an expert Python debugger. 1) List every bug. "
            "2) Return corrected code. 3) List what changed."),
    )
    result = await fixer.run(f"Fix all bugs in:\n```python\n{BUGGY_CODE}\n```")
    print(result)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — sys_operation code tool) ─────────────────────────────
import asyncio
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner import Runner
from openjiuwen.core.sys_operation import SysOperationCard, OperationMode, LocalWorkConfig
from openjiuwen.harness import create_deep_agent

BUGGY_CODE = '''
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total =+ n
    return total / len(numbers)
'''

MODEL = Model(
    model_client_config=ModelClientConfig(client_provider="OpenAI", api_key="sk-..."),
    model_config=ModelRequestConfig(model="gpt-4o"),
)

async def main():
    # A code tool requires a SysOperation resource (sandbox / local work config).
    sysop_card = SysOperationCard(mode=OperationMode.LOCAL, work_config=LocalWorkConfig(work_dir=None))
    Runner.resource_mgr.add_sys_operation(sysop_card)

    fixer = create_deep_agent(
        model=MODEL,
        system_prompt=(
            "You are an expert Python debugger. 1) List every bug. "
            "2) Return corrected code. 3) List what changed."),
        sys_operation=sysop_card,
        enable_task_loop=True,
    )

    res = await Runner.run_agent(
        agent=fixer,
        inputs={"query": f"Fix all bugs in:\n```python\n{BUGGY_CODE}\n```"},
    )
    print(res.get("output", res))

asyncio.run(main())
```

---

## Example 9 — Content pipeline: topic → blog → SEO → social posts

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.flows import pipeline, agent as flow_agent

async def main():
    await Agent.create("blogger", model="openai/gpt-4o",
        system_prompt="Write engaging 600-word blog posts with a clear structure.")
    await Agent.create("seo-expert", model="openai/gpt-4o",
        system_prompt="Generate SEO title (≤60 chars), meta description (≤155 chars), and 5 keywords.")
    await Agent.create("social-writer", model="openai/gpt-4o",
        system_prompt="Write 5 platform-specific snippets.")

    topic = "Why small businesses should adopt AI automation in 2025"
    blog, seo, social = await pipeline(
        flow_agent("blogger",       f"Write a blog post about: {topic}"),
        flow_agent("seo-expert",    "Generate SEO metadata for the blog post above."),
        flow_agent("social-writer", "Create 5 social media snippets for the blog post above."),
    )
    print(blog, seo, social)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — swarmflow workflow) ─────────────────────────────────
# content_pipeline.py
META = {
    "name": "content_pipeline",
    "description": "topic → blog → SEO → social snippets.",
}

from swarmflow import agent, pipeline  # noqa: E402


async def run(args):
    topic = args["topic"]
    blog, seo, social = await pipeline(
        agent(f"Write a blog post about: {topic}", label="blogger"),
        agent("Generate SEO metadata for the blog post above.", label="seo-expert"),
        agent("Create 5 social media snippets for the blog post above.", label="social-writer"),
    )
    return {"blog": blog, "seo": seo, "social": social}
```

```python
# driver.py
import asyncio
from openjiuwen.agent_teams.workflow.runner import run_swarmflow

asyncio.run(run_swarmflow(
    script_path="content_pipeline.py",
    args={"topic": "Why small businesses should adopt AI automation in 2025"},
))
```

---

## Example 10 — Document Q&A with vector store (RAG)

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.knowledge import KnowledgeBase

async def main():
    kb = await KnowledgeBase.create("legal-kb", vector_store="chroma")
    await kb.add_directory("./legal-docs", glob="**/*.pdf")

    agent = await Agent.create(
        "legal-assistant", model="openai/gpt-4o", knowledge=kb,
        system_prompt=(
            "You are a legal assistant. Answer using only the provided documents. "
            "Cite source document and page for every claim."),
    )
    answer = await agent.run("What are the termination clauses in the Master Services Agreement?")
    print(answer)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — retrieval + retriever) ───────────────────────────────
import asyncio
from openjiuwen.core.retrieval import (
    KnowledgeBase,
    EmbeddingConfig,
    KnowledgeBaseConfig,
    VectorStoreConfig,
)
from openjiuwen.core.retrieval.retriever.vector_retriever import VectorRetriever

async def main():
    # Build the knowledge base, index PDFs, then wire a retriever into the agent.
    kb = KnowledgeBase(KnowledgeBaseConfig(
        name="legal-kb",
        embedding=EmbeddingConfig(...),
        vector_store=VectorStoreConfig(store_type="chroma", persist_dir="./chroma-db"),
    ))
    await kb.add_documents("./legal-docs", glob="**/*.pdf")

    retriever = VectorRetriever(kb)
    # … the retrieved chunks must then be injected into the ReActAgent prompt /
    # context on each turn — the SDK's `knowledge=kb` does this automatically.
    # Direct usage: query the retriever, build the context block, and append it
    # to the agent prompt yourself (not shown).

asyncio.run(main())
```

> Like memory (Example 6), RAG is where the SDK abstracts the most: the direct
> path needs explicit KB config, indexing, a retriever, and per-turn context
> injection — no `knowledge=kb` shortcut.

---

## Example 11 — Sales data analysis with executive summary

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent, Team
from openjiuwen.sdk.tools import code_interpreter, Tool
import pandas as pd

def load_sales_stats() -> str:
    df = pd.read_csv("sales_q4.csv")
    return df.describe().to_string() + "\n\nSample:\n" + df.head(10).to_string()

stats_tool = Tool(name="load_sales_stats", fn=load_sales_stats,
                  description="Load and describe Q4 sales data.")

async def main():
    analyst = await Agent.create("data-analyst", model="openai/gpt-4o",
        tools=[stats_tool, code_interpreter],
        system_prompt="Analyse sales data. Identify top/bottom performers, anomalies, trends.")
    exec_writer = await Agent.create("exec-writer", model="openai/gpt-4o",
        system_prompt="Write concise executive summaries with numbered recommendations.")
    team = await Team.create([analyst, exec_writer], model="openai/gpt-4o")
    report = await team.spawn(
        "Analyse Q4 sales data and produce an executive summary with top 3 recommendations.")
    print(report)

asyncio.run(main())
```

```python
# ── openjiuwen (direct — swarmflow workflow) ─────────────────────────────────
# sales_analysis.py
META = {
    "name": "sales_analysis",
    "description": "Analyse Q4 sales data, then write an executive summary.",
}

from swarmflow import agent, pipeline  # noqa: E402


async def run(args):
    analysis = await agent(
        "Analyse Q4 sales data and produce an executive summary with top 3 recommendations.",
        label="data-analyst",
    )
    report = await pipeline(
        agent(f"Write an executive summary with 3 recommendations from:\n{analysis}",
              label="exec-writer"),
    )
    return report
```

```python
# driver.py
import asyncio
from openjiuwen.agent_teams.workflow.runner import run_swarmflow

asyncio.run(run_swarmflow(script_path="sales_analysis.py", args={}))
```

---

## Example 12 — Recruitment pipeline: screen → rank → write outreach

```python
# ── openjiuwen.sdk ────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.flows import parallel, pipeline, agent as flow_agent, phase

JD = "Senior Python Engineer — 5+ yrs, FastAPI, PostgreSQL, distributed systems, remote."
RESUMES = {f"candidate_{i}": f"Resume content for candidate {i}..." for i in range(1, 11)}

async def main():
    await Agent.create("screener", model="openai/gpt-4o",
        system_prompt="Screen resumes against a job description. Score 0-10 with reasoning.")
    await Agent.create("ranker", model="openai/gpt-4o",
        system_prompt="Rank candidates by score. Return top 3 with justification.")
    await Agent.create("recruiter", model="openai/gpt-4o",
        system_prompt="Write warm, personalised outreach emails.")

    scores = await parallel(*[
        flow_agent("screener", f"JD: {JD}\n\nResume ({name}):\n{cv}")
        for name, cv in RESUMES.items()
    ])
    top3_names, *emails = await pipeline(
        flow_agent("ranker", f"Scores:\n{scores}\n\nReturn top 3 candidate names."),
        *[flow_agent("recruiter", f"Write outreach email for top candidate {i+1}.")
          for i in range(3)],
    )
    for i, email in enumerate(emails, 1):
        print(f"=== Email to Top Candidate #{i} ===\n{email}\n")

asyncio.run(main())
```

```python
# ── openjiuwen (direct — swarmflow workflow) ─────────────────────────────────
# recruitment.py
META = {
    "name": "recruitment",
    "description": "Screen resumes in parallel, rank top 3, write outreach emails.",
}

from swarmflow import agent, parallel, pipeline  # noqa: E402

JD = "Senior Python Engineer — 5+ yrs, FastAPI, PostgreSQL, distributed systems, remote."
RESUMES = {f"candidate_{i}": f"Resume content for candidate {i}..." for i in range(1, 11)}


async def run(args):
    scores = await parallel(*[
        agent(f"JD: {JD}\n\nResume ({name}):\n{cv}", label="screener")
        for name, cv in RESUMES.items()
    ])
    top3_names, *emails = await pipeline(
        agent(f"Scores:\n{scores}\n\nReturn top 3 candidate names.", label="ranker"),
        *[agent(f"Write outreach email for top candidate {i+1}.", label="recruiter")
          for i in range(3)],
    )
    return emails
```

```python
# driver.py
import asyncio
from openjiuwen.agent_teams.workflow.runner import run_swarmflow

async def main():
    emails = await run_swarmflow(script_path="recruitment.py", args={})
    for i, email in enumerate(emails, 1):
        print(f"=== Email to Top Candidate #{i} ===\n{email}\n")

asyncio.run(main())
```

---

## Summary

| # | Task | SDK | Direct equivalent | Main SDK win |
|---|------|-----|-------------------|--------------|
| 1 | Single-agent Q&A | `Agent.create` + `run` | `ReActAgent` + `AgentCard` + `ReActAgentConfig` + `Runner.run_agent` | Model plumbing (no `model="..."` string) |
| 2 | Web search + summarise | `tools=[web_search]` | `create_web_tools` + `ability_manager.add` | Tool mounting |
| 3 | Code review | `Agent.create` + `run` | same as #1 | Model plumbing |
| 4 | Research → write | `Team.create` + `spawn` | swarmflow `agent()` x2 | Team abstraction |
| 5 | Parallel competitive analysis | `parallel()` / `pipeline()` | swarmflow `parallel()` / `pipeline()` | Inline vs script file |
| 6 | Support bot with memory | `Memory.create` | `LongTermMemory` + config + rails | Memory engine lifecycle |
| 7 | NL → SQL | `Tool(name=, fn=)` | subclass `Tool` + `ToolCard` | Custom-tool boilerplate |
| 8 | Auto bug fixer | `code_interpreter` | `SysOperationCard` + `create_deep_agent` | Sandbox/code tool setup |
| 9 | Content pipeline | `pipeline()` | swarmflow `pipeline()` | Inline vs script file |
| 10 | RAG | `KnowledgeBase.create` | `KnowledgeBase` + config + retriever | KB config + context injection |
| 11 | Sales analysis | `Team.create` + `spawn` | swarmflow `agent()` + `pipeline()` | Team abstraction |
| 12 | Recruitment pipeline | `parallel()` + `pipeline()` | swarmflow `parallel()` + `pipeline()` | Inline vs script file |

**Two recurring themes:**

1. **Model plumbing** — every direct example starts with the same ~10 lines of
   `Model` / `ModelClientConfig` / `ModelRequestConfig` boilerplate that the SDK
   hides behind `model="openai/gpt-4o"`.

2. **Orchestration is already close** — the direct `swarmflow` DSL
   (`agent` / `parallel` / `pipeline` / `phase`) is nearly identical to the
   SDK's `flows`. The SDK mainly adds the inline syntax and agent-name lookups;
   the direct path puts the same logic in a `META` + `async def run(args)` file.

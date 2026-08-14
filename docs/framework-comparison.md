# Framework Comparison: JiuwenSwarm vs LangChain vs AutoGen vs CrewAI

12 real-world examples, from trivial to genuinely complex.
Every example solves the same task across all four frameworks.
JiuwenSwarm code is shown first since this is its documentation.

**Models used throughout:** `gpt-4o` (OpenAI) unless the example is provider-agnostic.

---

## Example 1 — Single-agent Q&A

The simplest possible case: ask one question, get one structured answer.
Use case: internal FAQ bot that answers questions about company policy.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent

MODEL = "openai/gpt-4o"

async def main():
    agent = await Agent.create(
        "policy-bot",
        model=MODEL,
        system_prompt="You are a company policy assistant. Answer concisely.",
    )
    reply = await agent.run("What is our parental leave policy?")
    print(reply)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4o")
messages = [
    SystemMessage(content="You are a company policy assistant. Answer concisely."),
    HumanMessage(content="What is our parental leave policy?"),
]
reply = llm.invoke(messages)
print(reply.content)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

bot = AssistantAgent("policy-bot", llm_config=llm_config,
                     system_message="You are a company policy assistant. Answer concisely.")
user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)
user.initiate_chat(bot, message="What is our parental leave policy?")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew

bot = Agent(
    role="Policy Assistant",
    goal="Answer company policy questions concisely",
    backstory="You know all company policies by heart.",
    verbose=False,
)
task = Task(
    description="What is our parental leave policy?",
    agent=bot,
    expected_output="A concise answer about parental leave.",
)
Crew(agents=[bot], tasks=[task]).kickoff()
```

---

## Example 2 — Web search and summarise

Task: given a topic, search the web and produce a 3-bullet executive summary.
Use case: morning briefing bot for a sales team.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import web_search

MODEL = "openai/gpt-4o"

async def main():
    agent = await Agent.create(
        "briefing-bot",
        model=MODEL,
        tools=[web_search],
        system_prompt="Search the web and summarise in exactly 3 bullet points.",
    )
    summary = await agent.run("Latest news about enterprise AI adoption in 2025")
    print(summary)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

llm = ChatOpenAI(model="gpt-4o")
tools = [DuckDuckGoSearchRun()]
prompt = PromptTemplate.from_template(
    "Search the web and summarise in exactly 3 bullet points.\n\n"
    "Tools: {tools}\nTool names: {tool_names}\n"
    "Question: {input}\nScratchpad: {agent_scratchpad}"
)
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
result = executor.invoke({"input": "Latest news about enterprise AI adoption in 2025"})
print(result["output"])
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent
from duckduckgo_search import DDGS

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

def search_web(query: str) -> str:
    with DDGS() as ddgs:
        return "\n".join(r["body"] for r in ddgs.text(query, max_results=5))

assistant = AssistantAgent(
    "briefing-bot", llm_config=llm_config,
    system_message="Summarise search results in exactly 3 bullet points.",
)
user = UserProxyAgent(
    "user", human_input_mode="NEVER", max_consecutive_auto_reply=1,
    function_map={"search_web": search_web},
)
user.initiate_chat(assistant, message="Latest news about enterprise AI adoption in 2025")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool

researcher = Agent(
    role="News Researcher",
    goal="Find recent news on a given topic",
    backstory="Expert at finding and summarising news.",
    tools=[SerperDevTool()],
    verbose=False,
)
task = Task(
    description="Find and summarise in 3 bullets: latest enterprise AI adoption news 2025",
    agent=researcher,
    expected_output="3 concise bullet points with sources.",
)
Crew(agents=[researcher], tasks=[task]).kickoff()
```

---

## Example 3 — Automated code review

Task: accept a Python function, return a review with severity-tagged issues.
Use case: CI pipeline hook that comments on pull requests.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent

MODEL = "openai/gpt-4o"
CODE = """
def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
"""

async def main():
    reviewer = await Agent.create(
        "code-reviewer",
        model=MODEL,
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
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

CODE = """
def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
"""

llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a senior Python engineer. Review code and list issues as:\n"
     "[CRITICAL] / [WARNING] / [SUGGESTION] — one per line with explanation."),
    ("human", "Review this code:\n```python\n{code}\n```"),
])
chain = prompt | llm
result = chain.invoke({"code": CODE})
print(result.content)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent

CODE = """
def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
"""

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

reviewer = AssistantAgent(
    "code-reviewer", llm_config=llm_config,
    system_message=(
        "You are a senior Python engineer. Review code and list issues as:\n"
        "[CRITICAL] / [WARNING] / [SUGGESTION] — one per line with explanation."
    ),
)
user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)
user.initiate_chat(reviewer, message=f"Review this code:\n```python\n{CODE}\n```")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew

CODE = """
def get_user(db, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query).fetchone()
"""

reviewer = Agent(
    role="Senior Python Engineer",
    goal="Identify all bugs, security issues, and improvements in code",
    backstory="15 years of Python and security experience.",
    verbose=False,
)
task = Task(
    description=(
        f"Review this code and list issues tagged [CRITICAL]/[WARNING]/[SUGGESTION]:\n"
        f"```python\n{CODE}\n```"
    ),
    agent=reviewer,
    expected_output="A tagged list of issues with explanations.",
)
Crew(agents=[reviewer], tasks=[task]).kickoff()
```

---

## Example 4 — Research + write pipeline (two agents)

Task: one agent researches a topic, a second agent writes a 500-word article from those findings.
Use case: content marketing automation.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent, Team

MODEL = "openai/gpt-4o"

async def main():
    researcher = await Agent.create(
        "researcher",
        model=MODEL,
        system_prompt="Research topics thoroughly and return structured bullet-point findings.",
    )
    writer = await Agent.create(
        "writer",
        model=MODEL,
        system_prompt="Write engaging 500-word articles from research notes. Use subheadings.",
    )
    team = await Team.create([researcher, writer], model=MODEL)
    article = await team.spawn(
        "Research the business impact of AI agents in customer service, then write an article."
    )
    print(article)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o")
parser = StrOutputParser()

research_prompt = ChatPromptTemplate.from_messages([
    ("system", "Research topics thoroughly and return structured bullet-point findings."),
    ("human", "{topic}"),
])
write_prompt = ChatPromptTemplate.from_messages([
    ("system", "Write engaging 500-word articles from research notes. Use subheadings."),
    ("human", "Research notes:\n{research}"),
])

chain = (
    research_prompt | llm | parser
    | (lambda research: {"research": research})
    | write_prompt | llm | parser
)
article = chain.invoke({"topic": "Business impact of AI agents in customer service"})
print(article)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

researcher = AssistantAgent(
    "researcher", llm_config=llm_config,
    system_message="Research topics and return structured bullet-point findings. Say DONE when finished.",
)
writer = AssistantAgent(
    "writer", llm_config=llm_config,
    system_message="Write a 500-word article from the researcher's notes. Use subheadings. Say DONE when finished.",
)
user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)

gc = GroupChat(agents=[user, researcher, writer], messages=[], max_round=4)
manager = GroupChatManager(groupchat=gc, llm_config=llm_config)
user.initiate_chat(
    manager,
    message="Research the business impact of AI agents in customer service, then write an article.",
)
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="Research Analyst",
    goal="Find detailed information on a given topic",
    backstory="Expert researcher with strong analytical skills.",
    verbose=False,
)
writer = Agent(
    role="Content Writer",
    goal="Write compelling 500-word articles from research",
    backstory="Experienced writer specialising in technology content.",
    verbose=False,
)
research_task = Task(
    description="Research the business impact of AI agents in customer service.",
    agent=researcher,
    expected_output="Structured bullet-point research findings.",
)
write_task = Task(
    description="Write a 500-word article using the research findings. Use subheadings.",
    agent=writer,
    context=[research_task],
    expected_output="A complete 500-word article with subheadings.",
)
Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
).kickoff()
```

---

## Example 5 — Parallel competitive analysis

Task: simultaneously research three competitors, then produce a comparison table.
Use case: product team preparing a competitive positioning deck.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import web_search
from openjiuwen.sdk.flows import parallel, pipeline, agent as flow_agent

MODEL = "openai/gpt-4o"
COMPETITORS = ["Salesforce Einstein", "HubSpot AI", "Zendesk AI"]

async def main():
    analyst = await Agent.create(
        "analyst", model=MODEL, tools=[web_search],
        system_prompt="Research AI products. Return: pricing, key features, target market.",
    )
    synthesiser = await Agent.create(
        "synthesiser", model=MODEL,
        system_prompt="Produce a markdown comparison table from multiple research summaries.",
    )

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
# ── LangChain ────────────────────────────────────────────────────────────────
import asyncio
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o")
search = DuckDuckGoSearchRun()
tools = [search]
prompt = PromptTemplate.from_template(
    "Research AI products. Return: pricing, key features, target market.\n"
    "Tools: {tools}\nTool names: {tool_names}\n"
    "Question: {input}\nScratchpad: {agent_scratchpad}"
)
analyst = AgentExecutor(agent=create_react_agent(llm, tools, prompt), tools=tools)

COMPETITORS = ["Salesforce Einstein", "HubSpot AI", "Zendesk AI"]

async def research_one(name: str) -> str:
    result = await analyst.ainvoke({"input": f"Research {name} — pricing, features, target market"})
    return result["output"]

async def main():
    profiles = await asyncio.gather(*[research_one(c) for c in COMPETITORS])
    combined = "\n\n".join(f"### {c}\n{p}" for c, p in zip(COMPETITORS, profiles))

    synth_prompt = (
        "Create a markdown comparison table from these competitor profiles:\n\n" + combined
    )
    table = llm.invoke(synth_prompt)
    print(table.content)

asyncio.run(main())
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os, asyncio
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}
COMPETITORS = ["Salesforce Einstein", "HubSpot AI", "Zendesk AI"]

# AutoGen runs agents sequentially inside GroupChat; true parallelism requires
# spawning separate chats and gathering with asyncio.
async def research_one(name: str) -> str:
    assistant = AssistantAgent(
        f"analyst-{name.split()[0].lower()}", llm_config=llm_config,
        system_message="Research AI products. Return: pricing, key features, target market.",
    )
    user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)
    result = await user.a_initiate_chat(
        assistant, message=f"Research {name} — pricing, features, target market"
    )
    return result.summary

async def main():
    profiles = await asyncio.gather(*[research_one(c) for c in COMPETITORS])
    combined = "\n\n".join(f"### {c}\n{p}" for c, p in zip(COMPETITORS, profiles))

    synth = AssistantAgent(
        "synthesiser", llm_config=llm_config,
        system_message="Produce a markdown comparison table from competitor profiles.",
    )
    user = UserProxyAgent("user2", human_input_mode="NEVER", max_consecutive_auto_reply=0)
    user.initiate_chat(synth, message=f"Create comparison table:\n{combined}")

asyncio.run(main())
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool

COMPETITORS = ["Salesforce Einstein", "HubSpot AI", "Zendesk AI"]

analyst = Agent(
    role="Competitive Analyst",
    goal="Research AI product competitors thoroughly",
    backstory="Expert in SaaS competitive intelligence.",
    tools=[SerperDevTool()],
    verbose=False,
)
synthesiser = Agent(
    role="Report Writer",
    goal="Synthesise research into comparison tables",
    backstory="Skilled at structured data presentation.",
    verbose=False,
)

research_tasks = [
    Task(
        description=f"Research {c} — pricing, key features, target market.",
        agent=analyst,
        expected_output=f"Structured profile of {c}.",
    )
    for c in COMPETITORS
]
synthesis_task = Task(
    description="Create a markdown comparison table from all competitor profiles.",
    agent=synthesiser,
    context=research_tasks,
    expected_output="A complete markdown comparison table.",
)
Crew(
    agents=[analyst, synthesiser],
    tasks=research_tasks + [synthesis_task],
    process=Process.sequential,
).kickoff()
```

---

## Example 6 — Customer support bot with persistent memory

Task: a support bot that remembers previous interactions with the same user across sessions.
Use case: e-commerce helpdesk where customers often have recurring issues.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.memory import Memory, MemoryScope

MODEL = "openai/gpt-4o"

async def support_session(user_id: str, message: str) -> str:
    memory = await Memory.create(scope=MemoryScope.USER, key=user_id)
    agent = await Agent.create(
        "support-bot",
        model=MODEL,
        memory=memory,
        system_prompt=(
            "You are a friendly e-commerce support agent. "
            "You remember past issues and refer to them naturally."
        ),
    )
    return await agent.run(message)

async def main():
    # First session
    r1 = await support_session("user-42", "My order #8821 hasn't arrived yet.")
    print("Turn 1:", r1)
    # Second session — agent recalls order #8821
    r2 = await support_session("user-42", "Any update on that?")
    print("Turn 2:", r2)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a friendly e-commerce support agent. "
     "You remember past issues and refer to them naturally."),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])
chain = prompt | llm

with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: SQLChatMessageHistory(
        session_id=session_id, connection_string="sqlite:///chat_history.db"
    ),
    input_messages_key="question",
    history_messages_key="history",
)
cfg = {"configurable": {"session_id": "user-42"}}

r1 = with_history.invoke({"question": "My order #8821 hasn't arrived yet."}, config=cfg)
print("Turn 1:", r1.content)
r2 = with_history.invoke({"question": "Any update on that?"}, config=cfg)
print("Turn 2:", r2.content)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os, json
from pathlib import Path
from autogen import AssistantAgent, UserProxyAgent
from autogen.cache import Cache

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

HISTORY_FILE = Path("support_history_user42.json")

def load_history() -> list[dict]:
    return json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else []

def save_history(messages: list[dict]) -> None:
    HISTORY_FILE.write_text(json.dumps(messages))

def support_session(user_message: str) -> None:
    history = load_history()
    bot = AssistantAgent(
        "support-bot", llm_config=llm_config,
        system_message="You are a friendly e-commerce support agent.",
    )
    # Re-inject history into the agent
    bot.chat_messages = {"user": history}
    user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)
    user.initiate_chat(bot, message=user_message)
    save_history(bot.chat_messages.get("user", []))

support_session("My order #8821 hasn't arrived yet.")
support_session("Any update on that?")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
# CrewAI does not have built-in cross-session user memory; state must be managed externally.
import json
from pathlib import Path
from crewai import Agent, Task, Crew

HISTORY_FILE = Path("support_history_user42.json")

def load_history() -> str:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text()).get("summary", "No prior contact.")
    return "No prior contact."

def save_history(summary: str) -> None:
    HISTORY_FILE.write_text(json.dumps({"summary": summary}))

def support_session(user_message: str) -> None:
    prior = load_history()
    bot = Agent(
        role="E-commerce Support Agent",
        goal="Resolve customer issues efficiently",
        backstory=f"Prior interaction summary: {prior}",
        verbose=False,
    )
    task = Task(
        description=user_message,
        agent=bot,
        expected_output="A helpful support response.",
    )
    result = Crew(agents=[bot], tasks=[task]).kickoff()
    save_history(str(result))

support_session("My order #8821 hasn't arrived yet.")
support_session("Any update on that?")
```

---

## Example 7 — Natural language to SQL with self-validation

Task: convert a plain English question into SQL, run it against a SQLite database,
then explain the result in plain English.
Use case: business intelligence tool for non-technical stakeholders.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio, sqlite3
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import Tool

MODEL = "openai/gpt-4o"

def run_sql(query: str) -> str:
    conn = sqlite3.connect("sales.db")
    try:
        rows = conn.execute(query).fetchall()
        return str(rows[:20])
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

sql_tool = Tool(name="run_sql", fn=run_sql, description="Execute a SQL query against sales.db")

SCHEMA = """
Tables: orders(id, customer_id, amount, created_at), customers(id, name, region)
"""

async def main():
    agent = await Agent.create(
        "sql-agent",
        model=MODEL,
        tools=[sql_tool],
        system_prompt=(
            f"You translate questions to SQL and interpret results.\nSchema:{SCHEMA}\n"
            "Steps: 1) write SQL, 2) run it, 3) explain the result in plain English."
        ),
    )
    answer = await agent.run("Which region generated the most revenue last quarter?")
    print(answer)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

db = SQLDatabase.from_uri("sqlite:///sales.db")
llm = ChatOpenAI(model="gpt-4o")

agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=False,
)
result = agent_executor.invoke(
    {"input": "Which region generated the most revenue last quarter?"}
)
print(result["output"])
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os, sqlite3
from autogen import AssistantAgent, UserProxyAgent

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

SCHEMA = "Tables: orders(id, customer_id, amount, created_at), customers(id, name, region)"

def run_sql(query: str) -> str:
    conn = sqlite3.connect("sales.db")
    try:
        return str(conn.execute(query).fetchall()[:20])
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

analyst = AssistantAgent(
    "sql-analyst", llm_config=llm_config,
    system_message=(
        f"Translate questions to SQL and interpret results.\nSchema: {SCHEMA}\n"
        "Call run_sql() to execute queries."
    ),
)
user = UserProxyAgent(
    "user", human_input_mode="NEVER", max_consecutive_auto_reply=3,
    function_map={"run_sql": run_sql},
)
user.initiate_chat(analyst, message="Which region generated the most revenue last quarter?")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
import sqlite3
from crewai import Agent, Task, Crew
from crewai.tools import tool

SCHEMA = "Tables: orders(id, customer_id, amount, created_at), customers(id, name, region)"

@tool("run_sql")
def run_sql(query: str) -> str:
    """Execute a SQL query against sales.db"""
    conn = sqlite3.connect("sales.db")
    try:
        return str(conn.execute(query).fetchall()[:20])
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()

analyst = Agent(
    role="Data Analyst",
    goal="Answer business questions using SQL",
    backstory=f"Expert in data analysis. Database schema: {SCHEMA}",
    tools=[run_sql],
    verbose=False,
)
task = Task(
    description="Which region generated the most revenue last quarter? Write SQL, run it, explain the result.",
    agent=analyst,
    expected_output="The answer in plain English with the supporting SQL.",
)
Crew(agents=[analyst], tasks=[task]).kickoff()
```

---

## Example 8 — Automatic bug fixer

Task: receive buggy Python code, identify all bugs, produce a corrected version with a changelog.
Use case: automated code repair step in a developer workflow.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.tools import code_interpreter

MODEL = "openai/gpt-4o"

BUGGY_CODE = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total =+ n          # bug 1: should be +=
    return total / len(numbers)  # bug 2: ZeroDivisionError if empty

def find_user(users, name):
    for user in users:
        if user["name"] = name:   # bug 3: assignment instead of ==
            return user
"""

async def main():
    fixer = await Agent.create(
        "bug-fixer",
        model=MODEL,
        tools=[code_interpreter],
        system_prompt=(
            "You are an expert Python debugger. "
            "1) List every bug with its line and explanation. "
            "2) Return the fully corrected code. "
            "3) List what changed as a changelog."
        ),
    )
    result = await fixer.run(f"Fix all bugs in:\n```python\n{BUGGY_CODE}\n```")
    print(result)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

BUGGY_CODE = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total =+ n
    return total / len(numbers)

def find_user(users, name):
    for user in users:
        if user["name"] = name:
            return user
"""

llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert Python debugger. "
     "1) List every bug with its line and explanation. "
     "2) Return the fully corrected code. "
     "3) List what changed as a changelog."),
    ("human", "Fix all bugs in:\n```python\n{code}\n```"),
])
chain = prompt | llm
result = chain.invoke({"code": BUGGY_CODE})
print(result.content)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent

BUGGY_CODE = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total =+ n
    return total / len(numbers)

def find_user(users, name):
    for user in users:
        if user["name"] = name:
            return user
"""

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

fixer = AssistantAgent(
    "bug-fixer", llm_config=llm_config,
    system_message=(
        "You are an expert Python debugger. "
        "1) List every bug with its line and explanation. "
        "2) Return the fully corrected code. "
        "3) List what changed as a changelog."
    ),
)
user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)
user.initiate_chat(fixer, message=f"Fix all bugs in:\n```python\n{BUGGY_CODE}\n```")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew

BUGGY_CODE = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total =+ n
    return total / len(numbers)

def find_user(users, name):
    for user in users:
        if user["name"] = name:
            return user
"""

fixer = Agent(
    role="Python Debugger",
    goal="Find and fix all bugs in Python code",
    backstory="Expert Python developer with deep knowledge of common pitfalls.",
    verbose=False,
)
task = Task(
    description=(
        "Fix all bugs in the following code. "
        "List each bug, return corrected code, and provide a changelog.\n"
        f"```python\n{BUGGY_CODE}\n```"
    ),
    agent=fixer,
    expected_output="Bug list, corrected code, and changelog.",
)
Crew(agents=[fixer], tasks=[task]).kickoff()
```

---

## Example 9 — Content pipeline: topic → blog → SEO → social posts

Task: turn a raw topic into (1) a blog post, (2) SEO meta tags, (3) five social media snippets.
Each step feeds the next. Use case: fully automated content marketing pipeline.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.flows import pipeline, agent as flow_agent

MODEL = "openai/gpt-4o"

async def main():
    await Agent.create("blogger", model=MODEL,
        system_prompt="Write engaging 600-word blog posts with a clear structure.")
    await Agent.create("seo-expert", model=MODEL,
        system_prompt="Generate SEO title (≤60 chars), meta description (≤155 chars), and 5 keywords.")
    await Agent.create("social-writer", model=MODEL,
        system_prompt="Write 5 platform-specific snippets: Twitter, LinkedIn, Instagram, Facebook, TikTok.")

    topic = "Why small businesses should adopt AI automation in 2025"

    blog, seo, social = await pipeline(
        flow_agent("blogger",       f"Write a blog post about: {topic}"),
        flow_agent("seo-expert",    "Generate SEO metadata for the blog post above."),
        flow_agent("social-writer", "Create 5 social media snippets for the blog post above."),
    )
    print("=== BLOG ===\n", blog)
    print("=== SEO ===\n", seo)
    print("=== SOCIAL ===\n", social)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o")
p = StrOutputParser()

blog_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Write engaging 600-word blog posts with a clear structure."),
        ("human", "Write a blog post about: {topic}"),
    ]) | llm | p
)
seo_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Generate SEO title (≤60 chars), meta description (≤155 chars), and 5 keywords."),
        ("human", "Blog post:\n{blog}"),
    ]) | llm | p
)
social_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Write 5 platform-specific snippets: Twitter, LinkedIn, Instagram, Facebook, TikTok."),
        ("human", "Blog post:\n{blog}"),
    ]) | llm | p
)

topic = "Why small businesses should adopt AI automation in 2025"
blog   = blog_chain.invoke({"topic": topic})
seo    = seo_chain.invoke({"blog": blog})
social = social_chain.invoke({"blog": blog})

print("=== BLOG ===\n", blog)
print("=== SEO ===\n", seo)
print("=== SOCIAL ===\n", social)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

blogger = AssistantAgent("blogger", llm_config=llm_config,
    system_message="Write engaging 600-word blog posts. When done, say BLOG_DONE.")
seo = AssistantAgent("seo-expert", llm_config=llm_config,
    system_message="When you see a blog post, generate its SEO metadata. Say SEO_DONE when done.")
social = AssistantAgent("social-writer", llm_config=llm_config,
    system_message="When you see a blog post, write 5 social media snippets. Say SOCIAL_DONE when done.")
user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0,
    is_termination_msg=lambda m: "SOCIAL_DONE" in m.get("content", ""))

gc = GroupChat(agents=[user, blogger, seo, social], messages=[], max_round=6)
manager = GroupChatManager(groupchat=gc, llm_config=llm_config)
user.initiate_chat(manager,
    message="Write a blog post about: Why small businesses should adopt AI automation in 2025. "
            "Then generate SEO metadata. Then write 5 social media snippets.")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process

blogger = Agent(role="Blog Writer",
    goal="Write engaging 600-word blog posts",
    backstory="Professional content writer specialising in tech.", verbose=False)
seo_exp = Agent(role="SEO Expert",
    goal="Generate optimised SEO metadata",
    backstory="Expert in search engine optimisation.", verbose=False)
social_w = Agent(role="Social Media Manager",
    goal="Create platform-specific social media content",
    backstory="Expert at adapting content for different social platforms.", verbose=False)

topic = "Why small businesses should adopt AI automation in 2025"

t_blog = Task(description=f"Write a 600-word blog post about: {topic}",
    agent=blogger, expected_output="A complete 600-word blog post.")
t_seo  = Task(description="Generate SEO title (≤60 chars), meta description (≤155 chars), 5 keywords.",
    agent=seo_exp, context=[t_blog], expected_output="SEO metadata.")
t_soc  = Task(description="Write 5 social media snippets for Twitter, LinkedIn, Instagram, Facebook, TikTok.",
    agent=social_w, context=[t_blog], expected_output="5 platform-specific posts.")

Crew(agents=[blogger, seo_exp, social_w],
     tasks=[t_blog, t_seo, t_soc],
     process=Process.sequential).kickoff()
```

---

## Example 10 — Document Q&A with vector store (RAG)

Task: index a folder of PDFs, then answer questions from their content.
Use case: internal knowledge base for a legal or compliance team.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.knowledge import KnowledgeBase

MODEL = "openai/gpt-4o"

async def main():
    # Index documents once
    kb = await KnowledgeBase.create("legal-kb", vector_store="chroma")
    await kb.add_directory("./legal-docs", glob="**/*.pdf")

    agent = await Agent.create(
        "legal-assistant",
        model=MODEL,
        knowledge=kb,
        system_prompt=(
            "You are a legal assistant. Answer questions using only the provided documents. "
            "Cite the source document and page for every claim."
        ),
    )
    answer = await agent.run("What are the termination clauses in the Master Services Agreement?")
    print(answer)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

# Index documents
loader = DirectoryLoader("./legal-docs", glob="**/*.pdf", loader_cls=PyPDFLoader)
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = splitter.split_documents(docs)

vectorstore = Chroma.from_documents(chunks, OpenAIEmbeddings(), persist_directory="./chroma-db")

# Query
llm = ChatOpenAI(model="gpt-4o")
qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
    return_source_documents=True,
)
result = qa.invoke({"query": "What are the termination clauses in the Master Services Agreement?"})
print(result["result"])
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os
from autogen import AssistantAgent, UserProxyAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

assistant = AssistantAgent(
    "legal-assistant", llm_config=llm_config,
    system_message=(
        "Answer legal questions using only retrieved documents. "
        "Cite source and page for every claim."
    ),
)
retriever = RetrieveUserProxyAgent(
    "retriever",
    human_input_mode="NEVER",
    retrieve_config={
        "task": "qa",
        "docs_path": ["./legal-docs"],
        "chunk_token_size": 1000,
        "model": "gpt-4o",
        "vector_db": "chroma",
        "collection_name": "legal-kb",
        "get_or_create": True,
    },
    max_consecutive_auto_reply=3,
)
retriever.initiate_chat(
    assistant,
    message="What are the termination clauses in the Master Services Agreement?",
    problem="termination clauses in MSA",
)
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew
from crewai_tools import PDFSearchTool

pdf_tool = PDFSearchTool(
    config={"embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small"}}},
)

lawyer = Agent(
    role="Legal Research Assistant",
    goal="Answer legal questions using document content only",
    backstory="Expert at finding and citing legal clauses from contracts.",
    tools=[pdf_tool],
    verbose=False,
)
task = Task(
    description=(
        "Find and explain the termination clauses in the Master Services Agreement. "
        "Cite source document and page for every claim."
    ),
    agent=lawyer,
    expected_output="A detailed answer with citations.",
)
Crew(agents=[lawyer], tasks=[task]).kickoff()
```

---

## Example 11 — Sales data analysis with executive summary

Task: load sales data (CSV), identify top/bottom performers, anomalies, and trends,
then produce an executive summary with concrete recommendations.
Use case: weekly automated business review sent to leadership.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent, Team
from openjiuwen.sdk.tools import code_interpreter, Tool
import pandas as pd

MODEL = "openai/gpt-4o"

def load_sales_stats() -> str:
    df = pd.read_csv("sales_q4.csv")
    return df.describe().to_string() + "\n\nSample:\n" + df.head(10).to_string()

stats_tool = Tool(name="load_sales_stats", fn=load_sales_stats,
                  description="Load and describe Q4 sales data.")

async def main():
    analyst = await Agent.create("data-analyst", model=MODEL,
        tools=[stats_tool, code_interpreter],
        system_prompt="Analyse sales data. Identify top/bottom performers, anomalies, trends.")
    exec_writer = await Agent.create("exec-writer", model=MODEL,
        system_prompt="Write concise executive summaries with numbered recommendations.")

    team = await Team.create([analyst, exec_writer], model=MODEL)
    report = await team.spawn(
        "Analyse Q4 sales data and produce an executive summary with top 3 recommendations."
    )
    print(report)

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

df = pd.read_csv("sales_q4.csv")
llm = ChatOpenAI(model="gpt-4o")

# Step 1: analyse data
analyst = create_pandas_dataframe_agent(llm, df, verbose=False, allow_dangerous_code=True)
analysis = analyst.invoke({
    "input": "Identify top and bottom performing products, any anomalies, and monthly trends."
})["output"]

# Step 2: executive summary
summary_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Write concise executive summaries with numbered recommendations."),
        ("human", "Analysis:\n{analysis}\n\nWrite an executive summary with top 3 recommendations."),
    ]) | llm | StrOutputParser()
)
report = summary_chain.invoke({"analysis": analysis})
print(report)
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os, pandas as pd
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from autogen.coding import LocalCommandLineCodeExecutor

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

analyst = AssistantAgent("data-analyst", llm_config=llm_config,
    system_message="Analyse sales_q4.csv. Write Python code to find top/bottom performers, anomalies, trends.")
writer = AssistantAgent("exec-writer", llm_config=llm_config,
    system_message="Write an executive summary with 3 concrete recommendations from the analysis. Say DONE.")

executor = UserProxyAgent("executor", human_input_mode="NEVER", max_consecutive_auto_reply=5,
    code_execution_config={"executor": LocalCommandLineCodeExecutor(work_dir=".")},
    is_termination_msg=lambda m: "DONE" in m.get("content", ""))

gc = GroupChat(agents=[executor, analyst, writer], messages=[], max_round=8)
manager = GroupChatManager(groupchat=gc, llm_config=llm_config)
executor.initiate_chat(manager,
    message="Analyse Q4 sales data and write an executive summary with top 3 recommendations.")
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process
from crewai_tools import CodeInterpreterTool, FileReadTool

analyst = Agent(role="Data Analyst",
    goal="Analyse sales data and extract insights",
    backstory="Expert data analyst specialising in sales metrics.",
    tools=[CodeInterpreterTool(), FileReadTool()], verbose=False)
writer = Agent(role="Executive Report Writer",
    goal="Write concise executive summaries with actionable recommendations",
    backstory="MBA with 10 years of business reporting experience.", verbose=False)

t_analyse = Task(
    description="Load sales_q4.csv. Identify top/bottom performers, anomalies, and monthly trends.",
    agent=analyst, expected_output="Detailed analysis with key metrics.")
t_report = Task(
    description="Write an executive summary with exactly 3 numbered recommendations.",
    agent=writer, context=[t_analyse], expected_output="Executive summary with 3 recommendations.")

Crew(agents=[analyst, writer], tasks=[t_analyse, t_report], process=Process.sequential).kickoff()
```

---

## Example 12 — Recruitment pipeline: screen → rank → write outreach

Task: given 10 resumes and a job description, screen candidates, rank the top 3,
and write personalised outreach emails for each.
Use case: HR automation for high-volume hiring.

```python
# ── JiuwenSwarm ──────────────────────────────────────────────────────────────
import asyncio
from openjiuwen.sdk import Agent
from openjiuwen.sdk.flows import parallel, pipeline, agent as flow_agent, phase

MODEL = "openai/gpt-4o"

JD = "Senior Python Engineer — 5+ yrs, FastAPI, PostgreSQL, distributed systems, remote."
RESUMES = {f"candidate_{i}": f"Resume content for candidate {i}..." for i in range(1, 11)}

async def main():
    await Agent.create("screener", model=MODEL,
        system_prompt="Screen resumes against a job description. Score 0-10 with reasoning.")
    await Agent.create("ranker", model=MODEL,
        system_prompt="Rank candidates by score. Return top 3 with justification.")
    await Agent.create("recruiter", model=MODEL,
        system_prompt="Write warm, personalised outreach emails. Reference specific resume details.")

    # Screen all candidates in parallel
    scores = await parallel(*[
        flow_agent("screener", f"JD: {JD}\n\nResume ({name}):\n{cv}")
        for name, cv in RESUMES.items()
    ])

    # Rank, then write emails for top 3 in parallel
    top3_names, *emails = await pipeline(
        flow_agent("ranker", f"Scores:\n{scores}\n\nReturn top 3 candidate names."),
        *[
            flow_agent("recruiter", f"Write outreach email for top candidate {i+1}.")
            for i in range(3)
        ],
    )
    for i, email in enumerate(emails, 1):
        print(f"=== Email to Top Candidate #{i} ===\n{email}\n")

asyncio.run(main())
```

```python
# ── LangChain ────────────────────────────────────────────────────────────────
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o")
p = StrOutputParser()

JD = "Senior Python Engineer — 5+ yrs, FastAPI, PostgreSQL, distributed systems, remote."
RESUMES = {f"candidate_{i}": f"Resume content for candidate {i}..." for i in range(1, 11)}

screen_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Screen resumes. Score 0-10 with reasoning."),
        ("human", "JD: {jd}\n\nResume ({name}):\n{resume}"),
    ]) | llm | p
)
rank_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Rank candidates. Return top 3 names with justification."),
        ("human", "All scores:\n{scores}"),
    ]) | llm | p
)
email_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Write a warm personalised outreach email."),
        ("human", "Write outreach for:\n{candidate_info}"),
    ]) | llm | p
)

async def screen_one(name: str, cv: str) -> str:
    return await screen_chain.ainvoke({"jd": JD, "name": name, "resume": cv})

async def main():
    scores = await asyncio.gather(*[screen_one(n, cv) for n, cv in RESUMES.items()])
    combined_scores = "\n".join(f"{n}: {s}" for n, s in zip(RESUMES.keys(), scores))
    top3 = rank_chain.invoke({"scores": combined_scores})

    # Write emails for top 3 in parallel
    emails = await asyncio.gather(*[
        email_chain.ainvoke({"candidate_info": f"Top candidate #{i+1}\n{top3}"})
        for i in range(3)
    ])
    for i, email in enumerate(emails, 1):
        print(f"=== Email #{i} ===\n{email}\n")

asyncio.run(main())
```

```python
# ── AutoGen ──────────────────────────────────────────────────────────────────
import os, asyncio
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

llm_config = {"config_list": [{"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}]}

JD = "Senior Python Engineer — 5+ yrs, FastAPI, PostgreSQL, distributed systems, remote."
RESUMES = {f"candidate_{i}": f"Resume content for candidate {i}..." for i in range(1, 11)}

async def screen_one(name: str, cv: str) -> str:
    screener = AssistantAgent("screener", llm_config=llm_config,
        system_message="Screen resumes. Score 0-10 with reasoning.")
    user = UserProxyAgent("user", human_input_mode="NEVER", max_consecutive_auto_reply=0)
    result = await user.a_initiate_chat(screener,
        message=f"JD: {JD}\n\nResume ({name}):\n{cv}")
    return result.summary

async def main():
    scores = await asyncio.gather(*[screen_one(n, cv) for n, cv in RESUMES.items()])
    combined = "\n".join(f"{n}: {s}" for n, s in zip(RESUMES.keys(), scores))

    ranker = AssistantAgent("ranker", llm_config=llm_config,
        system_message="Rank candidates, return top 3 with justification.")
    writer = AssistantAgent("recruiter", llm_config=llm_config,
        system_message="Write warm personalised outreach emails.")
    user = UserProxyAgent("user2", human_input_mode="NEVER", max_consecutive_auto_reply=0)

    gc = GroupChat(agents=[user, ranker, writer], messages=[], max_round=5)
    manager = GroupChatManager(groupchat=gc, llm_config=llm_config)
    user.initiate_chat(manager,
        message=f"Rank these candidates:\n{combined}\nThen write outreach emails for top 3.")

asyncio.run(main())
```

```python
# ── CrewAI ───────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process

JD = "Senior Python Engineer — 5+ yrs, FastAPI, PostgreSQL, distributed systems, remote."
RESUMES = {f"candidate_{i}": f"Resume content for candidate {i}..." for i in range(1, 11)}
resumes_text = "\n\n".join(f"[{n}]\n{cv}" for n, cv in RESUMES.items())

screener = Agent(role="HR Screener",
    goal="Evaluate resumes against the job description",
    backstory="Expert technical recruiter.", verbose=False)
ranker = Agent(role="Talent Strategist",
    goal="Identify top candidates from screening results",
    backstory="Hiring manager with strong pattern recognition.", verbose=False)
recruiter = Agent(role="Recruiter",
    goal="Write personalised outreach emails that convert",
    backstory="Experienced recruiter known for high response rates.", verbose=False)

t_screen = Task(
    description=f"Screen all resumes against this JD. Score 0-10.\nJD: {JD}\n\nResumes:\n{resumes_text}",
    agent=screener, expected_output="Scored list of all candidates.")
t_rank = Task(
    description="Rank candidates and return top 3 with justification.",
    agent=ranker, context=[t_screen], expected_output="Top 3 candidates with scores and reasons.")
t_email = Task(
    description="Write personalised outreach emails for the top 3 candidates.",
    agent=recruiter, context=[t_rank], expected_output="3 personalised outreach emails.")

Crew(agents=[screener, ranker, recruiter],
     tasks=[t_screen, t_rank, t_email],
     process=Process.sequential).kickoff()
```

---

## Summary

| # | Task | Parallel support | Persistent memory | Vector store | Built-in gateway |
|---|------|:---:|:---:|:---:|:---:|
| 1 | Single agent Q&A | — | — | — | — |
| 2 | Web search + summarise | — | — | — | — |
| 3 | Code review | — | — | — | — |
| 4 | Research → write pipeline | — | — | — | — |
| 5 | Parallel competitive analysis | ✓ | — | — | — |
| 6 | Support bot with memory | — | ✓ | — | — |
| 7 | Natural language to SQL | — | — | — | — |
| 8 | Auto bug fixer | — | — | — | — |
| 9 | Content pipeline (blog→SEO→social) | — | — | — | — |
| 10 | Document Q&A (RAG) | — | — | ✓ | — |
| 11 | Sales data analysis | — | — | — | — |
| 12 | Recruitment pipeline | ✓ | — | — | — |

**Framework characteristics across these examples:**

| Capability | JiuwenSwarm | LangChain | AutoGen | CrewAI |
|---|---|---|---|---|
| Agent creation verbosity | Low | Low–medium | Medium | High (role/goal/backstory) |
| Parallel execution | `parallel()` DSL | `asyncio.gather` | `a_initiate_chat` + gather | Context-passing only (sequential) |
| Pipelines | `pipeline()` DSL | LCEL (`\|` operator) | GroupChat ordering | Task `context=` chain |
| Persistent memory | `Memory.create()` built-in | `RunnableWithMessageHistory` | Manual file / cache | Manual file |
| Vector store | `KnowledgeBase.create()` | `Chroma` + `RetrievalQA` | `RetrieveUserProxyAgent` | `PDFSearchTool` |
| WebSocket / streaming gateway | Built-in | Not included | Not included | Not included |
| LLM providers | 2 (OpenAI, Anthropic) | 100+ | 10+ | 10+ |
| TypeScript client | Official SDK | Community only | Not available | Not available |

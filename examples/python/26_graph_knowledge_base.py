"""26_graph_knowledge_base.py — knowledge graph layer for relationship-aware retrieval.

Corresponds to §26 of the usage examples.

Shows:
  - GraphKnowledgeBase extending standard KB with an SPO triple layer
  - llm_client used for triple extraction during indexing
  - gkb.retrieve() with use_graph=True for vector + graph traversal
  - Agent.create(knowledge_bases=[gkb]) integration

Run:
    python examples/26_graph_knowledge_base.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.core.retrieval import (
    GraphKnowledgeBase,
    KnowledgeBaseConfig,
    Document,
)


async def main():
    model_cfg = ModelConfig.from_env()

    gkb = GraphKnowledgeBase(
        config=KnowledgeBaseConfig(
            name="tech-history",
            embedding_model="text-embedding-3-small",
            vector_store="chroma",
        ),
        # Graph-specific components (defaults to built-in if not specified)
        llm_client=model_cfg.build_llm_client(),  # used for triple extraction
    )

    await gkb.add_documents([
        Document(text="Alan Turing invented the Turing machine, which influenced the Church-Turing thesis."),
        Document(text="The Church-Turing thesis underpins the theory of computability."),
        Document(text="Von Neumann architecture was inspired by Turing's stored-program concept."),
        Document(text="Modern CPUs implement Von Neumann architecture."),
    ])

    # Graph retrieval follows relationship chains, not just embedding similarity
    results = await gkb.retrieve(
        query="How does Turing's work connect to modern CPUs?",
        top_k=5,
        use_graph=True,   # enable graph traversal in addition to vector search
    )
    for r in results:
        print(f"[score={r.score:.2f}] {r.text}")

    # Attach to an agent
    agent = await Agent.create(
        "historian",
        model=model_cfg,
        knowledge_bases=[gkb],
    )
    result = await agent.run(
        "Trace the intellectual lineage from Turing to modern computing hardware."
    )
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())

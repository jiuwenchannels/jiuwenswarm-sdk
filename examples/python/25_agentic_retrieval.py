"""25_agentic_retrieval.py — LLM-driven multi-round retrieval with query rewriting.

Corresponds to §25 of the usage examples.

Shows:
  - KnowledgeBase and KnowledgeBaseConfig setup
  - AgenticRetriever wrapping a base retriever with an LLM loop
  - max_rounds and top_k_per_round configuration
  - agentic.retrieve() with automatic query rewriting and iteration
  - Agent.create(retriever=agentic) to override the default single-shot retriever

Run:
    python examples/25_agentic_retrieval.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.core.retrieval import (
    AgenticRetriever,
    KnowledgeBase,
    KnowledgeBaseConfig,
    Document,
)


async def main():
    model_cfg = ModelConfig.from_env()

    # Build a standard knowledge base
    kb = KnowledgeBase(
        config=KnowledgeBaseConfig(
            name="research-papers",
            embedding_model="text-embedding-3-small",
            vector_store="chroma",
        )
    )
    await kb.add_documents([
        Document(text="Transformers were introduced in 'Attention Is All You Need' (2017)."),
        Document(text="RLHF was used to align GPT models to human preferences."),
        Document(text="Constitutional AI (CAI) is an Anthropic technique for self-critique."),
        Document(text="Sparse mixture-of-experts reduces FLOPs by activating only a few experts."),
    ])

    # Wrap the KB's built-in retriever with AgenticRetriever
    agentic = AgenticRetriever(
        retriever=kb.retriever,
        llm_client=model_cfg.build_llm_client(),   # used for query rewriting
        max_rounds=3,                               # up to 3 retrieval rounds
        top_k_per_round=5,
    )

    # The agentic retriever rewrites the query, retrieves, decides if it needs
    # more context, and iterates — all automatically.
    results = await agentic.retrieve(
        query="How do modern LLMs reduce inference costs while maintaining quality?"
    )
    for r in results:
        print(f"[score={r.score:.2f}] {r.text}")

    # Attach the agentic retriever directly to an agent
    agent = await Agent.create(
        "research-agent",
        model=model_cfg,
        knowledge_bases=[kb],
        retriever=agentic,          # overrides the default single-shot retriever
    )
    result = await agent.run("Explain the key techniques for efficient LLM inference.")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())

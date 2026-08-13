"""07_knowledge_base_rag.py — knowledge base creation and retrieval-augmented generation.

Corresponds to §7 of the usage examples.

Shows:
  - KnowledgeBase.create() with embedding model and vector store
  - kb.add_documents() for indexing
  - Retriever with hybrid strategy
  - Agent.create(knowledge_bases=[kb]) for automatic RAG

Run:
    python examples/07_knowledge_base_rag.py
"""

import asyncio
from openjiuwen.sdk.knowledge import KnowledgeBase, Retriever, Document


async def main():
    # Build a knowledge base from documents
    kb = await KnowledgeBase.create(
        name="company-docs",
        embedding_model="text-embedding-3-small",
        vector_store="chroma",          # or "milvus"
    )

    # Index documents
    await kb.add_documents([
        Document(text="Our refund policy allows returns within 30 days."),
        Document(text="Customer support is available Monday–Friday, 9–5 PST."),
        Document(
            text="Pro plan includes unlimited API calls and priority support.",
            metadata={"source": "pricing.md"},
        ),
    ])

    # Retrieve relevant chunks for a query
    retriever = Retriever(kb, strategy="hybrid", top_k=3)
    results = await retriever.retrieve("What are the support hours?")
    for r in results:
        print(f"[{r.score:.2f}] {r.text}")

    # Use the KB as context in an agent
    from openjiuwen.sdk import Agent, ModelConfig
    agent = await Agent.create(
        "support-bot",
        knowledge_bases=[kb],
        model=ModelConfig.from_env(),
    )
    result = await agent.run("Can I return a product I bought last week?")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())

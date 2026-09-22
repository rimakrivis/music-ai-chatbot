# backend/knowledge_search.py
#
# Single shared implementation of the marketing-knowledge Pinecone search,
# used by the agent's search_marketing_knowledge tool. Takes an optional
# source_key so a query can be scoped to one project type's knowledge file
# (see seed_knowledge.py's SOURCES — each chunk is tagged with its source
# key in Pinecone metadata) instead of searching every project type's
# content at once.

import os
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from config import OPENAI_API_KEY

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

_vector_store = None


def _get_vector_store() -> PineconeVectorStore:
    global _vector_store
    if _vector_store is None:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY,
        )
        _vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings,
            namespace="marketing_knowledge",
        )
    return _vector_store


def search_knowledge(query: str, source_key: str | None = None, k: int = 3) -> str:
    """Search the marketing knowledge base, optionally scoped to one source_key
    (e.g. "concert"). Returns "" on no results or error — callers decide their
    own empty-state message."""
    try:
        vector_store = _get_vector_store()
        kwargs = {"k": k}
        if source_key:
            kwargs["filter"] = {"source": source_key}
        results = vector_store.similarity_search(query, **kwargs)
        if not results:
            return ""
        chunks = []
        for doc in results:
            header = doc.metadata.get("section") or ""
            chunks.append(f"[{header}]\n{doc.page_content}")
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        print(f"[knowledge_search] error: {e}")
        return ""

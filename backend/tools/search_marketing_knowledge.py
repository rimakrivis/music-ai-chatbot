import os
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from config import OPENAI_API_KEY

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

@tool
def search_marketing_knowledge(query: str) -> str:
    """
    Searches the music marketing knowledge base for strategy,
    timelines, radio submission rules, social media plans,
    Spotify pitch guidelines, press release format, and
    distributor deadlines. Use this when the user asks HOW
    to do something marketing-related.
    """
    print(f"[search_marketing_knowledge] Query: '{query}'")
    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY
        )
        vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX_NAME,
            embedding=embeddings,
            namespace="marketing_knowledge",
        )
        results = vector_store.similarity_search(query, k=3)
        if not results:
            return "No relevant marketing knowledge found."
        output = []
        for doc in results:
            header = doc.metadata.get("Header 2") or doc.metadata.get("Header 1") or ""
            output.append(f"[{header}]\n{doc.page_content}")
        print(f"   📚 Retrieved {len(results)} marketing knowledge chunks")
        return "\n\n---\n\n".join(output)
    except Exception as e:
        return f"Knowledge search error: {str(e)}"

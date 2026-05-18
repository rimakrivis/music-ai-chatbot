import os
import chromadb
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from config import OPENAI_API_KEY, IS_PRODUCTION
from pipeline import get_chroma_client

CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

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
        if IS_PRODUCTION:
            chroma_client = get_chroma_client()
            vector_store = Chroma(
                collection_name="marketing_knowledge",
                embedding_function=embeddings,
                client=chroma_client,
            )
        else:
            vector_store = Chroma(
                collection_name="marketing_knowledge",
                embedding_function=embeddings,
                persist_directory=CHROMA_DB_PATH,
            )
        results = vector_store.similarity_search(query, k=3)
        if not results:
            return "No relevant marketing knowledge found."
        output = []
        for doc in results:
            header = doc.metadata.get("Header 2") or doc.metadata.get("Header 1") or ""
            output.append(f"[{header}]\n{doc.page_content}")
        return "\n\n---\n\n".join(output)
    except Exception as e:
        return f"Knowledge search error: {str(e)}"

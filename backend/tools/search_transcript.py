# backend/tools/search_transcript.py
# Tool 1: search_transcript
# Searches ChromaDB for transcript chunks relevant to the user's query.
# Uses cosine similarity via OpenAI embeddings (text-embedding-3-small).
# This is the core RAG tool — the agent calls this whenever the user
# asks anything about the song's content, lyrics, or meaning.

from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config import OPENAI_API_KEY, IS_PRODUCTION

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY
)

from pathlib import Path
CHROMA_PATH = str(Path(__file__).parent.parent / "chroma_db")


@tool
def search_transcript(query: str, video_id: str) -> str:
    """
    Search the transcript of a YouTube music video for content relevant to a query.
    Use this tool when the user asks about the song's content, meaning, themes,
    specific lines, or anything that requires reading the transcript.
    Returns the top 3 most relevant transcript chunks with timestamps.
    Args:
        query: The search query describing what to look for in the transcript.
        video_id: The YouTube video ID (e.g. 'H5v3kku4y6Q').
    """
    print(f"\n🔍 [search_transcript] Query: '{query}' | Video: {video_id}")
    collection_name = f"video_{video_id}"

    try:
        from pipeline import get_chroma_client

        if IS_PRODUCTION:
            chroma_client = get_chroma_client()
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                client=chroma_client,
            )
        else:
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=CHROMA_PATH,
            )

        print(f"   Connected to ChromaDB collection: {collection_name}")

        results = vectorstore.similarity_search(query, k=3)

        if not results:
            print("   No results found in ChromaDB.")
            return "No relevant transcript content found for that query."

        formatted = []
        for i, doc in enumerate(results, start=1):
            timestamp = doc.metadata.get("timestamp", "unknown time")
            chunk_text = doc.page_content.strip()
            formatted.append(f"[Chunk {i} | ~{timestamp}]\n{chunk_text}")

        output = "\n\n".join(formatted)
        print(f"   ✅ Returned {len(results)} chunks")
        return output

    except Exception as e:
        error_msg = f"Error searching transcript for video '{video_id}': {str(e)}"
        print(f"   ❌ {error_msg}")
        return error_msg

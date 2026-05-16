# backend/tools/extract_lyrics.py
# Tool 2: extract_lyrics
# Takes the raw transcript text of a music video and uses GPT-4o to clean it
# into properly formatted song lyrics — removing timestamps, fixing
# auto-caption errors, and adding verse/chorus structure.
# This tool calls the LLM directly (not ChromaDB).

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config import OPENAI_API_KEY

from pathlib import Path
CHROMA_PATH = str(Path(__file__).parent.parent / "chroma_db")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=OPENAI_API_KEY
)


def _get_full_transcript_from_chroma(video_id: str) -> str:
    """
    Retrieves all stored chunks for a video from ChromaDB and
    reassembles them into a single transcript string.
    Called internally by extract_lyrics — not exposed as a tool.
    """
    print(f"   Fetching all chunks from ChromaDB for video: {video_id}")
    collection_name = f"video_{video_id}"

    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_PATH
        )

        # get() with no filter returns all documents in the collection
        collection = vectorstore.get()
        documents = collection.get("documents", [])

        if not documents:
            return ""

        # Join all chunks in order — they were stored sequentially in Day 1
        full_text = " ".join(documents)
        print(f"   Retrieved {len(documents)} chunks, total length: {len(full_text)} chars")
        return full_text

    except Exception as e:
        print(f"   ❌ Error fetching from ChromaDB: {str(e)}")
        return ""


@tool
def extract_lyrics(video_id: str) -> str:
    """
    Extract and clean the lyrics from a YouTube music video transcript.
    Use this tool when the user asks to see the lyrics of the song,
    wants the words cleaned up, or asks what the song says word for word.
    Retrieves the full transcript from storage and formats it as song lyrics.

    Args:
        video_id: The YouTube video ID (e.g. 'H5v3kku4y6Q').
    """
    print(f"\n🎵 [extract_lyrics] Extracting lyrics for video: {video_id}")

    # Step 1 — Get the full raw transcript from ChromaDB
    raw_transcript = _get_full_transcript_from_chroma(video_id)

    if not raw_transcript:
        return (
            f"Could not find transcript for video '{video_id}'. "
            "Make sure the video has been analyzed first via POST /analyze."
        )

    # Step 2 — Send to GPT-4o to clean and format as lyrics
    print("   Sending transcript to GPT-4o for lyrics extraction...")

    system_prompt = """Format this raw transcript as song lyrics. Remove timestamps. Fix spelling errors using musical context. Add [Verse 1], [Chorus], [Bridge] labels where identifiable. Output lyrics only, no commentary."""

    user_message = f"""Clean this raw transcript into formatted song lyrics:

{raw_transcript}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        lyrics = response.content.strip()
        print(f"   ✅ Lyrics extracted successfully ({len(lyrics)} chars)")
        return lyrics

    except Exception as e:
        error_msg = f"Error extracting lyrics for video '{video_id}': {str(e)}"
        print(f"   ❌ {error_msg}")
        return error_msg
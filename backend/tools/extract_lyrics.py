# backend/tools/extract_lyrics.py
# Tool 2: extract_lyrics
# Takes the raw transcript text of a music video and uses GPT-4o to clean it
# into properly formatted song lyrics — removing timestamps, fixing
# auto-caption errors, and adding verse/chorus structure.

import os
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=OPENAI_API_KEY
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=OPENAI_API_KEY
)


def _get_full_transcript_from_pinecone(video_id: str) -> str:
    """
    Retrieves all stored chunks for a video from Pinecone and
    reassembles them into a single transcript string.
    """
    print(f"   Fetching all chunks from Pinecone for video: {video_id}")

    try:
        from pipeline import get_transcript_from_pinecone
        result = get_transcript_from_pinecone(video_id)

        if not result:
            return ""

        full_text = result["transcript_text"]
        print(f"   Retrieved transcript, total length: {len(full_text)} chars")
        return full_text

    except Exception as e:
        print(f"   ❌ Error fetching from Pinecone: {str(e)}")
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

    raw_transcript = _get_full_transcript_from_pinecone(video_id)

    if not raw_transcript:
        return (
            f"Could not find transcript for video '{video_id}'. "
            "Make sure the video has been analyzed first via POST /analyze."
        )

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

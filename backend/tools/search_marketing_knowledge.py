from langchain.tools import tool
from knowledge_search import search_knowledge
from request_context import current_source_key


@tool
def search_marketing_knowledge(query: str) -> str:
    """
    Searches the music marketing knowledge base for strategy,
    timelines, radio submission rules, social media plans,
    Spotify pitch guidelines, press release format, and
    distributor deadlines. Use this when the user asks HOW
    to do something marketing-related.
    """
    source_key = current_source_key.get()
    print(f"[search_marketing_knowledge] Query: '{query}' | source_key: {source_key}")
    result = search_knowledge(query, source_key=source_key, k=3)
    if not result:
        return "No relevant marketing knowledge found."
    print(f"   📚 Retrieved marketing knowledge chunks")
    return result

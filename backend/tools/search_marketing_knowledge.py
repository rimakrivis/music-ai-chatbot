from langchain.tools import tool
from knowledge_search import search_knowledge
from request_context import current_source_key

# Sources where the agent's own query can't be trusted to also surface a
# fixed, always-needed chunk (e.g. social_campaign's single execution-rules
# chunk, which a campaign-type query like "revive an old song" won't
# reliably match). Rather than relying on a system-prompt instruction to
# remember a second search — unenforceable, since the agent could just
# forget — every call for that source_key deterministically also fetches
# this fixed query, in code, so the coverage is guaranteed regardless of
# what the agent actually searched for.
_ALWAYS_INCLUDE_QUERY = {
    "social_campaign": "campaign execution rules timing posting cadence escalation deadline handling",
}


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

    always_query = _ALWAYS_INCLUDE_QUERY.get(source_key)
    if always_query:
        rules_result = search_knowledge(always_query, source_key=source_key, k=1)
        if rules_result and "Campaign Execution Rules" not in (result or ""):
            result = f"{result}\n\n---\n\n{rules_result}" if result else rules_result

    if not result:
        return "No relevant marketing knowledge found."
    print(f"   📚 Retrieved marketing knowledge chunks")
    return result

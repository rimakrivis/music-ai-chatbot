# backend/request_context.py
#
# Holds per-request values that need to reach a tool function without being
# passed as a tool argument. The agent + its tools are built ONCE at startup
# (see create_music_agent() in agent.py) and reused for every request, so a
# tool can't just take extra params for "which project is this" — the LLM
# would have to guess them. A contextvar set at the top of run_agent() and
# read inside the tool is the standard way around that; it's scoped per
# asyncio task, so concurrent requests don't clobber each other's value.

import contextvars

current_source_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_source_key", default=None
)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Backend (`backend/`):
```bash
pip install -r requirements.txt -r requirements-local.txt   # +Essentia genre detection, local only
python seed_knowledge.py                                     # re-embed backend/knowledge/*.md into Pinecone
uvicorn main:app --reload --port 8000
python evaluation.py                                          # only test harness; needs an already-analyzed video
```
No linter/formatter configured. No unit tests beyond `evaluation.py` — don't add test scaffolding unless asked.

Frontend (`frontend/`): `npm install && npm run dev` (localhost:3000), `npm run build`, `npm run lint`.

## Architecture

Full request-flow diagram: `README.md`. Below: only what spans multiple files.

- **Data model:** `band_id` (Supabase `bands`, one per session) scopes everything. `projects` (`id, band_id, project_type, details jsonb`) = one concrete instance — a release, a concert, etc. `calendar_events`/`todos` are band-scoped, optionally tagged `project_id`. No committed migration for `projects` (schema is dashboard-defined; only `migration_band_profile.sql` exists).
- **Two agent prompt paths** (`agent.py::_build_system_prompt`, branch on `project_type`): release types (`single_release`, `album_release`) get an embedded `[ ] Title — YYYY-MM-DD — type` checklist contract that `main.py::extract_tasks_from_response()` parses into calendar/todo rows after every `/chat` call. Everything else routes to `_build_non_release_prompt()` — structural only by design, injects `project_details`, defers content to `search_marketing_knowledge`, doesn't yet emit `[ ]` lines (so non-release chat output isn't extracted into calendar data yet).
- `TOOLS` and the LangGraph agent are built once at startup, shared across requests (memory = `InMemorySaver`, keyed by `thread_id` from `project_id` or `session_id_{project_type}`) — tools aren't rebuilt per request, so request-scoped context can't go through a tool closure.
- **Knowledge base:** `seed_knowledge.py` embeds `backend/knowledge/*.md` into one Pinecone namespace (`marketing_knowledge`), tagging chunks with `source` (`marketing_dist` / `concert`). Neither `search_marketing_knowledge` (agent tool) nor `/event-chat`'s inline lookup filter by it yet — release/concert content can both surface either way.
- **Two chat surfaces:** `/chat` → `agent.py::run_agent()` (multi-turn, has `project_type`/`band_id`/`project_id`). `/event-chat` → stateless-per-call completion behind `EventDrawer`'s per-task assistant; only gets video/song + task metadata, no project/band context today.
- **Frontend state:** `frontend/app/page.tsx` owns essentially all state via `useState`, passed down as props — no store. `frontend/app/chat/page.tsx` is an older pre-Concert-migration duplicate of the same dashboard.

## Working with Rima

For multi-file changes: propose one step, wait for it to land or get a go-ahead, then move to the next — don't batch unrelated steps into one pass unless asked.

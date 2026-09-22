# backend/project_context.py
#
# Shared lookups for "what is this project" — used by both the main agent
# (agent.py) and the per-task creative assistant (/event-chat in main.py),
# so both surfaces see the same project details + band profile instead of
# only the main chat knowing about them.

from database import get_project, get_band_profile


async def fetch_non_release_context(project_id: int | None, band_id: str | None) -> dict:
    """Fetch a project's details and its band's profile in one call.
    Fails soft — returns None for whichever piece isn't available, never
    raises, since missing context just means a shorter prompt, not an error."""
    project_details = None
    band_profile = None

    if project_id is not None:
        try:
            project_row = await get_project(project_id)
            if project_row:
                project_details = project_row.get("details") or None
        except Exception as e:
            print(f"   ⚠️ [project_context] Could not load project details: {e}")

    if band_id:
        try:
            profile_result = await get_band_profile(band_id)
            if profile_result and profile_result.get("status") != "empty":
                band_profile = profile_result.get("profile") or None
        except Exception as e:
            print(f"   ⚠️ [project_context] Could not load band profile: {e}")

    return {"project_details": project_details, "band_profile": band_profile}


def format_details_block(project_details: dict | None) -> str:
    if project_details:
        lines = "\n".join(f"- {k}: {v}" for k, v in project_details.items())
        return f"PROJECT DETAILS (captured during setup):\n{lines}"
    return (
        "PROJECT DETAILS: none captured yet. Do not assume specifics "
        "(e.g. paid/free, who's handling logistics) — ask the user if it "
        "matters for the question at hand."
    )


def format_band_profile_block(band_profile: dict | None) -> str:
    if not band_profile:
        return ""
    lines = "\n".join(f"- {k}: {v}" for k, v in band_profile.items())
    return f"\nBAND PROFILE:\n{lines}\n"

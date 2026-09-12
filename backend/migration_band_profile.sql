-- Adds the Artist Questionnaire / Band Profile fields to the existing
-- `bands` table. Follows the same JSONB "details" pattern already used
-- by the `projects` table (see create_project() in database.py) — one
-- flexible column instead of ~25 individual ones, since the whole
-- profile is always read/written as a single unit (full-context inject
-- into the agent prompt, full-form save-and-continue on the frontend).
--
-- Run this once in the Supabase SQL Editor.

alter table bands
  add column if not exists profile jsonb default '{}'::jsonb,
  add column if not exists profile_status text default 'empty'
    check (profile_status in ('empty', 'draft', 'complete')),
  add column if not exists profile_updated_at timestamptz;

-- profile shape (informal — not enforced by Postgres, validated in FastAPI):
-- {
--   "basic_info": {
--     "artist_name": str, "primary_genre": str, "sub_genres": [str],
--     "home_country": str, "main_markets": [str], "languages": [str],
--     "bio": str, "brand_voice": [str],
--     "social_handles": {"instagram": str, "tiktok": str, "spotify": str, "youtube": str},
--     "content_restrictions": str
--   },
--   "audience_platform": {
--     "spotify_monthly_listeners": int | null, "spotify_followers": int | null,
--     "instagram_followers": int | null, "tiktok_followers": int | null,
--     "youtube_subscribers": int | null, "email_list_size": int | null,
--     "unknown_metrics": [str],  -- which of the above were skipped via "I don't know"
--     "age_range": [int, int], "top_cities": [str]
--   },
--   "career_stage": {
--     "stage": "emerging" | "mid_level" | "established",
--     "previous_releases_count": int, "best_release_performance": str,
--     "live_shows": [{"city": str, "attendance": int | null, "venue_size": str}],
--     "has_manager": bool, "has_booking_agent": bool,
--     "has_label": bool, "label_name": str | null, "has_pr": bool,
--     "release_cadence": str, "comparable_artists": [str]
--   },
--   "strengths_weaknesses": {
--     "what_works": [str], "what_works_other": str | null,
--     "what_weak": [str], "what_weak_other": str | null,
--     "promotion_styles": [str], "promotion_styles_other": str | null
--   },
--   "practical_preferences": {
--     "venue_size": str, "ticket_price_min": number | null, "ticket_price_max": number | null,
--     "budget_level": "low" | "medium" | "high", "promo_lead_time": str,
--     "has_content_assets": bool, "content_assets_notes": str | null,
--     "sells_merch": bool, "merch_type": str | null, "timezone": str
--   },
--   "goals": {
--     "main_goals": [str], "main_goals_other": str | null,
--     "success_definition": str,
--     "known_upcoming_dates": [{"label": str, "date": str}] | null,
--     "no_dates_set": bool
--   }
-- }

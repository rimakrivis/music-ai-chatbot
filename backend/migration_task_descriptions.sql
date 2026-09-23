-- Adds a `description` column to `calendar_events` and `todos` so each
-- generated task can carry a concrete content idea (what to actually post/
-- do), not just a title/date/type. Shown in EventDrawer when a task is
-- opened, instead of the generic "what do you need?" greeting.
--
-- Same manual-run convention as migration_projects.sql — no migration
-- framework in this project, just a plain SQL file checked in for the
-- record. `add column if not exists` makes this safe to run more than
-- once.
--
-- Run this once in the Supabase SQL Editor.

alter table calendar_events add column if not exists description text;
alter table todos add column if not exists description text;


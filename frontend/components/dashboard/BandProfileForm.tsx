"use client";

import { useEffect, useState } from "react";
import { getBandProfile, updateBandProfile } from "@/lib/api";
import { BandProfile, EMPTY_BAND_PROFILE, BandProfileStatus } from "@/lib/types";

interface BandProfileFormProps {
  open: boolean;
  onClose: () => void;
  bandId: string;
}

const STEP_LABELS = [
  "Basic Info",
  "Audience & Platform",
  "Career Stage",
  "Strengths & Style",
  "Practical Prefs",
  "Goals",
];

// --- small shared field helpers --------------------------------------------

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="mb-3.5">
      <label className="text-xs text-slate-500 mb-1 flex items-center gap-1">
        {label}
        {required && <span className="text-rose-400">*</span>}
      </label>
      {children}
    </div>
  );
}

function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:border-slate-400"
    />
  );
}

function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 focus:outline-none focus:border-slate-400 resize-none"
    />
  );
}

// Comma-separated tag input — pragmatic first version for array fields
// (sub-genres, languages, comparable artists, etc). Upgradeable to chip UI later.
function TagInput({
  value,
  onChange,
  placeholder,
}: {
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  return (
    <TextInput
      type="text"
      placeholder={placeholder ?? "Comma-separated"}
      defaultValue={value.join(", ")}
      onBlur={(e) =>
        onChange(
          e.target.value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        )
      }
    />
  );
}

function MultiToggle({
  options,
  selected,
  onToggle,
}: {
  options: string[];
  selected: string[];
  onToggle: (opt: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const active = selected.includes(opt);
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onToggle(opt)}
            className={`rounded-lg px-2.5 py-1.5 text-xs font-medium border transition-colors ${
              active
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function SingleToggle({
  options,
  selected,
  onSelect,
}: {
  options: { value: string; label: string }[];
  selected: string;
  onSelect: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onSelect(opt.value)}
          className={`rounded-lg px-2.5 py-1.5 text-xs font-medium border transition-colors ${
            selected === opt.value
              ? "bg-slate-800 text-white border-slate-800"
              : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

const BRAND_VOICE_OPTIONS = ["Dark", "Playful", "Raw", "Polished", "Underground", "Glamorous", "DIY", "Cinematic"];
const WORKS_WELL_OPTIONS = ["Organic TikTok", "Local scene", "Email list", "Press", "Collaborations", "Livestreams", "Fan community"];
const WEAK_OPTIONS = ["Low reach", "No email list", "No visuals/content", "No press contacts", "Budget", "Time"];
const PROMO_STYLE_OPTIONS = ["Community-first", "Hype / FOMO / scarcity", "PR and media driven", "Guerrilla / low-budget", "Content-heavy / social first"];
const VENUE_SIZE_OPTIONS = [
  { value: "house_show", label: "House show" },
  { value: "small_club", label: "Small club (<200)" },
  { value: "mid_club", label: "Mid club (200–800)" },
  { value: "theater", label: "Theater (800–3000)" },
  { value: "arena", label: "Arena (3000+)" },
  { value: "na", label: "N/A — no live shows" },
];
const LEAD_TIME_OPTIONS = [
  { value: "1_2_weeks", label: "1–2 weeks" },
  { value: "3_4_weeks", label: "3–4 weeks" },
  { value: "5_8_weeks", label: "5–8 weeks" },
  { value: "8plus_weeks", label: "8+ weeks" },
];
const GOALS_OPTIONS = ["Grow streaming audience", "Sell out bigger venues", "Grow socials", "Break into new market", "Build email list", "Launch merch line"];

export default function BandProfileForm({ open, onClose, bandId }: BandProfileFormProps) {
  const [profile, setProfile] = useState<BandProfile>(EMPTY_BAND_PROFILE);
  const [status, setStatus] = useState<BandProfileStatus>("empty");
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !bandId) return;
    setLoading(true);
    getBandProfile(bandId)
      .then(({ profile: saved, status: savedStatus }) => {
        if (saved && Object.keys(saved).length > 0) {
          setProfile({ ...EMPTY_BAND_PROFILE, ...saved } as BandProfile);
        }
        setStatus(savedStatus);
        // Resume where they left off rather than restarting at step 0.
        setStep(0);
      })
      .catch((err) => console.error("[BandProfileForm] Failed to load profile", err))
      .finally(() => setLoading(false));
  }, [open, bandId]);

  if (!open) return null;

  const update = <K extends keyof BandProfile>(section: K, patch: Partial<BandProfile[K]>) => {
    setProfile((prev) => ({ ...prev, [section]: { ...prev[section], ...patch } }));
  };

  const toggleInArray = (section: keyof BandProfile, field: string, value: string) => {
    setProfile((prev) => {
      const current = (prev[section] as any)[field] as string[];
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
      return { ...prev, [section]: { ...prev[section], [field]: next } };
    });
  };

  const validateStep = (): string | null => {
    const b = profile.basic_info;
    const c = profile.career_stage;
    const sw = profile.strengths_weaknesses;
    const pp = profile.practical_preferences;
    const g = profile.goals;
    switch (step) {
      case 0:
        if (!b.artist_name.trim()) return "Artist / band name is required.";
        if (!b.primary_genre.trim()) return "Primary genre is required.";
        if (!b.home_country.trim()) return "Home country is required.";
        if (b.languages.length === 0) return "At least one language is required.";
        if (b.bio.trim().length < 20) return "Bio should be at least 20 characters.";
        if (b.brand_voice.length === 0) return "Pick at least one brand voice tag.";
        return null;
      case 1:
        return null; // all optional except age range, which always has a default
      case 2:
        if (!c.stage) return "Career stage is required.";
        if (c.previous_releases_count === null) return "Number of previous releases is required (0 is fine).";
        return null;
      case 3:
        if (sw.what_works.length === 0) return "Pick at least one thing that works well.";
        if (sw.what_weak.length === 0) return "Pick at least one weak/missing area.";
        if (sw.promotion_styles.length === 0) return "Pick at least one preferred promotion style.";
        return null;
      case 4:
        if (!pp.venue_size) return "Typical venue size is required.";
        if (!pp.budget_level) return "Usual campaign budget level is required.";
        if (!pp.promo_lead_time) return "Typical promo lead time is required.";
        return null;
      case 5:
        if (g.main_goals.length === 0) return "Pick at least one goal.";
        if (g.success_definition.trim().length < 10) return "Describe what success looks like.";
        if (!g.no_dates_set && g.known_upcoming_dates.length === 0)
          return "Add a known date, or check 'no dates set yet'.";
        return null;
      default:
        return null;
    }
  };

  const persist = async (finalStatus: BandProfileStatus) => {
    if (!bandId) return;
    setSaving(true);
    setError(null);
    try {
      await updateBandProfile(bandId, profile, finalStatus === "complete" ? "complete" : "draft");
      setStatus(finalStatus === "complete" ? "complete" : "draft");
    } catch (err) {
      console.error("[BandProfileForm] Failed to save profile", err);
      setError("Couldn't save — check your connection and try again.");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleNext = async () => {
    const validationError = validateStep();
    if (validationError) {
      setError(validationError);
      return;
    }
    try {
      await persist("draft");
      if (step < STEP_LABELS.length - 1) setStep((s) => s + 1);
      else {
        await persist("complete");
        onClose();
      }
    } catch {
      // error already set by persist()
    }
  };

  const handleBack = () => {
    setError(null);
    setStep((s) => Math.max(0, s - 1));
  };

  const handleSaveAndClose = async () => {
    try {
      await persist("draft");
      onClose();
    } catch {
      // error already set
    }
  };

  return (
    <>
      <div onClick={handleSaveAndClose} className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40" />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-xl w-full max-w-lg pointer-events-auto flex flex-col max-h-[85vh]">
          {/* Header + step indicator */}
          <div className="px-5 pt-5 pb-3 border-b border-slate-100 shrink-0">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-slate-800 font-semibold text-base">Artist Questionnaire</h2>
              <button type="button" onClick={handleSaveAndClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex items-center gap-1">
              {STEP_LABELS.map((label, i) => (
                <div key={label} className="flex-1">
                  <div className={`h-1 rounded-full ${i <= step ? "bg-slate-800" : "bg-slate-100"}`} />
                </div>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Step {step + 1} of {STEP_LABELS.length} — {STEP_LABELS[step]}
              {status === "draft" && " · draft saved"}
              {status === "complete" && " · complete"}
            </p>
          </div>

          {/* Body */}
          <div className="px-5 py-4 overflow-y-auto flex-1">
            {loading ? (
              <p className="text-sm text-slate-400">Loading…</p>
            ) : (
              <>
                {step === 0 && (
                  <>
                    <Field label="Artist / Band name" required>
                      <TextInput
                        value={profile.basic_info.artist_name}
                        onChange={(e) => update("basic_info", { artist_name: e.target.value })}
                      />
                    </Field>
                    <Field label="Primary genre" required>
                      <TextInput
                        value={profile.basic_info.primary_genre}
                        onChange={(e) => update("basic_info", { primary_genre: e.target.value })}
                      />
                    </Field>
                    <Field label="Sub-genres">
                      <TagInput
                        value={profile.basic_info.sub_genres}
                        onChange={(v) => update("basic_info", { sub_genres: v })}
                      />
                    </Field>
                    <Field label="Home country" required>
                      <TextInput
                        value={profile.basic_info.home_country}
                        onChange={(e) => update("basic_info", { home_country: e.target.value })}
                      />
                    </Field>
                    <Field label="Main markets">
                      <TagInput
                        value={profile.basic_info.main_markets}
                        onChange={(v) => update("basic_info", { main_markets: v })}
                      />
                    </Field>
                    <Field label="Languages used" required>
                      <TagInput
                        value={profile.basic_info.languages}
                        onChange={(v) => update("basic_info", { languages: v })}
                      />
                    </Field>
                    <Field label="Short bio (20–400 chars)" required>
                      <TextArea
                        rows={3}
                        value={profile.basic_info.bio}
                        onChange={(e) => update("basic_info", { bio: e.target.value })}
                      />
                    </Field>
                    <Field label="Brand voice / aesthetic (pick 1–4)" required>
                      <MultiToggle
                        options={BRAND_VOICE_OPTIONS}
                        selected={profile.basic_info.brand_voice}
                        onToggle={(v) => toggleInArray("basic_info", "brand_voice", v)}
                      />
                    </Field>
                    <Field label="Content restrictions (things to avoid)">
                      <TextInput
                        value={profile.basic_info.content_restrictions}
                        onChange={(e) => update("basic_info", { content_restrictions: e.target.value })}
                        placeholder="e.g. no profanity, family-friendly only"
                      />
                    </Field>
                  </>
                )}

                {step === 1 && (
                  <>
                    <p className="text-xs text-slate-400 mb-3">
                      All optional — leave blank if you don't track a number.
                    </p>
                    {([
                      ["spotify_monthly_listeners", "Spotify monthly listeners"],
                      ["spotify_followers", "Spotify followers"],
                      ["instagram_followers", "Instagram followers"],
                      ["tiktok_followers", "TikTok followers"],
                      ["youtube_subscribers", "YouTube subscribers"],
                      ["email_list_size", "Email list size"],
                    ] as const).map(([key, label]) => (
                      <Field key={key} label={label}>
                        <TextInput
                          type="number"
                          min={0}
                          value={profile.audience_platform[key] ?? ""}
                          onChange={(e) =>
                            update("audience_platform", {
                              [key]: e.target.value === "" ? null : Number(e.target.value),
                            } as any)
                          }
                        />
                      </Field>
                    ))}
                    <Field label="Audience age range" required>
                      <div className="flex items-center gap-2">
                        <TextInput
                          type="number"
                          className="w-20"
                          value={profile.audience_platform.age_range[0]}
                          onChange={(e) =>
                            update("audience_platform", {
                              age_range: [Number(e.target.value), profile.audience_platform.age_range[1]],
                            })
                          }
                        />
                        <span className="text-slate-400 text-sm">to</span>
                        <TextInput
                          type="number"
                          className="w-20"
                          value={profile.audience_platform.age_range[1]}
                          onChange={(e) =>
                            update("audience_platform", {
                              age_range: [profile.audience_platform.age_range[0], Number(e.target.value)],
                            })
                          }
                        />
                      </div>
                    </Field>
                    <Field label="Top cities (audience location)">
                      <TagInput
                        value={profile.audience_platform.top_cities}
                        onChange={(v) => update("audience_platform", { top_cities: v })}
                      />
                    </Field>
                  </>
                )}

                {step === 2 && (
                  <>
                    <Field label="Career stage" required>
                      <SingleToggle
                        options={[
                          { value: "emerging", label: "Emerging" },
                          { value: "mid_level", label: "Mid-level" },
                          { value: "established", label: "Established" },
                        ]}
                        selected={profile.career_stage.stage}
                        onSelect={(v) => update("career_stage", { stage: v as any })}
                      />
                    </Field>
                    <Field label="Number of previous releases" required>
                      <TextInput
                        type="number"
                        min={0}
                        value={profile.career_stage.previous_releases_count ?? ""}
                        onChange={(e) =>
                          update("career_stage", {
                            previous_releases_count: e.target.value === "" ? null : Number(e.target.value),
                          })
                        }
                      />
                    </Field>
                    <Field label="Best release performance so far">
                      <TextInput
                        value={profile.career_stage.best_release_performance}
                        onChange={(e) => update("career_stage", { best_release_performance: e.target.value })}
                        placeholder="e.g. 120k streams"
                      />
                    </Field>
                    <Field label="Release cadence">
                      <TextInput
                        value={profile.career_stage.release_cadence}
                        onChange={(e) => update("career_stage", { release_cadence: e.target.value })}
                        placeholder="e.g. quarterly, one-off, album-cycle only"
                      />
                    </Field>
                    <Field label="Comparable artists">
                      <TagInput
                        value={profile.career_stage.comparable_artists}
                        onChange={(v) => update("career_stage", { comparable_artists: v })}
                      />
                    </Field>
                    <div className="grid grid-cols-2 gap-2 mb-1">
                      {([
                        ["has_manager", "Has manager"],
                        ["has_booking_agent", "Has booking agent"],
                        ["has_label", "Has label"],
                        ["has_pr", "Has PR support"],
                      ] as const).map(([key, label]) => (
                        <label key={key} className="flex items-center gap-2 text-xs text-slate-600">
                          <input
                            type="checkbox"
                            checked={profile.career_stage[key]}
                            onChange={(e) => update("career_stage", { [key]: e.target.checked } as any)}
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                  </>
                )}

                {step === 3 && (
                  <>
                    <Field label="What usually works well? (pick 1+)" required>
                      <MultiToggle
                        options={WORKS_WELL_OPTIONS}
                        selected={profile.strengths_weaknesses.what_works}
                        onToggle={(v) => toggleInArray("strengths_weaknesses", "what_works", v)}
                      />
                    </Field>
                    <Field label="What's currently weak or missing? (pick 1+)" required>
                      <MultiToggle
                        options={WEAK_OPTIONS}
                        selected={profile.strengths_weaknesses.what_weak}
                        onToggle={(v) => toggleInArray("strengths_weaknesses", "what_weak", v)}
                      />
                    </Field>
                    <Field label="Preferred promotion styles (pick 1+)" required>
                      <MultiToggle
                        options={PROMO_STYLE_OPTIONS}
                        selected={profile.strengths_weaknesses.promotion_styles}
                        onToggle={(v) => toggleInArray("strengths_weaknesses", "promotion_styles", v)}
                      />
                    </Field>
                  </>
                )}

                {step === 4 && (
                  <>
                    <Field label="Typical venue size" required>
                      <SingleToggle
                        options={VENUE_SIZE_OPTIONS}
                        selected={profile.practical_preferences.venue_size}
                        onSelect={(v) => update("practical_preferences", { venue_size: v })}
                      />
                    </Field>
                    <Field label="Average ticket price range">
                      <div className="flex items-center gap-2">
                        <TextInput
                          type="number"
                          min={0}
                          className="w-24"
                          value={profile.practical_preferences.ticket_price_min ?? ""}
                          onChange={(e) =>
                            update("practical_preferences", {
                              ticket_price_min: e.target.value === "" ? null : Number(e.target.value),
                            })
                          }
                        />
                        <span className="text-slate-400 text-sm">to</span>
                        <TextInput
                          type="number"
                          min={0}
                          className="w-24"
                          value={profile.practical_preferences.ticket_price_max ?? ""}
                          onChange={(e) =>
                            update("practical_preferences", {
                              ticket_price_max: e.target.value === "" ? null : Number(e.target.value),
                            })
                          }
                        />
                      </div>
                    </Field>
                    <Field label="Usual campaign budget level" required>
                      <SingleToggle
                        options={[
                          { value: "low", label: "Low" },
                          { value: "medium", label: "Medium" },
                          { value: "high", label: "High" },
                        ]}
                        selected={profile.practical_preferences.budget_level}
                        onSelect={(v) => update("practical_preferences", { budget_level: v as any })}
                      />
                    </Field>
                    <Field label="Typical promo lead time" required>
                      <SingleToggle
                        options={LEAD_TIME_OPTIONS}
                        selected={profile.practical_preferences.promo_lead_time}
                        onSelect={(v) => update("practical_preferences", { promo_lead_time: v })}
                      />
                    </Field>
                    <div className="grid grid-cols-2 gap-3 mb-1">
                      <label className="flex items-center gap-2 text-xs text-slate-600">
                        <input
                          type="checkbox"
                          checked={!!profile.practical_preferences.has_content_assets}
                          onChange={(e) => update("practical_preferences", { has_content_assets: e.target.checked })}
                        />
                        Has content assets ready
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-600">
                        <input
                          type="checkbox"
                          checked={!!profile.practical_preferences.sells_merch}
                          onChange={(e) => update("practical_preferences", { sells_merch: e.target.checked })}
                        />
                        Currently selling merch
                      </label>
                    </div>
                    <Field label="Timezone">
                      <TextInput
                        value={profile.practical_preferences.timezone}
                        onChange={(e) => update("practical_preferences", { timezone: e.target.value })}
                        placeholder="e.g. Europe/Amsterdam"
                      />
                    </Field>
                  </>
                )}

                {step === 5 && (
                  <>
                    <Field label="Main goals for next 6–12 months (pick 1–3)" required>
                      <MultiToggle
                        options={GOALS_OPTIONS}
                        selected={profile.goals.main_goals}
                        onToggle={(v) => toggleInArray("goals", "main_goals", v)}
                      />
                    </Field>
                    <Field label="What does success look like?" required>
                      <TextArea
                        rows={3}
                        value={profile.goals.success_definition}
                        onChange={(e) => update("goals", { success_definition: e.target.value })}
                      />
                    </Field>
                    <label className="flex items-center gap-2 text-xs text-slate-600 mb-2">
                      <input
                        type="checkbox"
                        checked={profile.goals.no_dates_set}
                        onChange={(e) => update("goals", { no_dates_set: e.target.checked })}
                      />
                      No dates set yet
                    </label>
                    {!profile.goals.no_dates_set && (
                      <Field label="Known upcoming dates" required>
                        <TextArea
                          rows={2}
                          placeholder="e.g. Release date: 2026-11-14, Tour kickoff: 2026-12-01"
                          defaultValue={profile.goals.known_upcoming_dates
                            .map((d) => `${d.label}: ${d.date}`)
                            .join("\n")}
                          onBlur={(e) => {
                            const parsed = e.target.value
                              .split("\n")
                              .map((line) => {
                                const [label, date] = line.split(":").map((s) => s.trim());
                                return label && date ? { label, date } : null;
                              })
                              .filter(Boolean) as { label: string; date: string }[];
                            update("goals", { known_upcoming_dates: parsed });
                          }}
                        />
                      </Field>
                    )}
                  </>
                )}

                {error && <p className="text-xs text-rose-500 mt-2">{error}</p>}
              </>
            )}
          </div>

          {/* Footer nav */}
          <div className="px-5 py-4 border-t border-slate-100 flex gap-2 shrink-0">
            {step > 0 && (
              <button
                type="button"
                onClick={handleBack}
                className="rounded-xl px-3 py-2 text-sm font-medium text-slate-500 border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                Back
              </button>
            )}
            <div className="flex-1" />
            <button
              type="button"
              onClick={handleSaveAndClose}
              className="rounded-xl px-3 py-2 text-sm font-medium text-slate-500 border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              Save &amp; close
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={saving || loading}
              className="rounded-xl px-4 py-2 text-sm font-medium bg-slate-800 text-white hover:bg-slate-700 transition-colors disabled:opacity-50"
            >
              {saving ? "Saving…" : step < STEP_LABELS.length - 1 ? "Next" : "Finish"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

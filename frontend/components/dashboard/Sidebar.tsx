"use client";

import { useState } from "react";
import MiniCalendar from "./MiniCalendar";
import ProgressBar from "./ProgressBar";
import { PROJECT_TYPES, ProjectType } from "./ProjectTypeSelector";
import { CalendarEvent, TodoItem } from "@/lib/types";

interface SidebarProps {
  events: CalendarEvent[];
  onEventClick: (event: CalendarEvent) => void;
  progress: number;
  todos: TodoItem[];
  onOpenTodoDrawer: () => void;
  onOpenBandProfile: () => void;
  activeProjectType: ProjectType | null;
  onSelectProjectType: (type: ProjectType) => void;
  onShowAgenda: () => void;
  onOpenAddEventModal: () => void;
  onReset: () => void;
  mobileNavOpen: boolean;
  onCloseMobileNav: () => void;
}

// Sections that expand downward. Only one of Calendar/Progress/Projects is
// open at a time (accordion behavior) — independent from which center view
// (Agenda, handled in page.tsx) is currently showing.
type AccordionSection = "calendar" | "progress" | "projects" | null;

function IconMenu() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}
function IconAgenda({ active }: { active?: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={active ? "#ffffff" : "#475569"} strokeWidth="1.5">
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18M8 3v3M16 3v3" />
    </svg>
  );
}
function IconClose() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}
function IconChevron({ direction }: { direction: "down" | "right" }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
      {direction === "down" ? <path d="M6 9l6 6 6-6" /> : <path d="M9 6l6 6-6 6" />}
    </svg>
  );
}
function IconProgress() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
      <path d="M4 19V10M12 19V5M20 19v-6" />
    </svg>
  );
}
function IconTodo() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="M8 12l2.5 2.5L16 9" />
    </svg>
  );
}
function IconBandProfile() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <circle cx="12" cy="9" r="2.5" />
      <path d="M8 17c1-2 7-2 8 0" />
    </svg>
  );
}
function IconProjects() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
      <circle cx="9" cy="7" r="3.2" />
      <path d="M2.5 20a6.5 6.5 0 0113 0" />
      <circle cx="17.5" cy="8.5" r="2.5" />
      <path d="M15 20a5 5 0 018-4" />
    </svg>
  );
}
function IconAddEvent() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18M8 3v3M16 3v3" />
      <path d="M12 13v5M9.5 15.5h5" />
    </svg>
  );
}
function IconReset() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="1.8">
      <path d="M4 4v6h6" />
      <path d="M4.5 10a8 8 0 1 1 2 8.5" />
    </svg>
  );
}

export default function Sidebar({
  events,
  onEventClick,
  progress,
  todos,
  onOpenTodoDrawer,
  onOpenBandProfile,
  activeProjectType,
  onSelectProjectType,
  onShowAgenda,
  onOpenAddEventModal,
  onReset,
  mobileNavOpen,
  onCloseMobileNav,
}: SidebarProps) {
  // null = auto (CSS decides: icon-only at tablet widths, expanded at desktop),
  // true/false = user has explicitly overridden the toggle at any width.
  const [manualOverride, setManualOverride] = useState<boolean | null>(null);
  const [openSection, setOpenSection] = useState<AccordionSection>("calendar");

  const toggleSection = (section: AccordionSection) =>
    setOpenSection((prev) => (prev === section ? null : section));

  const completedTodos = todos.filter((t) => t.completed).length;

  const handleToggle = () => {
    const currentlyIconOnly =
      manualOverride !== null
        ? manualOverride
        : typeof window !== "undefined" &&
          window.matchMedia("(min-width: 768px) and (max-width: 1023.98px)").matches;
    setManualOverride(!currentlyIconOnly);
  };

  const widthClass =
    manualOverride === true
      ? "w-[280px] md:w-[68px]"
      : manualOverride === false
      ? "w-[280px] md:w-[320px]"
      : "w-[280px] md:w-[68px] lg:w-[320px]";

  // Label/body visibility mirrors widthClass so icon-only sections stay
  // mounted (just hidden) instead of unmounting per breakpoint.
  const labelClass =
    manualOverride === true
      ? "hidden"
      : manualOverride === false
      ? "inline"
      : "inline md:hidden lg:inline";
  const bodyClass =
    manualOverride === true
      ? "hidden"
      : manualOverride === false
      ? "block"
      : "block md:hidden lg:block";

  const navItemClass =
    "flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-sm text-slate-600 hover:bg-slate-50 transition-colors w-full text-left";

  return (
    <>
      {/* Backdrop — mobile nav drawer only; Sidebar is static in-flow at md:+ */}
      {mobileNavOpen && (
        <div
          onClick={onCloseMobileNav}
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-slate-200 p-3.5 h-full overflow-y-auto transition-[width,transform] duration-300 ease-out shrink-0 ${widthClass} ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        } md:static md:z-auto md:translate-x-0`}
      >
        <div className="flex items-center justify-between mb-2">
          <button
            type="button"
            onClick={handleToggle}
            className="hidden md:inline-flex p-2 rounded-xl hover:bg-slate-50 transition-colors self-start"
            title="Toggle sidebar"
          >
            <IconMenu />
          </button>
          <button
            type="button"
            onClick={onCloseMobileNav}
            className="md:hidden p-2 rounded-xl hover:bg-slate-50 transition-colors self-start ml-auto"
            title="Close menu"
          >
            <IconClose />
          </button>
        </div>

        {/* Agenda — shows every task for the band. Active whenever no project
          type is selected; clicking it clears the project filter. */}
      <button
        type="button"
        onClick={onShowAgenda}
        className={`${navItemClass} mb-1 ${
          !activeProjectType ? "bg-slate-800 text-white hover:bg-slate-800" : ""
        }`}
      >
        <IconAgenda active={!activeProjectType} />
        <span className={`font-medium ${labelClass}`}>Agenda</span>
      </button>

      {/* Calendar accordion */}
      <div>
        <button type="button" onClick={() => toggleSection("calendar")} className={navItemClass + " justify-between"}>
          <span className="flex items-center gap-2.5">
            <IconAgenda />
            <span className={labelClass}>Calendar</span>
          </span>
          <span className={labelClass}>
            <IconChevron direction={openSection === "calendar" ? "down" : "right"} />
          </span>
        </button>
        {openSection === "calendar" && (
          <div className={`pt-1 pb-2 px-0.5 ${bodyClass}`}>
            <MiniCalendar events={events} onEventClick={onEventClick} />
          </div>
        )}
      </div>

      {/* Progress accordion */}
      <div>
        <button type="button" onClick={() => toggleSection("progress")} className={navItemClass + " justify-between"}>
          <span className="flex items-center gap-2.5">
            <IconProgress />
            <span className={labelClass}>Progress</span>
          </span>
          <span className={labelClass}>
            <IconChevron direction={openSection === "progress" ? "down" : "right"} />
          </span>
        </button>
        {openSection === "progress" && (
          <div className={`pt-1 pb-2 px-0.5 ${bodyClass}`}>
            <ProgressBar progress={progress} />
          </div>
        )}
      </div>

      {/* To-do — opens as a drawer (page.tsx owns the open/close state) */}
      <button type="button" onClick={onOpenTodoDrawer} className={navItemClass + " justify-between"}>
        <span className="flex items-center gap-2.5">
          <IconTodo />
          <span className={labelClass}>To-do list</span>
        </span>
        {todos.length > 0 && (
          <span className={`text-[10px] text-slate-400 border border-slate-200 rounded-md px-1.5 py-0.5 ${labelClass}`}>
            {completedTodos}/{todos.length}
          </span>
        )}
      </button>

      <div className="border-t border-slate-100 my-2" />

      {/* Band profile — above Projects, per approved layout */}
      <button type="button" onClick={onOpenBandProfile} className={navItemClass}>
        <IconBandProfile />
        <span className={labelClass}>Band profile</span>
      </button>

      {/* Projects accordion — nests the "what are you planning?" type buttons */}
      <div>
        <button type="button" onClick={() => toggleSection("projects")} className={navItemClass + " justify-between"}>
          <span className="flex items-center gap-2.5">
            <IconProjects />
            <span className={labelClass}>Projects</span>
          </span>
          <span className={labelClass}>
            <IconChevron direction={openSection === "projects" ? "down" : "right"} />
          </span>
        </button>
        {openSection === "projects" && (
          <div className={`pt-0.5 pb-1 pl-2 flex flex-col gap-0.5 ${bodyClass}`}>
            {PROJECT_TYPES.map((pt) => {
              const active = activeProjectType === pt.id;
              return (
                <button
                  key={pt.id}
                  type="button"
                  onClick={() => onSelectProjectType(pt.id)}
                  className={`flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-xs transition-colors text-left ${
                    active ? "bg-slate-100 text-slate-900 font-medium" : "text-slate-500 hover:bg-slate-50"
                  }`}
                >
                  <pt.Icon active={false} />
                  {pt.label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Manual calendar entry — independent of the agent flow */}
      <button type="button" onClick={onOpenAddEventModal} className={navItemClass}>
        <IconAddEvent />
        <span className={labelClass}>Add to calendar</span>
      </button>

      <div className="flex-1" />

      <div className="border-t border-slate-100 mt-2 mb-2" />
      <button
        type="button"
        onClick={onReset}
        className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-xs text-slate-300 hover:text-rose-400 transition-colors w-full text-left"
        title="Clear band data"
      >
        <IconReset />
        <span className={labelClass}>reset</span>
      </button>
      </aside>
    </>
  );
}

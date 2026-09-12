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
  onOpenAddEventModal: () => void;
  onReset: () => void;
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
  onOpenAddEventModal,
  onReset,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [openSection, setOpenSection] = useState<AccordionSection>("calendar");

  const toggleSection = (section: AccordionSection) =>
    setOpenSection((prev) => (prev === section ? null : section));

  const completedTodos = todos.filter((t) => t.completed).length;

  const navItemClass =
    "flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-sm text-slate-600 hover:bg-slate-50 transition-colors w-full text-left";

  return (
    <aside
      className={`flex flex-col bg-white rounded-2xl border border-slate-100 shadow-sm p-3.5 lg:sticky lg:top-6 lg:h-fit lg:max-h-[calc(100vh-48px)] overflow-y-auto transition-[width] ${
        collapsed ? "w-[68px]" : "w-[220px]"
      }`}
    >
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="p-2 rounded-xl hover:bg-slate-50 transition-colors mb-2 self-start"
        title={collapsed ? "Expand" : "Collapse"}
      >
        <IconMenu />
      </button>

      {/* Agenda — always the default center view; this button doesn't need
          local "active" state since page.tsx has no other center view to
          switch away from besides the To-do drawer, which overlays rather
          than replaces. */}
      <button type="button" className={`${navItemClass} bg-slate-800 text-white hover:bg-slate-800 mb-1`}>
        <IconAgenda active />
        {!collapsed && <span className="font-medium">Agenda</span>}
      </button>

      {/* Calendar accordion */}
      <div>
        <button type="button" onClick={() => toggleSection("calendar")} className={navItemClass + " justify-between"}>
          <span className="flex items-center gap-2.5">
            <IconAgenda />
            {!collapsed && "Calendar"}
          </span>
          {!collapsed && <IconChevron direction={openSection === "calendar" ? "down" : "right"} />}
        </button>
        {!collapsed && openSection === "calendar" && (
          <div className="pt-1 pb-2 px-0.5">
            <MiniCalendar events={events} onEventClick={onEventClick} />
          </div>
        )}
      </div>

      {/* Progress accordion */}
      <div>
        <button type="button" onClick={() => toggleSection("progress")} className={navItemClass + " justify-between"}>
          <span className="flex items-center gap-2.5">
            <IconProgress />
            {!collapsed && "Progress"}
          </span>
          {!collapsed && <IconChevron direction={openSection === "progress" ? "down" : "right"} />}
        </button>
        {!collapsed && openSection === "progress" && (
          <div className="pt-1 pb-2 px-0.5">
            <ProgressBar progress={progress} />
          </div>
        )}
      </div>

      {/* To-do — opens as a drawer (page.tsx owns the open/close state) */}
      <button type="button" onClick={onOpenTodoDrawer} className={navItemClass + " justify-between"}>
        <span className="flex items-center gap-2.5">
          <IconTodo />
          {!collapsed && "To-do list"}
        </span>
        {!collapsed && todos.length > 0 && (
          <span className="text-[10px] text-slate-400 border border-slate-200 rounded-md px-1.5 py-0.5">
            {completedTodos}/{todos.length}
          </span>
        )}
      </button>

      <div className="border-t border-slate-100 my-2" />

      {/* Band profile — above Projects, per approved layout */}
      <button type="button" onClick={onOpenBandProfile} className={navItemClass}>
        <IconBandProfile />
        {!collapsed && "Band profile"}
      </button>

      {/* Projects accordion — nests the "what are you planning?" type buttons */}
      <div>
        <button type="button" onClick={() => toggleSection("projects")} className={navItemClass + " justify-between"}>
          <span className="flex items-center gap-2.5">
            <IconProjects />
            {!collapsed && "Projects"}
          </span>
          {!collapsed && <IconChevron direction={openSection === "projects" ? "down" : "right"} />}
        </button>
        {!collapsed && openSection === "projects" && (
          <div className="pt-0.5 pb-1 pl-2 flex flex-col gap-0.5">
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
        {!collapsed && "Add to calendar"}
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
        {!collapsed && "reset"}
      </button>
    </aside>
  );
}

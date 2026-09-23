"use client";
import ReactMarkdown from "react-markdown";

// Renders assistant replies (bold, bullet/numbered lists, paragraph breaks)
// instead of dumping raw markdown text into one unstyled blob. Shared by
// every chat surface (main AIChatbot, EventDrawer's per-task assistant) so
// formatting stays consistent across the app.
export default function AssistantMessageContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
        ul: ({ children }) => <ul className="mb-2 last:mb-0 pl-4 space-y-1 list-disc marker:text-slate-400">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 last:mb-0 pl-4 space-y-1 list-decimal marker:text-slate-400">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="underline text-slate-800 hover:text-slate-600">
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

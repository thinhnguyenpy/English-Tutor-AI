import { NotebookPen } from "lucide-react";

import type { FeedbackType, TurnFeedback } from "@/api/types";

const TYPE_STYLES: Record<FeedbackType, string> = {
  grammar: "bg-amber-100 text-amber-800",
  vocabulary: "bg-violet-100 text-violet-800",
  naturalness: "bg-sky-100 text-sky-800",
};

interface Props {
  items: TurnFeedback[];
}

export default function FeedbackPanel({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-slate-400">
        <NotebookPen size={28} className="mx-auto mb-3 text-slate-300" />
        <p className="font-medium text-slate-500">No notes yet</p>
        <p className="mt-1.5 leading-relaxed">
          When something you say could be phrased better, the correction shows up here a
          few seconds later — without interrupting the conversation.
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-2.5 px-4 py-4">
      {items.map((item) => (
        <li
          key={item.id}
          className="rounded-lg bg-white p-3 text-sm ring-1 ring-slate-200"
        >
          <div className="mb-2 flex items-center gap-2">
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                TYPE_STYLES[item.type] ?? "bg-slate-100 text-slate-700"
              }`}
            >
              {item.type}
            </span>
            {item.severity === "major" && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-rose-600">
                major
              </span>
            )}
          </div>

          <p className="text-slate-400 line-through decoration-rose-300">{item.original}</p>
          <p className="mt-1 font-medium text-emerald-700">{item.corrected}</p>
          <p className="mt-1.5 text-[13px] leading-snug text-slate-500">{item.explanation}</p>
        </li>
      ))}
    </ul>
  );
}

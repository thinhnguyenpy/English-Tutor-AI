import { BrainCircuit, X } from "lucide-react";

import { MEMORY_KIND_LABELS, type MemoryGroup } from "@/api/types";

interface Props {
  groups: MemoryGroup[];
  onDismiss: (id: string) => void;
}

export default function MemoryPanel({ groups, onDismiss }: Props) {
  const total = groups.reduce((sum, group) => sum + group.items.length, 0);

  if (total === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-slate-400">
        <BrainCircuit size={28} className="mx-auto mb-3 text-slate-300" />
        <p className="font-medium text-slate-500">Nothing remembered yet</p>
        <p className="mt-1.5 leading-relaxed">
          Talk for a few turns and the tutor starts keeping notes about your life, so it
          can pick the thread back up next time.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5 px-4 py-4">
      {groups.map((group) => (
        <section key={group.kind}>
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            {MEMORY_KIND_LABELS[group.kind] ?? group.kind}
          </h3>
          <ul className="space-y-1.5">
            {group.items.map((memory) => (
              <li
                key={memory.id}
                className="group flex items-start gap-2 rounded-lg bg-white px-3 py-2 text-sm text-slate-700 ring-1 ring-slate-200"
              >
                <span className="flex-1 leading-snug">{memory.content}</span>
                <button
                  type="button"
                  onClick={() => onDismiss(memory.id)}
                  title="Forget this — the tutor stops using it and won't re-add it"
                  className="mt-0.5 shrink-0 text-slate-300 opacity-0 transition hover:text-rose-600 group-hover:opacity-100"
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

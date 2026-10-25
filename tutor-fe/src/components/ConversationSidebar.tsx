import { Check, MessageSquarePlus, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";

import type { Conversation } from "@/api/types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  maxActive: number;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  maxActive,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const startEditing = (conversation: Conversation) => {
    setEditingId(conversation.id);
    setDraft(conversation.title);
  };

  const commit = (id: string) => {
    const title = draft.trim();
    if (title) onRename(id, title);
    setEditingId(null);
  };

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center justify-between px-4 py-4">
        <h1 className="text-sm font-semibold text-slate-900">English Tutor</h1>
        <button
          type="button"
          onClick={onCreate}
          title="New conversation"
          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-brand-600"
        >
          <MessageSquarePlus size={18} />
        </button>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 && (
          <p className="px-3 py-6 text-sm text-slate-400">
            No conversations yet. Start one and just talk.
          </p>
        )}

        {conversations.map((conversation) => {
          const active = conversation.id === activeId;
          const editing = editingId === conversation.id;

          return (
            <div
              key={conversation.id}
              className={`group flex items-center gap-1 rounded-lg px-2 py-2 text-sm transition ${
                active ? "bg-brand-50 text-brand-800" : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {editing ? (
                <>
                  <input
                    autoFocus
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commit(conversation.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    className="min-w-0 flex-1 rounded border border-brand-300 px-1.5 py-0.5 text-sm outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => commit(conversation.id)}
                    className="p-1 text-slate-500 hover:text-emerald-600"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="p-1 text-slate-500 hover:text-slate-800"
                  >
                    <X size={14} />
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => onSelect(conversation.id)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <div className="truncate font-medium">{conversation.title}</div>
                    <div className="truncate text-[11px] text-slate-400">
                      {conversation.turn_count} turn
                      {conversation.turn_count === 1 ? "" : "s"}
                      {conversation.summary ? ` · ${conversation.summary}` : ""}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => startEditing(conversation)}
                    title="Rename"
                    className="p-1 text-slate-400 opacity-0 transition hover:text-slate-700 group-hover:opacity-100"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(conversation.id)}
                    title="Delete"
                    className="p-1 text-slate-400 opacity-0 transition hover:text-rose-600 group-hover:opacity-100"
                  >
                    <Trash2 size={14} />
                  </button>
                </>
              )}
            </div>
          );
        })}
      </nav>

      <p className="border-t border-slate-100 px-4 py-3 text-[11px] leading-relaxed text-slate-400">
        Keeps your {maxActive} most recent conversations. Older ones are archived, never
        deleted — what the tutor learned about you stays.
      </p>
    </aside>
  );
}

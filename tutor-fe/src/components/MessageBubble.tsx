import { Bot, User } from "lucide-react";

import type { MessageRole } from "@/api/types";

interface Props {
  role: MessageRole;
  text: string;
  /** Streaming replies render with a caret and no timestamp. */
  pending?: boolean;
  createdAt?: string;
}

export default function MessageBubble({ role, text, pending, createdAt }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-600"
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className={`max-w-[75%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-left text-sm leading-relaxed ${
            isUser
              ? "rounded-tr-sm bg-brand-600 text-white"
              : "rounded-tl-sm bg-white text-slate-800 shadow-sm ring-1 ring-slate-200"
          }`}
        >
          {/* Rendered as text, never as HTML — this is model output. */}
          {text}
          {pending && <span className="ml-0.5 animate-pulse">▍</span>}
        </div>
        {createdAt && !pending && (
          <div className="mt-1 text-[11px] text-slate-400">
            {new Date(createdAt).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        )}
      </div>
    </div>
  );
}

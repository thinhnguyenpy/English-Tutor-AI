import { SendHorizontal } from "lucide-react";
import { useState } from "react";

/** Mirrors MAX_TURN_CHARS in tutor-be/src/core/config.py — longer turns are refused. */
const MAX_TURN_CHARS = 1000;

interface Props {
  disabled?: boolean;
  onSend: (text: string) => void;
}

/**
 * Typed turns, for when speech is unavailable (Firefox, mic denied, a noisy
 * room) — and the quickest way to exercise the tutor without speaking.
 */
export default function TextTurnInput({ disabled, onSend }: Props) {
  const [text, setText] = useState("");
  const trimmed = text.trim();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <form onSubmit={submit} className="flex w-full max-w-xl items-center gap-2 px-6">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={MAX_TURN_CHARS}
        disabled={disabled}
        placeholder="…or type what you want to say"
        className="flex-1 rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 outline-none focus:border-brand-400 disabled:bg-slate-50"
      />
      <button
        type="submit"
        disabled={disabled || !trimmed}
        aria-label="Send"
        className="rounded-full p-2 text-brand-600 transition hover:bg-brand-50 disabled:text-slate-300"
      >
        <SendHorizontal size={18} />
      </button>
    </form>
  );
}

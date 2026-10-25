import { Loader2, Mic, Square } from "lucide-react";

interface Props {
  listening: boolean;
  busy: boolean;
  disabled?: boolean;
  onToggle: () => void;
}

export default function MicButton({ listening, busy, disabled, onToggle }: Props) {
  const label = busy ? "Tutor is replying" : listening ? "Stop recording" : "Start speaking";

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled || busy}
      aria-label={label}
      title={label}
      className={`relative flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition
        disabled:cursor-not-allowed disabled:bg-slate-300
        ${listening ? "bg-rose-600 hover:bg-rose-700" : "bg-brand-600 hover:bg-brand-700"}`}
    >
      {listening && (
        <span className="absolute inset-0 animate-ping rounded-full bg-rose-500 opacity-40" />
      )}
      {busy ? (
        <Loader2 size={24} className="animate-spin" />
      ) : listening ? (
        <Square size={22} fill="currentColor" />
      ) : (
        <Mic size={24} />
      )}
    </button>
  );
}

import type { Topic } from "@/api/types";

const LEVEL_STYLES: Record<Topic["level"], string> = {
  beginner: "bg-emerald-100 text-emerald-700",
  intermediate: "bg-amber-100 text-amber-700",
  advanced: "bg-rose-100 text-rose-700",
};

interface Props {
  topics: Topic[];
  onPick: (topic: Topic) => void;
}

export default function TopicPicker({ topics, onPick }: Props) {
  if (topics.length === 0) return null;

  return (
    <div className="mx-auto max-w-2xl">
      <p className="mb-3 text-center text-sm text-slate-400">
        …or pick something to talk about
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {topics.map((topic) => (
          <button
            key={topic.id}
            type="button"
            onClick={() => onPick(topic)}
            className="group flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-sm text-slate-700 shadow-sm transition hover:border-brand-300 hover:text-brand-700"
          >
            {topic.title}
            <span
              className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${LEVEL_STYLES[topic.level]}`}
            >
              {topic.level}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

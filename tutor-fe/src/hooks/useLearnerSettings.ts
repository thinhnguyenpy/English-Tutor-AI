import { useEffect, useState } from "react";

import type { Difficulty, FeedbackStyle } from "@/api/types";

/**
 * The student's own level and feedback preference. Global, not per
 * conversation — they describe the learner, not the session — and sent with
 * every turn, so the server stores nothing.
 *
 * localStorage can throw (private windows, blocked site data); the defaults
 * then simply apply for this visit.
 */
function read<T extends string>(key: string, fallback: T): T {
  try {
    return (localStorage.getItem(key) as T | null) ?? fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* not persisted this visit */
  }
}

export function useLearnerSettings() {
  const [difficulty, setDifficulty] = useState<Difficulty>(() =>
    read("tutor.difficulty", "intermediate"),
  );
  const [feedbackStyle, setFeedbackStyle] = useState<FeedbackStyle>(() =>
    read("tutor.feedbackStyle", "gentle"),
  );

  useEffect(() => write("tutor.difficulty", difficulty), [difficulty]);
  useEffect(() => write("tutor.feedbackStyle", feedbackStyle), [feedbackStyle]);

  return { difficulty, setDifficulty, feedbackStyle, setFeedbackStyle };
}

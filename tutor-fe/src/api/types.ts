/**
 * Schema contract — mirrors the backend Pydantic schemas.
 *
 * Sources, in the same order as below:
 *   tutor-be/src/conversations/schemas.py
 *   tutor-be/src/memories/schemas.py
 *   tutor-be/src/feedback/schemas.py
 *   tutor-be/src/topics/schemas.py
 *   tutor-be/src/conversations/ws_router.py  (the WS frame protocol)
 *
 * When those change, update this file in the same commit. This comment is
 * load-bearing — it is the only thing keeping the two tiers in step.
 */

// --- conversations -----------------------------------------------------------

export type ConversationStatus = "active" | "archived";

export interface Conversation {
  id: string;
  title: string;
  topic_slug: string | null;
  status: ConversationStatus;
  persona: Persona;
  summary: string | null;
  turn_count: number;
  /** Server setting MAX_TURNS_PER_CONVERSATION. */
  max_turns: number;
  created_at: string;
  last_active_at: string;
}

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  text: string;
  created_at: string;
}

export interface ConversationCreate {
  title?: string | null;
  topic_slug?: string | null;
  persona?: Persona | null;
}

export interface ConversationUpdate {
  title?: string | null;
  status?: ConversationStatus | null;
  persona?: Persona | null;
}

// --- memories ----------------------------------------------------------------

/** Mirrors MEMORY_KINDS in tutor-be/src/memories/models.py. */
export type MemoryKind =
  | "profile"
  | "event"
  | "goal"
  | "preference"
  | "language_issue";

export const MEMORY_KIND_LABELS: Record<MemoryKind, string> = {
  profile: "About them",
  event: "Events",
  goal: "Goals",
  preference: "Preferences",
  language_issue: "Recurring mistakes",
};

export interface Memory {
  id: string;
  kind: MemoryKind;
  content: string;
  status: "active" | "dismissed";
  confidence: number;
  created_at: string;
  last_seen_at: string;
}

export interface MemoryGroup {
  kind: MemoryKind;
  items: Memory[];
}

// --- feedback ----------------------------------------------------------------

/**
 * Mirrors FEEDBACK_TYPES in tutor-be/src/feedback/models.py. No "pronunciation":
 * the server only ever sees a transcript, so it cannot judge how anything
 * sounded. Add it when Azure Speech pronunciation assessment lands.
 */
export type FeedbackType = "grammar" | "vocabulary" | "naturalness";

export type FeedbackSeverity = "minor" | "major";

export interface TurnFeedback {
  id: string;
  message_id: string;
  type: FeedbackType;
  original: string;
  corrected: string;
  explanation: string;
  severity: FeedbackSeverity;
  created_at: string;
}

// --- topics ------------------------------------------------------------------

export interface Topic {
  id: string;
  slug: string;
  title: string;
  level: "beginner" | "intermediate" | "advanced";
  sort_order: number;
}

// --- health ------------------------------------------------------------------

export interface Health {
  status: string;
  /** False means no Azure key: the tutor refuses turns rather than faking them. */
  tutor_configured: boolean;
}

// --- tutoring options --------------------------------------------------------

/** Mirrors PERSONA_PROMPTS in tutor-be/src/agents/prompts/tutor_prompts.py. */
export type Persona =
  | "conversation_partner"
  | "grammar_tutor"
  | "pronunciation_coach"
  | "vocabulary_builder"
  | "fluency_coach";

export const PERSONA_LABELS: Record<Persona, string> = {
  conversation_partner: "Conversation partner",
  grammar_tutor: "Grammar tutor",
  pronunciation_coach: "Pronunciation coach",
  vocabulary_builder: "Vocabulary builder",
  fluency_coach: "Fluency coach",
};

export type Difficulty = "beginner" | "intermediate" | "advanced" | "native";
export type FeedbackStyle = "gentle" | "detailed" | "immediate" | "summary";

// --- WebSocket frames --------------------------------------------------------

export interface UserTurnFrame {
  type: "user_turn";
  text: string;
  difficulty?: Difficulty;
  feedback_style?: FeedbackStyle;
}

export type ServerFrame =
  | { type: "reply_delta"; text: string }
  | {
      type: "reply_done";
      message_id: string;
      user_message_id: string;
      turn_count: number;
      max_turns: number;
    }
  | { type: "turn_limit"; turn_count: number; max_turns: number }
  | { type: "feedback"; message_id: string; items: TurnFeedback[] }
  | { type: "title"; title: string }
  | { type: "error"; detail: string };

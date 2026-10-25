import { AlertTriangle, BrainCircuit, MicOff, NotebookPen, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import type {
  Difficulty,
  FeedbackStyle,
  Health,
  Memory,
  MemoryGroup,
  Message,
  Persona,
  Topic,
  TurnFeedback,
} from "@/api/types";
import { DIFFICULTY_LABELS, FEEDBACK_STYLE_LABELS, PERSONA_LABELS } from "@/api/types";
import ChatPanel from "@/components/ChatPanel";
import ConversationSidebar from "@/components/ConversationSidebar";
import FeedbackPanel from "@/components/FeedbackPanel";
import MemoryPanel from "@/components/MemoryPanel";
import MicButton from "@/components/MicButton";
import TopicPicker from "@/components/TopicPicker";
import { useConversations } from "@/hooks/useConversations";
import { useLearnerSettings } from "@/hooks/useLearnerSettings";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";
import { useTutorSocket } from "@/hooks/useTutorSocket";

const MAX_ACTIVE = 15;
type SidePanel = "memories" | "notes";

export default function TutorPage() {
  const conversationsState = useConversations();
  const { activeId, conversations, patchLocal } = conversationsState;

  const [health, setHealth] = useState<Health | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [memoryGroups, setMemoryGroups] = useState<MemoryGroup[]>([]);
  const [notes, setNotes] = useState<TurnFeedback[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [panel, setPanel] = useState<SidePanel>("memories");
  // Persona lives on the conversation (server-side), so it survives reloads.
  const persona: Persona =
    conversations.find((c) => c.id === activeId)?.persona ?? "conversation_partner";

  const tts = useSpeechSynthesis();
  const learner = useLearnerSettings();
  const levelFrame = useMemo(
    () => ({ difficulty: learner.difficulty, feedback_style: learner.feedbackStyle }),
    [learner.difficulty, learner.feedbackStyle],
  );
  const active = conversations.find((c) => c.id === activeId);
  // Messages fetched for this id, so "no messages" is known rather than "not loaded yet".
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  // --- data loading ----------------------------------------------------------

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.topics.list().then(setTopics).catch(() => setTopics([]));
  }, []);

  const refreshMemories = useCallback(() => {
    api.memories.grouped().then(setMemoryGroups).catch(() => {});
  }, []);

  useEffect(refreshMemories, [refreshMemories]);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      setNotes([]);
      return;
    }
    // A turn in flight belongs to the conversation being left; its reply_done
    // will never arrive here, so `busy` must not carry over and lock the mic.
    setBusy(false);
    setStreaming("");
    setError(null);
    api.conversations
      .messages(activeId)
      .then((rows) => {
        setMessages(rows);
        setLoadedFor(activeId);
      })
      .catch(() => setMessages([]));
    api.conversations.feedback(activeId).then(setNotes).catch(() => setNotes([]));
  }, [activeId]);

  // --- live socket -----------------------------------------------------------

  const socket = useTutorSocket(activeId, {
    onReplyDelta: (text) => {
      setStreaming((prev) => prev + text);
      tts.speakStreaming(text);
    },
    onReplyDone: (_messageId, _userMessageId, turnCount) => {
      if (activeId) patchLocal(activeId, { turn_count: turnCount });
      tts.flush();
      setStreaming("");
      setBusy(false);
      // Re-read rather than appending the local buffer, so ids and timestamps
      // come from the server.
      if (activeId) api.conversations.messages(activeId).then(setMessages).catch(() => {});
    },
    onFeedback: (_messageId, items) => setNotes((prev) => [...prev, ...items]),
    onTitle: (title) => {
      if (activeId) patchLocal(activeId, { title });
    },
    onTurnLimit: (turnCount) => {
      setBusy(false);
      if (activeId) patchLocal(activeId, { turn_count: turnCount });
      // Drop the optimistic bubble: the server refused and stored nothing.
      if (activeId) api.conversations.messages(activeId).then(setMessages).catch(() => {});
    },
    onError: (detail) => {
      setError(detail);
      setBusy(false);
      setStreaming("");
    },
    onDisconnect: () => {
      if (!busy) return;
      tts.cancel();
      setBusy(false);
      setStreaming("");
      setError("Connection lost mid-reply. Reconnecting — please say that again.");
    },
  });

  // Memories are written by the cold pass a few turns in, so poll while a
  // conversation is open rather than only on mount.
  useEffect(() => {
    if (!activeId) return;
    const id = window.setInterval(refreshMemories, 15_000);
    return () => window.clearInterval(id);
  }, [activeId, refreshMemories]);

  // --- speech ----------------------------------------------------------------

  const handleTranscript = useCallback(
    (transcript: string) => {
      if (!activeId) return;
      tts.cancel();
      setError(null);
      const sent = socket.sendTurn({ text: transcript, ...levelFrame });
      if (!sent) {
        setError("Not connected to the tutor. Check the backend is running.");
        return;
      }
      setBusy(true);
      setMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          role: "user",
          text: transcript,
          created_at: new Date().toISOString(),
        },
      ]);
    },
    [activeId, socket, tts, levelFrame],
  );

  const speech = useSpeechRecognition({ onResult: handleTranscript });

  // --- tutor speaks first ----------------------------------------------------

  const isEmpty = loadedFor === activeId && messages.length === 0 && !streaming;
  const askTutorToStart = () => socket.sendStart(levelFrame);

  // A topic conversation opens on its own. A blank one waits, so its empty
  // state (topic picker, "let the tutor start") stays usable. The server
  // ignores `start` once messages exist, so a reconnect cannot greet twice.
  useEffect(() => {
    if (isEmpty && active?.topic_slug && socket.state === "open") askTutorToStart();
    // Not keyed on askTutorToStart: a level change must not re-trigger it.
  }, [isEmpty, active?.topic_slug, socket.state]);

  // --- actions ---------------------------------------------------------------

  const startTopic = async (topic: Topic) => {
    await conversationsState.create({ topic_slug: topic.slug, title: topic.title });
  };

  const dismissMemory = async (id: string) => {
    await api.memories.dismiss(id);
    setMemoryGroups((prev) =>
      prev
        .map((group) => ({ ...group, items: group.items.filter((m: Memory) => m.id !== id) }))
        .filter((group) => group.items.length > 0),
    );
  };

  const memoryCount = useMemo(
    () => memoryGroups.reduce((sum, group) => sum + group.items.length, 0),
    [memoryGroups],
  );

  // The cap counts student turns; the server refuses past it (turn_limit).
  const turnCount = active?.turn_count ?? 0;
  const maxTurns = active?.max_turns ?? 0;
  const turnsLeft = maxTurns - turnCount;
  const limitReached = Boolean(active) && turnsLeft <= 0;

  const micDisabled =
    !activeId || !speech.supported || health?.tutor_configured === false || limitReached;

  // --- render ----------------------------------------------------------------

  return (
    <div className="flex h-full">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        maxActive={MAX_ACTIVE}
        onSelect={conversationsState.setActiveId}
        onCreate={() => conversationsState.create()}
        onRename={conversationsState.rename}
        onDelete={conversationsState.remove}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <Banners
          health={health}
          speechSupported={speech.supported}
          socketClosed={Boolean(activeId) && socket.state === "closed"}
          error={error ?? speech.error}
        />

        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="flex items-center gap-2">
            <select
              value={persona}
              disabled={!activeId}
              onChange={(e) => {
                if (activeId) conversationsState.setPersona(activeId, e.target.value as Persona);
              }}
              className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-700 outline-none focus:border-brand-400"
            >
              {Object.entries(PERSONA_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <select
              value={learner.difficulty}
              onChange={(e) => learner.setDifficulty(e.target.value as Difficulty)}
              title="Your level — applies to every conversation"
              className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-700 outline-none focus:border-brand-400"
            >
              {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <select
              value={learner.feedbackStyle}
              onChange={(e) => learner.setFeedbackStyle(e.target.value as FeedbackStyle)}
              title="How the tutor corrects you — applies to every conversation"
              className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-700 outline-none focus:border-brand-400"
            >
              {Object.entries(FEEDBACK_STYLE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => {
              tts.cancel();
              tts.setMuted(!tts.muted);
            }}
            title={tts.muted ? "Unmute the tutor" : "Mute the tutor"}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100"
          >
            {tts.muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
        </header>

        <ChatPanel
          messages={messages}
          streaming={streaming}
          interim={speech.interim}
          emptyState={
            <div className="flex h-full flex-col items-center justify-center gap-8">
              <div className="text-center">
                <h2 className="text-lg font-semibold text-slate-700">
                  {activeId ? "Press the mic and just talk" : "Start a conversation"}
                </h2>
                <p className="mt-1.5 text-sm text-slate-400">
                  Anything at all — your day, your work, what's on your mind.
                </p>
              </div>
              {activeId && (
                <button
                  type="button"
                  onClick={askTutorToStart}
                  disabled={socket.state !== "open"}
                  className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-brand-700 disabled:bg-slate-300"
                >
                  Let the tutor start
                </button>
              )}
              <TopicPicker topics={topics} onPick={startTopic} />
            </div>
          }
        />

        <footer className="flex flex-col items-center gap-2 border-t border-slate-200 bg-white py-5">
          <MicButton
            listening={speech.listening}
            busy={busy}
            disabled={micDisabled}
            onToggle={speech.toggle}
          />
          {limitReached ? (
            <button
              type="button"
              onClick={() => conversationsState.create()}
              className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-brand-700"
            >
              That's {maxTurns} turns — start a new conversation
            </button>
          ) : (
            active && (
              <p className={`text-xs ${turnsLeft <= 3 ? "text-amber-600" : "text-slate-400"}`}>
                Turn {turnCount} / {maxTurns}
                {turnsLeft <= 3 && ` — ${turnsLeft} left`}
              </p>
            )
          )}
          <p className="h-4 text-xs text-slate-400">
            {busy
              ? "Tutor is replying…"
              : speech.listening
                ? "Listening — speak now"
                : activeId
                  ? "Click to speak"
                  : "Create a conversation to begin"}
          </p>
        </footer>
      </main>

      <aside className="flex h-full w-80 shrink-0 flex-col border-l border-slate-200 bg-slate-50">
        <div className="flex border-b border-slate-200">
          <PanelTab
            active={panel === "memories"}
            onClick={() => setPanel("memories")}
            icon={<BrainCircuit size={15} />}
            label="Memory"
            count={memoryCount}
          />
          <PanelTab
            active={panel === "notes"}
            onClick={() => setPanel("notes")}
            icon={<NotebookPen size={15} />}
            label="Notes"
            count={notes.length}
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          {panel === "memories" ? (
            <MemoryPanel groups={memoryGroups} onDismiss={dismissMemory} />
          ) : (
            <FeedbackPanel items={notes} />
          )}
        </div>
      </aside>
    </div>
  );
}

function PanelTab({
  active,
  onClick,
  icon,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-1 items-center justify-center gap-1.5 py-3 text-sm font-medium transition ${
        active
          ? "border-b-2 border-brand-600 text-brand-700"
          : "text-slate-500 hover:text-slate-800"
      }`}
    >
      {icon}
      {label}
      {count > 0 && (
        <span className="rounded-full bg-slate-200 px-1.5 text-[10px] text-slate-600">
          {count}
        </span>
      )}
    </button>
  );
}

function Banners({
  health,
  speechSupported,
  socketClosed,
  error,
}: {
  health: Health | null;
  speechSupported: boolean;
  socketClosed: boolean;
  error: string | null;
}) {
  return (
    <>
      {health && !health.tutor_configured && (
        <Banner tone="amber" icon={<AlertTriangle size={15} />}>
          No Azure key configured — the tutor will refuse turns rather than fake replies.
          Set <code className="font-mono">AZURE_LLM_*</code> in{" "}
          <code className="font-mono">tutor-be/.env</code>.
        </Banner>
      )}
      {!speechSupported && (
        <Banner tone="amber" icon={<MicOff size={15} />}>
          This browser has no Web Speech API. Use a Chromium-based browser on localhost or
          HTTPS.
        </Banner>
      )}
      {socketClosed && (
        <Banner tone="amber" icon={<AlertTriangle size={15} />}>
          Disconnected from the tutor — reconnecting. Is the backend running on port 8000?
        </Banner>
      )}
      {error && (
        <Banner tone="rose" icon={<AlertTriangle size={15} />}>
          {error}
        </Banner>
      )}
    </>
  );
}

function Banner({
  tone,
  icon,
  children,
}: {
  tone: "amber" | "rose";
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const styles =
    tone === "amber"
      ? "bg-amber-50 text-amber-800 border-amber-200"
      : "bg-rose-50 text-rose-800 border-rose-200";
  return (
    <div className={`flex items-center gap-2 border-b px-6 py-2 text-sm ${styles}`}>
      {icon}
      <span>{children}</span>
    </div>
  );
}

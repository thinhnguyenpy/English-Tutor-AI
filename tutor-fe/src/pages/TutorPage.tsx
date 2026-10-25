import { AlertTriangle, BrainCircuit, MicOff, NotebookPen, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import type {
  Health,
  Memory,
  MemoryGroup,
  Message,
  Persona,
  Topic,
  TurnFeedback,
} from "@/api/types";
import { PERSONA_LABELS } from "@/api/types";
import ChatPanel from "@/components/ChatPanel";
import ConversationSidebar from "@/components/ConversationSidebar";
import FeedbackPanel from "@/components/FeedbackPanel";
import MemoryPanel from "@/components/MemoryPanel";
import MicButton from "@/components/MicButton";
import TopicPicker from "@/components/TopicPicker";
import { useConversations } from "@/hooks/useConversations";
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
    api.conversations.messages(activeId).then(setMessages).catch(() => setMessages([]));
    api.conversations.feedback(activeId).then(setNotes).catch(() => setNotes([]));
  }, [activeId]);

  // --- live socket -----------------------------------------------------------

  const socket = useTutorSocket(activeId, {
    onReplyDelta: (text) => {
      setStreaming((prev) => prev + text);
      tts.speakStreaming(text);
    },
    onReplyDone: () => {
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
    onTurnLimit: (_turnCount, maxTurns) => {
      setBusy(false);
      setError(`This conversation has reached its ${maxTurns}-turn limit. Start a new one.`);
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
      const sent = socket.sendTurn({ text: transcript });
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
    [activeId, socket, tts],
  );

  const speech = useSpeechRecognition({ onResult: handleTranscript });

  // --- actions ---------------------------------------------------------------

  const startTopic = async (topic: Topic) => {
    const conversation = await conversationsState.create(topic.slug);
    await conversationsState.rename(conversation.id, topic.title);
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

  const micDisabled = !activeId || !speech.supported || health?.tutor_configured === false;

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

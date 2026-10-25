import { useCallback, useEffect, useState } from "react";

import { api } from "@/api/client";
import type { Conversation } from "@/api/types";

const LAST_OPEN_KEY = "tutor.lastConversationId";

/**
 * The sidebar list plus which conversation is open.
 *
 * Reopens whatever was last open across reloads — the whole point of the
 * feature is being able to pick a conversation back up at any time.
 */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const rows = await api.conversations.list();
    setConversations(rows);
    return rows;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const rows = await refresh();
        const remembered = localStorage.getItem(LAST_OPEN_KEY);
        const stillThere = rows.some((c) => c.id === remembered);
        setActiveId(stillThere ? remembered : (rows[0]?.id ?? null));
      } finally {
        setLoading(false);
      }
    })();
  }, [refresh]);

  useEffect(() => {
    if (activeId) localStorage.setItem(LAST_OPEN_KEY, activeId);
  }, [activeId]);

  const create = useCallback(
    async (topicSlug?: string) => {
      const conversation = await api.conversations.create(
        topicSlug ? { topic_slug: topicSlug } : {},
      );
      // Creating may have archived the least-recently-active one, so re-read
      // rather than prepending locally.
      await refresh();
      setActiveId(conversation.id);
      return conversation;
    },
    [refresh],
  );

  const rename = useCallback(async (id: string, title: string) => {
    const updated = await api.conversations.update(id, { title });
    setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)));
  }, []);

  const remove = useCallback(
    async (id: string) => {
      await api.conversations.remove(id);
      const rows = await refresh();
      setActiveId((current) => (current === id ? (rows[0]?.id ?? null) : current));
    },
    [refresh],
  );

  /** Patch one row locally — used when the cold path renames a conversation. */
  const patchLocal = useCallback((id: string, patch: Partial<Conversation>) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  }, []);

  return {
    conversations,
    activeId,
    loading,
    setActiveId,
    refresh,
    create,
    rename,
    remove,
    patchLocal,
  };
}

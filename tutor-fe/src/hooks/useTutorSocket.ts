import { useCallback, useEffect, useRef, useState } from "react";

import { liveSocketUrl } from "@/api/client";
import type { ServerFrame, StartFrame, TurnFeedback, UserTurnFrame } from "@/api/types";

export type ConnectionState = "connecting" | "open" | "closed";

export interface TutorSocketHandlers {
  onReplyDelta: (text: string) => void;
  onReplyDone: (messageId: string, userMessageId: string | null) => void;
  onFeedback: (messageId: string, items: TurnFeedback[]) => void;
  onTitle: (title: string) => void;
  onError: (detail: string) => void;
}

/**
 * One WebSocket per open conversation.
 *
 * Handlers live in a ref so the socket is not torn down and rebuilt every time
 * the parent re-renders — reconnecting mid-turn would drop the reply.
 */
export function useTutorSocket(
  conversationId: string | null,
  handlers: TutorSocketHandlers,
) {
  const [state, setState] = useState<ConnectionState>("closed");
  const socketRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!conversationId) {
      setState("closed");
      return;
    }

    const socket = new WebSocket(liveSocketUrl(conversationId));
    socketRef.current = socket;
    setState("connecting");

    socket.onopen = () => setState("open");
    socket.onclose = () => setState("closed");
    socket.onerror = () => setState("closed");

    socket.onmessage = (event) => {
      let frame: ServerFrame;
      try {
        frame = JSON.parse(event.data);
      } catch {
        return;
      }
      const h = handlersRef.current;
      switch (frame.type) {
        case "reply_delta":
          h.onReplyDelta(frame.text);
          break;
        case "reply_done":
          h.onReplyDone(frame.message_id, frame.user_message_id);
          break;
        case "feedback":
          h.onFeedback(frame.message_id, frame.items);
          break;
        case "title":
          h.onTitle(frame.title);
          break;
        case "error":
          h.onError(frame.detail);
          break;
      }
    };

    return () => {
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
      socketRef.current = null;
    };
  }, [conversationId]);

  const send = useCallback((frame: UserTurnFrame | StartFrame) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(frame));
    return true;
  }, []);

  const sendTurn = useCallback(
    (frame: Omit<UserTurnFrame, "type">) => send({ type: "user_turn", ...frame }),
    [send],
  );

  const sendStart = useCallback(
    (frame: Omit<StartFrame, "type"> = {}) => send({ type: "start", ...frame }),
    [send],
  );

  return { state, sendTurn, sendStart };
}

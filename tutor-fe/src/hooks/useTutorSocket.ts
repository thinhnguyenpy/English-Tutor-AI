import { useCallback, useEffect, useRef, useState } from "react";

import { liveSocketUrl } from "@/api/client";
import type { ServerFrame, StartFrame, TurnFeedback, UserTurnFrame } from "@/api/types";

export type ConnectionState = "connecting" | "open" | "closed";

export interface TutorSocketHandlers {
  onReplyDelta: (text: string) => void;
  onReplyDone: (
    messageId: string,
    userMessageId: string | null,
    turnCount: number,
    maxTurns: number,
  ) => void;
  onTurnLimit: (turnCount: number, maxTurns: number) => void;
  onFeedback: (messageId: string, items: TurnFeedback[]) => void;
  onTitle: (title: string) => void;
  onError: (detail: string) => void;
  /** The socket dropped. A turn in flight will never get its reply_done. */
  onDisconnect: () => void;
}

const MAX_RETRY_MS = 10_000;

/**
 * One WebSocket per open conversation.
 *
 * Handlers live in a ref so the socket is not torn down and rebuilt every time
 * the parent re-renders — reconnecting mid-turn would drop the reply.
 *
 * A dropped socket (backend restart, laptop sleep) reconnects on its own with
 * exponential backoff, 1s doubling to 10s, until the conversation changes.
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

    let socket: WebSocket;
    let retryTimer: number | undefined;
    let attempt = 0;

    const connect = () => {
      socket = new WebSocket(liveSocketUrl(conversationId));
      socketRef.current = socket;
      setState("connecting");

      socket.onopen = () => {
        attempt = 0;
        setState("open");
      };
      // Browsers always follow an error with a close, so only close reconnects.
      socket.onclose = () => {
        socketRef.current = null;
        setState("closed");
        handlersRef.current.onDisconnect();
        retryTimer = window.setTimeout(connect, Math.min(1000 * 2 ** attempt, MAX_RETRY_MS));
        attempt += 1;
      };
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
            h.onReplyDone(
              frame.message_id,
              frame.user_message_id,
              frame.turn_count,
              frame.max_turns,
            );
            break;
          case "turn_limit":
            h.onTurnLimit(frame.turn_count, frame.max_turns);
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
    };

    connect();

    return () => {
      window.clearTimeout(retryTimer);
      socket.onmessage = null;
      socket.onclose = null;
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

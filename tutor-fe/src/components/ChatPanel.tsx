import { useEffect, useRef } from "react";

import type { Message } from "@/api/types";
import MessageBubble from "@/components/MessageBubble";

interface Props {
  messages: Message[];
  /** Reply currently streaming in, if any. */
  streaming: string;
  interim: string;
  emptyState: React.ReactNode;
}

export default function ChatPanel({ messages, streaming, interim, emptyState }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streaming, interim]);

  const empty = messages.length === 0 && !streaming && !interim;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      {empty ? (
        emptyState
      ) : (
        // Oldest first, newest at the bottom — the direction a conversation
        // actually runs.
        <div className="mx-auto flex max-w-2xl flex-col gap-5">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              role={message.role}
              text={message.text}
              createdAt={message.created_at}
            />
          ))}

          {interim && <MessageBubble role="user" text={interim} pending />}
          {streaming && <MessageBubble role="assistant" text={streaming} pending />}

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}

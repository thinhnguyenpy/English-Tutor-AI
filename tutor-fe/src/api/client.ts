import type {
  Conversation,
  ConversationCreate,
  ConversationStatus,
  ConversationUpdate,
  Health,
  Memory,
  MemoryGroup,
  Message,
  Topic,
  TurnFeedback,
} from "@/api/types";

const BASE = "/api";

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    // FastAPI puts the message in `detail`; fall back to the status line when
    // the body is not JSON (a proxy error page, say).
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),

  conversations: {
    list: (status: ConversationStatus = "active") =>
      request<Conversation[]>(`/conversations?status=${status}`),

    create: (body: ConversationCreate = {}) =>
      request<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    get: (id: string) => request<Conversation>(`/conversations/${id}`),

    update: (id: string, body: ConversationUpdate) =>
      request<Conversation>(`/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    remove: (id: string) =>
      request<void>(`/conversations/${id}`, { method: "DELETE" }),

    messages: (id: string) => request<Message[]>(`/conversations/${id}/messages`),

    feedback: (id: string) => request<TurnFeedback[]>(`/conversations/${id}/feedback`),
  },

  memories: {
    list: () => request<Memory[]>("/memories"),
    grouped: () => request<MemoryGroup[]>("/memories/grouped"),
    dismiss: (id: string) => request<void>(`/memories/${id}`, { method: "DELETE" }),
  },

  feedback: {
    recent: (limit = 100) => request<TurnFeedback[]>(`/feedback?limit=${limit}`),
  },

  topics: {
    list: () => request<Topic[]>("/topics"),
  },
};

/** WebSocket URL for the live turn. Same origin, so the Vite proxy handles it
 * in dev and there is nothing to configure in production. */
export function liveSocketUrl(conversationId: string): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}${BASE}/conversations/${conversationId}/live`;
}

export { ApiError };

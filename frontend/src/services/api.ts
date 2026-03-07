import type { ChatResponse, MessageHistoryItem } from "../types";

const API_BASE = "/api";

export async function sendChat(
  message: string,
  history: MessageHistoryItem[] = [],
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Chat request failed: ${error}`);
  }

  return response.json() as Promise<ChatResponse>;
}

export async function sendChatStream(
  message: string,
  history: MessageHistoryItem[],
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    const error = await response.text();
    onError(`Stream request failed: ${error}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;

      const payload = trimmed.slice(6);
      if (payload === "[DONE]") {
        onDone();
        return;
      }

      try {
        const data = JSON.parse(payload) as { token?: string; error?: string };
        if (data.error) {
          onError(data.error);
          return;
        }
        if (data.token) {
          onToken(data.token);
        }
      } catch {
        // skip malformed lines
      }
    }
  }

  onDone();
}

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health/`);
  if (!response.ok) throw new Error("Health check failed");
  return response.json() as Promise<{ status: string }>;
}

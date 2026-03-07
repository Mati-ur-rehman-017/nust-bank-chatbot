import { useCallback, useRef, useState } from "react";
import { sendChatStream } from "../services/api";
import type { Message, MessageHistoryItem, Source } from "../types";

const MAX_HISTORY_MESSAGES = 5;

let nextId = 0;
function genId(): string {
  nextId += 1;
  return `msg-${nextId}-${Date.now()}`;
}

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I'm the NUST Bank Assistant. How can I help you today? You can ask me about account services, funds transfer, mobile banking, and more.",
};

/**
 * Extract the last N completed messages as history items for the API.
 * Excludes currently streaming messages and the welcome message.
 */
function getHistoryFromMessages(messages: Message[]): MessageHistoryItem[] {
  return messages
    .filter((m) => !m.isStreaming && m.id !== "welcome")
    .slice(-MAX_HISTORY_MESSAGES)
    .map((m) => ({ role: m.role, content: m.content }));
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(false);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      const userMsg: Message = { id: genId(), role: "user", content: text };
      const botId = genId();
      const botMsg: Message = {
        id: botId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      // Get history before adding the new messages
      const history = getHistoryFromMessages(messages);

      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsStreaming(true);
      abortRef.current = false;

      const sourcesForMsg: Source[] = [];

      try {
        await sendChatStream(
          text,
          history,
          (token) => {
            if (abortRef.current) return;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId ? { ...m, content: m.content + token } : m,
              ),
            );
          },
          () => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? { ...m, isStreaming: false, sources: sourcesForMsg }
                  : m,
              ),
            );
            setIsStreaming(false);
          },
          (error) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? {
                      ...m,
                      content: `Sorry, something went wrong: ${error}`,
                      isStreaming: false,
                    }
                  : m,
              ),
            );
            setIsStreaming(false);
          },
        );
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? {
                  ...m,
                  content:
                    "Sorry, I couldn't connect to the server. Please try again later.",
                  isStreaming: false,
                }
              : m,
          ),
        );
        setIsStreaming(false);
      }
    },
    [isStreaming, messages],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current = true;
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming ? { ...m, isStreaming: false } : m,
      ),
    );
    setIsStreaming(false);
  }, []);

  return { messages, isStreaming, sendMessage, stopStreaming };
}

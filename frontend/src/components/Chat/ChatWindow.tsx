import { useEffect, useRef } from "react";
import type { Message } from "../../types";
import { MessageBubble } from "./MessageBubble";
import { WelcomeScreen } from "./WelcomeScreen";

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
}

export function ChatWindow({ messages, isStreaming }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Filter out the welcome message for display purposes
  const displayMessages = messages.filter((m) => m.id !== "welcome");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  // Show welcome screen if no messages (excluding the system welcome)
  if (displayMessages.length === 0) {
    return <WelcomeScreen />;
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-3xl flex-col py-6 px-4">
        {displayMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isStreaming && !displayMessages.some((m) => m.isStreaming) && (
          <div className="flex gap-4 py-6">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-sm font-bold text-white">
              N
            </div>
            <div className="flex items-center gap-1.5 pt-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-[#8e8ea0] [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-[#8e8ea0] [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-[#8e8ea0] [animation-delay:300ms]" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

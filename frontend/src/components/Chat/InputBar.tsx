import {
  useState,
  useRef,
  useEffect,
  type FormEvent,
  type KeyboardEvent,
  type ChangeEvent,
} from "react";

interface InputBarProps {
  onSend: (message: string) => void;
  disabled: boolean;
  isStreaming: boolean;
  onStop: () => void;
}

// Send arrow icon
function SendIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  );
}

// Stop icon
function StopIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x="6" y="6" width="12" height="12" rx="1" />
    </svg>
  );
}

export function InputBar({ onSend, disabled, isStreaming, onStop }: InputBarProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [input]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
  }

  return (
    <div className="border-t border-[#4e4f60] bg-[#343541] px-4 py-4">
      <div className="mx-auto max-w-3xl">
        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-end rounded-2xl border border-[#565869] bg-[#40414f] shadow-lg transition-colors focus-within:border-[#8e8ea0]">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="Message NUST Bank Assistant..."
              disabled={disabled}
              rows={1}
              className="flex-1 resize-none bg-transparent px-4 py-3.5 text-sm text-[#ececf1] outline-none placeholder:text-[#8e8ea0] disabled:opacity-50"
              style={{ maxHeight: "200px" }}
            />
            
            <div className="flex items-center pr-2 pb-2">
              {isStreaming ? (
                <button
                  type="button"
                  onClick={onStop}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ececf1] text-[#343541] transition-colors hover:bg-white"
                  title="Stop generating"
                >
                  <StopIcon />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={disabled || !input.trim()}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-[#565869] disabled:text-[#8e8ea0]"
                  title="Send message"
                >
                  <SendIcon />
                </button>
              )}
            </div>
          </div>
        </form>
        
        <p className="mt-2 text-center text-xs text-[#8e8ea0]">
          NUST Bank Assistant can make mistakes. Please verify important information.
        </p>
      </div>
    </div>
  );
}

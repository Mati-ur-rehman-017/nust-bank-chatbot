import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Message } from "../../types";

interface MessageBubbleProps {
  message: Message;
}

// User icon SVG
function UserIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
  );
}

// Copy icon SVG
function CopyIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
      />
    </svg>
  );
}

// Check icon SVG
function CheckIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`group flex gap-4 py-6 ${
        isUser ? "bg-transparent" : "bg-[#444654] -mx-4 px-4 rounded-xl"
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
          isUser
            ? "bg-[#5436DA] text-white"
            : "bg-emerald-600 text-white"
        }`}
      >
        {isUser ? <UserIcon /> : "N"}
      </div>

      {/* Message content */}
      <div className="flex-1 min-w-0">
        {/* Role label */}
        <div className="mb-1 text-sm font-semibold text-[#ececf1]">
          {isUser ? "You" : "NUST Bank Assistant"}
        </div>

        {/* Message text */}
        <div className="text-[#ececf1] text-sm leading-relaxed">
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <div className="markdown-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const codeString = String(children).replace(/\n$/, "");
                    
                    // Check if this is an inline code or code block
                    const isInline = !match && !codeString.includes("\n");
                    
                    if (isInline) {
                      return (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }

                    return (
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match ? match[1] : "text"}
                        PreTag="div"
                        customStyle={{
                          margin: 0,
                          borderRadius: "0.5rem",
                          fontSize: "0.875rem",
                        }}
                      >
                        {codeString}
                      </SyntaxHighlighter>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Streaming cursor */}
          {message.isStreaming && (
            <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-[#ececf1]" />
          )}
        </div>

        {/* Sources section */}
        {!isUser &&
          message.sources &&
          message.sources.length > 0 &&
          !message.isStreaming && (
            <div className="mt-4 border-t border-[#4e4f60] pt-3">
              <button
                onClick={() => setShowSources(!showSources)}
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
              >
                {showSources
                  ? "Hide sources"
                  : `View sources (${message.sources.length})`}
              </button>

              {showSources && (
                <ul className="mt-2 space-y-2">
                  {message.sources.map((source) => (
                    <li
                      key={source.doc_id}
                      className="rounded-lg bg-[#2a2b32] p-3 text-xs text-[#c5c5d2]"
                    >
                      <span className="font-medium text-[#ececf1]">
                        {source.doc_id}
                      </span>
                      <span className="ml-2 text-[#8e8ea0]">
                        ({(source.score * 100).toFixed(0)}% match)
                      </span>
                      <p className="mt-1 line-clamp-2">{source.text}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

        {/* Copy button - only for assistant messages */}
        {!isUser && !message.isStreaming && (
          <div className="mt-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-[#8e8ea0] hover:bg-[#2a2b32] hover:text-[#ececf1] transition-colors"
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

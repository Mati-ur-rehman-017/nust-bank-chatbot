import { useState } from "react";
import { Header } from "./components/Layout/Header";
import { Sidebar } from "./components/Layout/Sidebar";
import { ChatWindow } from "./components/Chat/ChatWindow";
import { InputBar } from "./components/Chat/InputBar";
import { UploadForm } from "./components/Documents/UploadForm";
import { DocumentList } from "./components/Documents/DocumentList";
import { useChat } from "./hooks/useChat";
import type { ActiveTab } from "./types";

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const { messages, isStreaming, sendMessage, stopStreaming } = useChat();

  return (
    <div className="flex h-screen flex-col bg-[#343541] text-[#ececf1]">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        <main className="flex flex-1 flex-col overflow-hidden">
          {activeTab === "chat" && (
            <>
              <ChatWindow messages={messages} isStreaming={isStreaming} />
              <InputBar
                onSend={sendMessage}
                disabled={isStreaming}
                isStreaming={isStreaming}
                onStop={stopStreaming}
              />
            </>
          )}

          {activeTab === "documents" && (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="mx-auto max-w-2xl space-y-6">
                <h2 className="text-lg font-semibold text-[#ececf1]">
                  Document Management
                </h2>
                <UploadForm />
                <DocumentList />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

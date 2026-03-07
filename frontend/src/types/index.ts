export interface Source {
  doc_id: string;
  score: number;
  text: string;
}

export interface ChatResponse {
  response: string;
  sources: Source[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
}

export interface MessageHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export interface Document {
  id: string;
  filename: string;
  status: string;
  indexed_at: string;
}

export type ActiveTab = "chat" | "documents";

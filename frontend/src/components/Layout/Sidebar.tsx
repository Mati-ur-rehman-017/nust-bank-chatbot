import type { ActiveTab } from "../../types";

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
}

const tabs: { id: ActiveTab; label: string; icon: string }[] = [
  { id: "chat", label: "Chat", icon: "💬" },
  { id: "documents", label: "Documents", icon: "📄" },
];

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <nav className="flex w-56 flex-col gap-1 border-r border-[#4e4f60] bg-[#202123] p-3">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "bg-[#343541] text-white"
              : "text-[#c5c5d2] hover:bg-[#2a2b32] hover:text-white"
          }`}
        >
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}

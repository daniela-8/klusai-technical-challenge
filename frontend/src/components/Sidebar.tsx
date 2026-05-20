"use client";

import { useState } from "react";
import {
  LayoutDashboard,
  Users,
  Briefcase,
  Building2,
  Trophy,
  FileText,
  Bell,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import clsx from "clsx";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  alertCount: number;
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "competitors", label: "Competitors", icon: Users },
  { id: "jobs", label: "Job Postings", icon: Briefcase },
  { id: "matches", label: "Company Matches", icon: Building2 },
  { id: "priorities", label: "Priority Board", icon: Trophy },
  { id: "briefs", label: "Prospect Briefs", icon: FileText },
  { id: "alerts", label: "Alerts", icon: Bell },
];

export default function Sidebar({
  activeTab,
  onTabChange,
  alertCount,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        "fixed left-0 top-0 h-screen flex flex-col border-r transition-all duration-300 z-50",
        collapsed ? "w-[68px]" : "w-[240px]",
      )}
      style={{
        background: "var(--bg-secondary)",
        borderColor: "var(--border)",
      }}
    >
      {}
      <div
        className="flex items-center gap-3 px-4 h-16 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <img
          src="/klusai.svg"
          width={32}
          height={32}
          alt="Rival Scout"
          className="flex-shrink-0"
          style={{ filter: "brightness(0) invert(1)" }}
        />
        {!collapsed && (
          <div className="animate-fade-in">
            <h1
              className="text-sm font-bold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              Rival Scout
            </h1>
            <p
              className="text-[10px] font-medium"
              style={{ color: "var(--text-secondary)" }}
            >
              Competitor Intelligence
            </p>
          </div>
        )}
      </div>

      {}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={clsx(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                isActive ? "text-white" : "hover:text-white",
              )}
              style={{
                background: isActive
                  ? "linear-gradient(135deg, var(--accent-dim), var(--accent))"
                  : "transparent",
                color: isActive ? "white" : "var(--text-secondary)",
              }}
              onMouseEnter={(e) => {
                if (!isActive)
                  e.currentTarget.style.background = "var(--bg-card-hover)";
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = "transparent";
              }}
            >
              <Icon size={18} className="flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.id === "alerts" && alertCount > 0 && (
                <span
                  className="ml-auto text-xs px-1.5 py-0.5 rounded-full font-semibold"
                  style={{ background: "var(--danger)", color: "white" }}
                >
                  {alertCount}
                </span>
              )}
              {collapsed && item.id === "alerts" && alertCount > 0 && (
                <span
                  className="absolute top-1 right-1 w-2 h-2 rounded-full"
                  style={{ background: "var(--danger)" }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {}
      <div className="p-2 border-t" style={{ borderColor: "var(--border)" }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center py-2 rounded-lg transition-colors"
          style={{ color: "var(--text-secondary)" }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.background = "var(--bg-card-hover)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.background = "transparent")
          }
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  );
}

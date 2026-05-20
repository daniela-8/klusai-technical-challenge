"use client";

import { useEffect, useState } from "react";
import {
  Briefcase,
  Building2,
  Trophy,
  Users,
  TrendingUp,
  Bell,
  BarChart3,
  Loader2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";

const COLORS = [
  "#6366f1",
  "#a855f7",
  "#ec4899",
  "#f59e0b",
  "#22c55e",
  "#3b82f6",
];

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  delay,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  delay: number;
}) {
  return (
    <div
      className="rounded-xl p-5 border transition-all duration-200 animate-fade-in"
      style={{
        background: "var(--bg-card)",
        borderColor: "var(--border)",
        animationDelay: `${delay}ms`,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = color;
        e.currentTarget.style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--border)";
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="p-2 rounded-lg" style={{ background: `${color}20` }}>
          <Icon size={20} style={{ color }} />
        </div>
        <span
          className="text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-secondary)" }}
        >
          {label}
        </span>
      </div>
      <p
        className="text-3xl font-bold"
        style={{ color: "var(--text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

function DarkTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#1c1c28",
        border: "1px solid #3a3a5a",
        borderRadius: "8px",
        padding: "8px 12px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
      }}
    >
      <p
        style={{
          color: "#e8e8f0",
          fontSize: "12px",
          fontWeight: 600,
          marginBottom: "2px",
        }}
      >
        {label}
      </p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: "#a5b4fc", fontSize: "11px" }}>
          {entry.name}: <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

export default function DashboardPage({ refreshKey }: { refreshKey?: number }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .getDashboard()
      .then(setStats)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2
          className="animate-spin"
          size={32}
          style={{ color: "var(--accent)" }}
        />
      </div>
    );
  }

  if (!stats) return null;

  const competitorData = Object.entries(stats.jobs_by_competitor)
    .filter(
      ([name]) =>
        name && name.trim() !== "" && name !== "null" && name !== "undefined",
    )
    .sort(([, a], [, b]) => b - a)
    .map(([name, count]) => ({
      name: name.length > 14 ? name.slice(0, 14) + "…" : name,
      fullName: name,
      jobs: count,
    }));

  const sourceData = Object.entries(stats.jobs_by_source).map(
    ([name, count]) => ({
      name,
      value: count,
    }),
  );

  const confData = Object.entries(stats.confidence_distribution).map(
    ([range, count]) => ({
      name: range,
      count,
    }),
  );

  return (
    <div className="space-y-6">
      <div>
        <h2
          className="text-2xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Dashboard
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Real-time overview of your competitive intelligence pipeline
        </p>
      </div>

      {}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          icon={Briefcase}
          label="Jobs Tracked"
          value={stats.total_jobs}
          color="#6366f1"
          delay={0}
        />
        <StatCard
          icon={Building2}
          label="Companies Inferred"
          value={stats.total_companies_matched}
          color="#a855f7"
          delay={50}
        />
        <StatCard
          icon={Trophy}
          label="High Priority"
          value={stats.high_priority_targets}
          color="#22c55e"
          delay={100}
        />
        <StatCard
          icon={Users}
          label="Competitors"
          value={stats.active_competitors}
          color="#3b82f6"
          delay={150}
        />
        <StatCard
          icon={TrendingUp}
          label="Avg. Confidence"
          value={`${stats.avg_confidence}%`}
          color="#f59e0b"
          delay={200}
        />
        <StatCard
          icon={Bell}
          label="Unread Alerts"
          value={stats.recent_alerts}
          color="#ef4444"
          delay={250}
        />
      </div>

      {}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {}
        <div
          className="rounded-xl p-5 border animate-fade-in"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border)",
            animationDelay: "300ms",
          }}
        >
          <h3
            className="text-sm font-semibold mb-4 flex items-center gap-2"
            style={{ color: "var(--text-primary)" }}
          >
            <BarChart3 size={16} style={{ color: "var(--accent)" }} />
            Postings by Competitor
          </h3>
          {competitorData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={competitorData} barCategoryGap="20%">
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#9898b0", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#9898b0", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<DarkTooltip />} cursor={false} />
                <Bar dataKey="jobs" radius={[6, 6, 0, 0]}>
                  {competitorData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div
              className="flex items-center justify-center h-[250px]"
              style={{ color: "var(--text-secondary)" }}
            >
              <p className="text-sm">Run the pipeline to see data</p>
            </div>
          )}
        </div>

        {}
        <div
          className="rounded-xl p-5 border animate-fade-in"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border)",
            animationDelay: "350ms",
          }}
        >
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Distribution by Source
          </h3>
          <div className="flex items-center gap-8">
            <ResponsiveContainer width="50%" height={200}>
              <PieChart>
                <Pie
                  data={sourceData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  stroke="none"
                >
                  {sourceData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<DarkTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-3">
              {sourceData.map((item, i) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ background: COLORS[i % COLORS.length] }}
                  />
                  <span
                    className="text-sm capitalize"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {item.name}:{" "}
                    <span
                      style={{ color: "var(--text-primary)" }}
                      className="font-semibold"
                    >
                      {item.value}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div
          className="rounded-xl p-5 border animate-fade-in"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border)",
            animationDelay: "400ms",
          }}
        >
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Match Confidence Distribution
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={confData}>
              <XAxis
                dataKey="name"
                tick={{ fill: "#9898b0", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#9898b0", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<DarkTooltip />} cursor={false} />
              <Bar dataKey="count" fill="#6366f1" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div
          className="rounded-xl p-5 border animate-fade-in"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border)",
            animationDelay: "450ms",
          }}
        >
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Top Sectors
          </h3>
          {stats.top_sectors.length > 0 ? (
            <div className="space-y-3">
              {stats.top_sectors.slice(0, 8).map((sector, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className="text-xs font-medium"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {String(sector.name)}
                      </span>
                      <span
                        className="text-xs"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        {sector.count}
                      </span>
                    </div>
                    <div
                      className="h-1.5 rounded-full"
                      style={{ background: "var(--border)" }}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, (sector.count / (stats.top_sectors[0]?.count || 1)) * 100)}%`,
                          background: COLORS[i % COLORS.length],
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              className="flex items-center justify-center h-[200px]"
              style={{ color: "var(--text-secondary)" }}
            >
              <p className="text-sm">Run the pipeline to see sectors</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

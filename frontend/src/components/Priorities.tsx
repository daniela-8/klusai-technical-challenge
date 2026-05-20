"use client";

import { useEffect, useState, useMemo } from "react";
import {
  Trophy,
  Loader2,
  FileText,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Info,
  AlertTriangle,
} from "lucide-react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { api } from "@/lib/api";
import type { PriorityScore } from "@/lib/types";

const SIGNAL_LABELS: Record<string, string> = {
  role_relevance: "Role Relevance",
  hiring_volume: "Hiring Volume",
  seniority: "Seniority Level",
  urgency: "Urgency Signals",
  recent_company_context: "Company Context",
  recency: "Recency",
  dept_hiring_activity: "Dept. Activity",
  company_growth: "Growth Signals",
  reposting: "Reposting",
  competitor_overlap: "Competitor Overlap",
};

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 75
      ? "#22c55e"
      : score >= 50
        ? "#f59e0b"
        : score >= 25
          ? "#3b82f6"
          : "#ef4444";
  return (
    <div className="flex items-center gap-3 w-32">
      <div
        className="flex-1 h-2 rounded-full"
        style={{ background: "var(--border)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span className="text-sm font-bold w-10 text-right" style={{ color }}>
        {score.toFixed(0)}
      </span>
    </div>
  );
}

export default function PrioritiesPage({
  onGenerateBrief,
  refreshKey,
}: {
  onGenerateBrief: (company: string) => void;
  refreshKey?: number;
}) {
  const [priorities, setPriorities] = useState<PriorityScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showUnknown, setShowUnknown] = useState(false);

  useEffect(() => {
    api
      .getPriorities()
      .then(setPriorities)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const { identifiedPriorities, unknownPriorities } = useMemo(() => {
    const identified: PriorityScore[] = [];
    const unknown: PriorityScore[] = [];
    for (const p of priorities) {
      if (p.company_name.toLowerCase().startsWith("unknown")) {
        unknown.push(p);
      } else {
        identified.push(p);
      }
    }
    return { identifiedPriorities: identified, unknownPriorities: unknown };
  }, [priorities]);

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

  const renderPriorityCard = (
    p: PriorityScore,
    i: number,
    isUnknown: boolean = false,
  ) => {
    const radarData = p.scoring_breakdown
      ? Object.entries(p.scoring_breakdown).map(([key, value]) => {
          const score =
            typeof value === "object" && value !== null
              ? (value as { score: number }).score
              : typeof value === "number"
                ? value
                : 0;
          return {
            signal:
              SIGNAL_LABELS[key] ||
              key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
            score,
            fullMark: 100,
          };
        })
      : [];

    const signalDetails = p.scoring_breakdown
      ? Object.entries(p.scoring_breakdown).map(([key, value]) => {
          const score =
            typeof value === "object" && value !== null
              ? (value as { score: number }).score
              : typeof value === "number"
                ? value
                : 0;
          const justification =
            typeof value === "object" && value !== null
              ? (value as { justification?: string }).justification || "—"
              : "—";
          return {
            key,
            label: SIGNAL_LABELS[key] || key.replace(/_/g, " "),
            score,
            justification,
          };
        })
      : [];

    return (
      <div
        key={p.id}
        className="rounded-xl border transition-all duration-200 animate-fade-in"
        style={{
          background: isUnknown ? "rgba(255,255,255,0.02)" : "var(--bg-card)",
          borderColor: isUnknown ? "var(--border)" : "var(--border)",
          animationDelay: `${i * 40}ms`,
          opacity: isUnknown ? 0.7 : 1,
        }}
      >
        <div
          className="p-4 flex items-center gap-4 cursor-pointer"
          onClick={() => setExpanded(expanded === p.id ? null : p.id)}
        >
          {}
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0"
            style={{
              background: isUnknown
                ? "var(--bg-secondary)"
                : i === 0
                  ? "linear-gradient(135deg, #f59e0b, #ef4444)"
                  : i === 1
                    ? "linear-gradient(135deg, #94a3b8, #64748b)"
                    : i === 2
                      ? "linear-gradient(135deg, #b45309, #92400e)"
                      : "var(--bg-secondary)",
              color: !isUnknown && i < 3 ? "white" : "var(--text-secondary)",
            }}
          >
            {isUnknown ? "?" : `#${i + 1}`}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3
                className="font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                {p.company_name}
              </h3>
              <span
                className="text-xs"
                style={{ color: "var(--text-secondary)" }}
              >
                {p.job_count} role{p.job_count !== 1 ? "s" : ""}
              </span>
              {isUnknown && (
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{ background: "#ef444420", color: "#ef4444" }}
                >
                  Unidentified
                </span>
              )}
            </div>
            <p
              className="text-sm mt-1 line-clamp-1"
              style={{ color: "var(--text-secondary)" }}
            >
              {p.rationale}
            </p>
          </div>

          <ScoreBar score={p.priority_score} />

          <button
            onClick={(e) => {
              e.stopPropagation();
              onGenerateBrief(p.company_name);
            }}
            className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1"
            style={{ background: "var(--accent)", color: "white" }}
          >
            <FileText size={12} /> Brief
          </button>

          {expanded === p.id ? (
            <ChevronUp size={18} />
          ) : (
            <ChevronDown size={18} />
          )}
        </div>

        {expanded === p.id && (
          <div
            className="px-4 pb-4 pt-2 border-t animate-fade-in"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {}
              {radarData.length > 0 && (
                <div>
                  <h4
                    className="text-xs font-semibold uppercase mb-2 flex items-center gap-1"
                    style={{ color: "var(--accent)" }}
                  >
                    <BarChart3 size={12} /> Scoring Breakdown
                  </h4>
                  <ResponsiveContainer width="100%" height={420}>
                    <RadarChart
                      data={radarData}
                      cx="50%"
                      cy="52%"
                      outerRadius="70%"
                      margin={{ top: 20, right: 40, bottom: 20, left: 40 }}
                    >
                      <PolarGrid stroke="#2a2a3a" />
                      <PolarAngleAxis
                        dataKey="signal"
                        tick={{ fill: "#9898b0", fontSize: 11 }}
                      />
                      <PolarRadiusAxis
                        tick={false}
                        axisLine={false}
                        domain={[0, 100]}
                      />
                      <Radar
                        name="Score"
                        dataKey="score"
                        stroke="#6366f1"
                        fill="#6366f1"
                        fillOpacity={0.3}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#1a1a2e",
                          border: "1px solid #2a2a3a",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        labelStyle={{ color: "#e0e0f0" }}
                        itemStyle={{ color: "#6366f1" }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="space-y-4">
                {}
                {signalDetails.length > 0 && (
                  <div>
                    <h4
                      className="text-xs font-semibold uppercase mb-2 flex items-center gap-1"
                      style={{ color: "var(--accent)" }}
                    >
                      <Info size={12} /> Signal Justifications
                    </h4>
                    <div className="space-y-1.5">
                      {signalDetails
                        .sort((a, b) => b.score - a.score)
                        .map((signal) => {
                          const scoreColor =
                            signal.score >= 70
                              ? "#22c55e"
                              : signal.score >= 40
                                ? "#f59e0b"
                                : "#ef4444";
                          return (
                            <div
                              key={signal.key}
                              className="rounded-lg p-2 text-xs flex items-start gap-2"
                              style={{ background: "var(--bg-secondary)" }}
                            >
                              <span
                                className="font-bold w-8 text-right flex-shrink-0"
                                style={{ color: scoreColor }}
                              >
                                {signal.score.toFixed(0)}
                              </span>
                              <div className="flex-1 min-w-0">
                                <span
                                  className="font-semibold capitalize"
                                  style={{ color: "var(--text-primary)" }}
                                >
                                  {signal.label}
                                </span>
                                {signal.justification !== "—" && (
                                  <p
                                    className="mt-0.5"
                                    style={{ color: "var(--text-secondary)" }}
                                  >
                                    {signal.justification}
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}

                {}
                <div>
                  <h4
                    className="text-xs font-semibold uppercase mb-2"
                    style={{ color: "var(--accent)" }}
                  >
                    Related Job Postings
                  </h4>
                  <div className="space-y-2">
                    {p.jobs.map((job) => (
                      <div
                        key={job.id}
                        className="rounded-lg p-3 text-xs"
                        style={{ background: "var(--bg-secondary)" }}
                      >
                        <span
                          className="font-semibold"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {job.job_title}
                        </span>
                        <div
                          className="flex gap-3 mt-1"
                          style={{ color: "var(--text-secondary)" }}
                        >
                          <span>{job.competitor_name}</span>
                          {job.location && <span>{job.location}</span>}
                          {job.salary_range && (
                            <span style={{ color: "var(--success)" }}>
                              {job.salary_range}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {}
                <div>
                  <h4
                    className="text-xs font-semibold uppercase mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Rationale
                  </h4>
                  <p
                    className="text-sm"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {p.rationale}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Priority Board
          </h2>
          <p
            className="text-sm mt-1"
            style={{ color: "var(--text-secondary)" }}
          >
            {identifiedPriorities.length} identified companies ranked by
            outreach priority
            {unknownPriorities.length > 0 &&
              ` · ${unknownPriorities.length} unidentified`}
          </p>
        </div>
      </div>

      {}
      <div className="space-y-3">
        {identifiedPriorities.map((p, i) => renderPriorityCard(p, i))}

        {identifiedPriorities.length === 0 && (
          <div
            className="rounded-xl p-12 border text-center"
            style={{
              background: "var(--bg-card)",
              borderColor: "var(--border)",
            }}
          >
            <Trophy
              size={48}
              className="mx-auto mb-4"
              style={{ color: "var(--text-secondary)" }}
            />
            <h3
              className="text-lg font-semibold mb-2"
              style={{ color: "var(--text-primary)" }}
            >
              No priorities yet
            </h3>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Run the pipeline to score and rank companies.
            </p>
          </div>
        )}
      </div>

      {}
      {unknownPriorities.length > 0 && (
        <div>
          <button
            onClick={() => setShowUnknown(!showUnknown)}
            className="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg border transition-all"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
              background: "var(--bg-card)",
            }}
          >
            <AlertTriangle size={14} />
            {showUnknown ? "Hide" : "Show"} {unknownPriorities.length}{" "}
            Unidentified Compan{unknownPriorities.length === 1 ? "y" : "ies"}
            {showUnknown ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showUnknown && (
            <div className="space-y-3 mt-3 animate-fade-in">
              {unknownPriorities.map((p, i) => renderPriorityCard(p, i, true))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

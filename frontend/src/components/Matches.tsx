"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  Target,
  Loader2,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Trophy,
  Globe,
  Users,
  UserCheck,
  Calendar,
  Briefcase,
  AlertCircle,
  MapPin,
  Layers,
  Activity,
  Cpu,
  Newspaper,
  Shield,
  ExternalLink,
  Link,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";
import type { CompanyMatchDetail } from "@/lib/types";

const ALL_SIGNAL_TYPES = [
  "career_page_match",
  "job_description_similarity",
  "location_match",
  "industry_match",
  "seniority_match",
  "hiring_activity",
  "tech_tools_match",
  "public_news",
] as const;

interface EnrichmentData {
  likely_industry?: string;
  company_size_estimate?: string;
  growth_stage?: string;
  role_seniority?: string;
  hiring_urgency?: string;
  technologies_mentioned?: string[];
  salary_competitiveness?: string;
  estimated_applicants?: string;
  linkedin_career_page?: string;
  company_context?: string;
  potential_hiring_contacts?: Array<Record<string, string>>;
  [key: string]: unknown;
}

const SIGNAL_ICONS: Record<string, React.ElementType> = {
  career_page_match: Globe,
  job_description_similarity: Layers,
  location_match: MapPin,
  industry_match: Building2,
  seniority_match: Shield,
  hiring_activity: Activity,
  tech_tools_match: Cpu,
  public_news: Newspaper,
};

const SOURCE_BADGE: Record<
  string,
  { bg: string; color: string; label: string }
> = {
  scraped: { bg: "#22c55e20", color: "#22c55e", label: "Scraped" },
  mocked: { bg: "#f59e0b20", color: "#f59e0b", label: "Mocked" },
  uploaded: { bg: "#6366f120", color: "#6366f1", label: "Uploaded" },
};

const SIGNAL_LABELS: Record<string, string> = {
  career_page_match: "Career Page",
  job_description_similarity: "Description Similarity",
  location_match: "Location",
  industry_match: "Industry",
  seniority_match: "Seniority Level",
  hiring_activity: "Hiring Activity",
  tech_tools_match: "Technologies & Tools",
  public_news: "Public News",
};

function ConfidenceGauge({ score }: { score: number }) {
  const color = score >= 80 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";
  const circumference = 2 * Math.PI * 36;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative w-20 h-20 flex-shrink-0">
      <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
        <circle
          cx="40"
          cy="40"
          r="36"
          stroke="#2a2a3a"
          strokeWidth="6"
          fill="none"
        />
        <circle
          cx="40"
          cy="40"
          r="36"
          stroke={color}
          strokeWidth="6"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold" style={{ color }}>
          {score}%
        </span>
      </div>
    </div>
  );
}

function RenderWithLinks({ text }: { text: string }) {
  if (!text) return null;
  const urlRegex = /(https?:\/\/[^\s|,]+)/g;
  const parts = text.split(urlRegex);
  return (
    <span>
      {parts.map((part, i) =>
        urlRegex.test(part) ? (
          <a
            key={i}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-0.5 hover:underline break-all"
            style={{ color: "var(--accent)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={9} />
            {new URL(part).hostname}
          </a>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  );
}

export default function MatchesPage({ refreshKey }: { refreshKey?: number }) {
  const [matches, setMatches] = useState<CompanyMatchDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getMatches()
      .then(setMatches)
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

  return (
    <div className="space-y-6">
      <div>
        <h2
          className="text-2xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Company Matches
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          Companies identified by AI behind competitor job postings
        </p>
      </div>

      {matches.length === 0 ? (
        <div
          className="rounded-xl p-12 border text-center"
          style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
        >
          <Building2
            size={48}
            className="mx-auto mb-4"
            style={{ color: "var(--text-secondary)" }}
          />
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)" }}
          >
            No matches found
          </h3>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Run the pipeline to identify companies behind competitor job
            postings.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {matches.map((match, i) => {
            const isHighConfidence = match.confidence_score >= 85;
            const isLowConfidence = match.confidence_score < 50;
            const enrichment = (match.enrichment_data || {}) as EnrichmentData;
            const contacts = enrichment.potential_hiring_contacts || [];

            const signalsMap = new Map<
              string,
              { signal_type: string; signal_value: string; inference: string }
            >();
            ALL_SIGNAL_TYPES.forEach((st) =>
              signalsMap.set(st, {
                signal_type: st,
                signal_value: "Not detected",
                inference: "No evidence found for this signal category",
              }),
            );
            if (match.signals_used) {
              for (const s of match.signals_used) {
                if (typeof s === "object" && s.signal_type) {
                  signalsMap.set(s.signal_type, s);
                }
              }
            }
            const allSignals = Array.from(signalsMap.values());

            return (
              <div
                key={match.id}
                className="rounded-xl border transition-all duration-200 animate-fade-in overflow-hidden"
                style={{
                  background: "var(--bg-card)",
                  borderColor:
                    isHighConfidence && expanded === match.id
                      ? "#f59e0b"
                      : "var(--border)",
                  animationDelay: `${i * 30}ms`,
                }}
              >
                <div
                  className="p-4 flex items-center gap-4 cursor-pointer"
                  onClick={() =>
                    setExpanded(expanded === match.id ? null : match.id)
                  }
                  onMouseEnter={(e) =>
                    (e.currentTarget.parentElement!.style.borderColor =
                      "var(--border-bright)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.parentElement!.style.borderColor =
                      isHighConfidence && expanded === match.id
                        ? "#f59e0b"
                        : "var(--border)")
                  }
                >
                  <ConfidenceGauge score={match.confidence_score} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3
                        className="font-semibold"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {match.company_name}
                      </h3>
                      {typeof enrichment.likely_industry === "string" &&
                        enrichment.likely_industry && (
                          <span
                            className="text-xs px-2 py-0.5 rounded-full"
                            style={{
                              background: "#6366f120",
                              color: "#6366f1",
                            }}
                          >
                            {enrichment.likely_industry}
                          </span>
                        )}
                      {isHighConfidence && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-semibold flex items-center gap-1"
                          style={{ background: "#f59e0b20", color: "#f59e0b" }}
                        >
                          <Trophy size={10} /> Match Premium
                        </span>
                      )}
                      {isLowConfidence && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-semibold flex items-center gap-1"
                          style={{ background: "#ef444420", color: "#ef4444" }}
                        >
                          <AlertCircle size={10} /> Low Confidence
                        </span>
                      )}
                    </div>
                    <p
                      className="text-sm mt-1 line-clamp-2"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {match.match_explanation}
                    </p>
                    {match.job && (
                      <div
                        className="flex items-center gap-3 mt-2 text-xs flex-wrap"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        <span>
                          From: <strong>{match.job.competitor_name}</strong>
                        </span>
                        <span>
                          Position: <strong>{match.job.job_title}</strong>
                        </span>
                        {match.job.location && (
                          <span>{match.job.location}</span>
                        )}
                        {(() => {
                          const ds = match.job.data_source;
                          const badge = ds
                            ? SOURCE_BADGE[ds] || SOURCE_BADGE.mocked
                            : null;
                          return badge ? (
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-medium"
                              style={{
                                background: badge.bg,
                                color: badge.color,
                              }}
                            >
                              {badge.label}
                            </span>
                          ) : null;
                        })()}
                      </div>
                    )}
                  </div>

                  {expanded === match.id ? (
                    <ChevronUp size={20} />
                  ) : (
                    <ChevronDown size={20} />
                  )}
                </div>

                {}
                {expanded === match.id && (
                  <div
                    className="px-4 pb-4 pt-2 border-t animate-fade-in space-y-4"
                    style={{ borderColor: "var(--border)" }}
                  >
                    {}
                    {match.additional_data_needed && (
                      <div
                        className="rounded-lg p-3 text-xs"
                        style={{
                          background: "#ef444410",
                          border: "1px solid #ef444430",
                        }}
                      >
                        <span
                          className="flex items-center gap-1.5 font-bold uppercase tracking-wider mb-1"
                          style={{ color: "#ef4444" }}
                        >
                          <AlertCircle size={12} /> Additional Data Needed
                        </span>
                        <p style={{ color: "var(--text-secondary)" }}>
                          {match.additional_data_needed}
                        </p>
                      </div>
                    )}

                    {}
                    {isHighConfidence && (
                      <div
                        className="rounded-lg p-4 space-y-3"
                        style={{
                          background:
                            "linear-gradient(135deg, #f59e0b08, #f59e0b15)",
                          border: "1px solid #f59e0b30",
                        }}
                      >
                        <h4
                          className="text-xs font-bold uppercase flex items-center gap-1.5 tracking-wider"
                          style={{ color: "#f59e0b" }}
                        >
                          <Trophy size={13} /> Premium Intelligence — High
                          Confidence Match
                        </h4>

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {}
                          <div
                            className="rounded-lg p-2.5 text-xs"
                            style={{ background: "var(--bg-secondary)" }}
                          >
                            <span
                              className="flex items-center gap-1 font-semibold"
                              style={{ color: "var(--text-secondary)" }}
                            >
                              Salary
                            </span>
                            <p
                              className="font-medium mt-0.5"
                              style={{
                                color: match.job?.salary_range
                                  ? "#22c55e"
                                  : "var(--text-secondary)",
                              }}
                            >
                              {match.job?.salary_range || "Salary unavailable"}
                            </p>
                          </div>

                          {}
                          {match.job?.posting_date && (
                            <div
                              className="rounded-lg p-2.5 text-xs"
                              style={{ background: "var(--bg-secondary)" }}
                            >
                              <span
                                className="flex items-center gap-1 font-semibold"
                                style={{ color: "var(--text-secondary)" }}
                              >
                                <Calendar size={11} /> Publication Date
                              </span>
                              <p
                                className="font-medium mt-0.5"
                                style={{ color: "var(--text-primary)" }}
                              >
                                {(() => {
                                  try {
                                    return new Date(
                                      match.job.posting_date,
                                    ).toLocaleDateString("en-GB", {
                                      day: "numeric",
                                      month: "short",
                                      year: "numeric",
                                    });
                                  } catch {
                                    return match.job.posting_date;
                                  }
                                })()}
                              </p>
                            </div>
                          )}

                          {}
                          {enrichment.estimated_applicants &&
                            String(enrichment.estimated_applicants) !==
                              "Unknown" &&
                            String(enrichment.estimated_applicants) !==
                              "Non disponible" && (
                              <div
                                className="rounded-lg p-2.5 text-xs"
                                style={{ background: "var(--bg-secondary)" }}
                              >
                                <span
                                  className="flex items-center gap-1 font-semibold"
                                  style={{ color: "var(--text-secondary)" }}
                                >
                                  <Users size={11} /> Estimated Applicants
                                </span>
                                <p
                                  className="font-medium mt-0.5"
                                  style={{ color: "var(--text-primary)" }}
                                >
                                  {String(enrichment.estimated_applicants)}
                                </p>
                              </div>
                            )}

                          {}
                          {enrichment.linkedin_career_page &&
                            String(enrichment.linkedin_career_page) !==
                              "Unknown" &&
                            String(enrichment.linkedin_career_page) !==
                              "Non vérifié" && (
                              <div
                                className="rounded-lg p-2.5 text-xs"
                                style={{ background: "var(--bg-secondary)" }}
                              >
                                <span
                                  className="flex items-center gap-1 font-semibold"
                                  style={{ color: "var(--text-secondary)" }}
                                >
                                  <Globe size={11} /> Company Page
                                </span>
                                <div className="font-medium mt-0.5">
                                  {String(
                                    enrichment.linkedin_career_page,
                                  ).startsWith("http") ? (
                                    <a
                                      href={String(
                                        enrichment.linkedin_career_page,
                                      )}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 hover:underline"
                                      style={{ color: "var(--accent)" }}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink size={10} />{" "}
                                      {(() => {
                                        try {
                                          const u = new URL(
                                            String(
                                              enrichment.linkedin_career_page,
                                            ),
                                          );
                                          return (
                                            u.hostname + u.pathname.slice(0, 30)
                                          );
                                        } catch {
                                          return "View page";
                                        }
                                      })()}
                                    </a>
                                  ) : String(
                                      enrichment.linkedin_career_page,
                                    ) === "Not verified" ? (
                                    <span
                                      style={{ color: "var(--text-secondary)" }}
                                    >
                                      Not yet verified
                                    </span>
                                  ) : (
                                    <RenderWithLinks
                                      text={String(
                                        enrichment.linkedin_career_page,
                                      )}
                                    />
                                  )}
                                </div>
                              </div>
                            )}

                          {}
                          {enrichment.salary_competitiveness &&
                            String(enrichment.salary_competitiveness) !==
                              "Market rate" && (
                              <div
                                className="rounded-lg p-2.5 text-xs"
                                style={{ background: "var(--bg-secondary)" }}
                              >
                                <span
                                  className="flex items-center gap-1 font-semibold"
                                  style={{ color: "var(--text-secondary)" }}
                                >
                                  <TrendingUp size={11} /> Salary
                                  Competitiveness
                                </span>
                                <p
                                  className="font-medium mt-0.5"
                                  style={{ color: "var(--text-primary)" }}
                                >
                                  {String(enrichment.salary_competitiveness)}
                                </p>
                              </div>
                            )}

                          {}
                          {enrichment.company_context &&
                            String(enrichment.company_context) !==
                              "No specific company events detected in job description" &&
                            String(enrichment.company_context) !==
                              "Aucun événement spécifique détecté dans la description de poste" && (
                              <div
                                className="rounded-lg p-2.5 text-xs col-span-2"
                                style={{ background: "var(--bg-secondary)" }}
                              >
                                <span
                                  className="flex items-center gap-1 font-semibold"
                                  style={{ color: "var(--text-secondary)" }}
                                >
                                  <Briefcase size={11} /> Company Context
                                </span>
                                <p
                                  className="font-medium mt-0.5"
                                  style={{ color: "var(--text-primary)" }}
                                >
                                  {String(enrichment.company_context)}
                                </p>
                              </div>
                            )}
                        </div>

                        {}
                        {contacts.length > 0 && (
                          <div>
                            <span
                              className="flex items-center gap-1 text-xs font-semibold mb-1.5"
                              style={{ color: "var(--text-secondary)" }}
                            >
                              <UserCheck size={11} /> Potential Hiring Contacts
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {contacts.map(
                                (
                                  contact: Record<string, string>,
                                  ci: number,
                                ) => (
                                  <div
                                    key={ci}
                                    className="rounded-lg p-2.5 text-xs"
                                    style={{
                                      background: "var(--bg-secondary)",
                                    }}
                                  >
                                    <span
                                      className="font-semibold"
                                      style={{ color: "#f59e0b" }}
                                    >
                                      {contact.title}
                                    </span>
                                    <p
                                      style={{ color: "var(--text-secondary)" }}
                                    >
                                      {contact.reasoning}
                                    </p>
                                    {contact.contact_info && (
                                      <div
                                        className="mt-1 text-xs"
                                        style={{ color: "var(--accent)" }}
                                      >
                                        <RenderWithLinks
                                          text={contact.contact_info}
                                        />
                                      </div>
                                    )}
                                  </div>
                                ),
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {}
                    <div>
                      <h4
                        className="text-xs font-semibold uppercase mb-2 flex items-center gap-1"
                        style={{ color: "var(--accent)" }}
                      >
                        <Target size={12} /> Matching Signals (
                        {
                          allSignals.filter(
                            (s) => s.signal_value !== "Not detected",
                          ).length
                        }
                        /8 detected)
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {allSignals.map((signal, si) => {
                          const SignalIcon =
                            SIGNAL_ICONS[signal.signal_type] || Target;
                          const signalLabel =
                            SIGNAL_LABELS[signal.signal_type] ||
                            signal.signal_type?.replace(/_/g, " ");
                          const isDetected =
                            signal.signal_value !== "Not detected";

                          return (
                            <div
                              key={si}
                              className="rounded-lg p-2.5 text-xs flex items-start gap-2 transition-all"
                              style={{
                                background: isDetected
                                  ? "var(--bg-secondary)"
                                  : "rgba(255,255,255,0.02)",
                                opacity: isDetected ? 1 : 0.6,
                                border: isDetected
                                  ? "none"
                                  : "1px dashed var(--border)",
                              }}
                            >
                              <div
                                className="p-1 rounded"
                                style={{
                                  background: isDetected
                                    ? "rgba(99,102,241,0.15)"
                                    : "rgba(99,102,241,0.05)",
                                }}
                              >
                                <SignalIcon
                                  size={12}
                                  style={{
                                    color: isDetected
                                      ? "var(--accent)"
                                      : "var(--text-secondary)",
                                  }}
                                />
                              </div>
                              <div className="flex-1 min-w-0">
                                <span
                                  className="font-semibold capitalize block"
                                  style={{
                                    color: isDetected
                                      ? "var(--text-primary)"
                                      : "var(--text-secondary)",
                                  }}
                                >
                                  {signalLabel}
                                </span>
                                {isDetected && signal.signal_value && (
                                  <span
                                    className="text-xs block"
                                    style={{ color: "var(--accent)" }}
                                  >
                                    <RenderWithLinks
                                      text={signal.signal_value}
                                    />
                                  </span>
                                )}
                                <p style={{ color: "var(--text-secondary)" }}>
                                  {signal.inference}
                                </p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {}
                    {match.enrichment_data && (
                      <div>
                        <h4
                          className="text-xs font-semibold uppercase mb-2 flex items-center gap-1"
                          style={{ color: "var(--accent)" }}
                        >
                          <Lightbulb size={12} /> Enrichment Data
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {Object.entries(match.enrichment_data)
                            .filter(
                              ([k, v]) =>
                                v &&
                                typeof v !== "object" &&
                                ![
                                  "estimated_applicants",
                                  "linkedin_career_page",
                                  "company_context",
                                  "potential_hiring_contacts",
                                ].includes(k),
                            )
                            .map(([key, value]) => (
                              <div
                                key={key}
                                className="rounded-lg p-2 text-xs"
                                style={{ background: "var(--bg-secondary)" }}
                              >
                                <span
                                  className="capitalize"
                                  style={{ color: "var(--text-secondary)" }}
                                >
                                  {key.replace(/_/g, " ")}
                                </span>
                                <p
                                  className="font-medium"
                                  style={{ color: "var(--text-primary)" }}
                                >
                                  {String(value)}
                                </p>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {}
                    {match.job?.job_url && (
                      <a
                        href={match.job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs hover:underline"
                        style={{ color: "var(--accent)" }}
                      >
                        <ExternalLink size={12} /> View original posting on{" "}
                        {match.job.competitor_name}
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

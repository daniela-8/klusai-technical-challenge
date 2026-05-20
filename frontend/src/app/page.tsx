"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  Loader2,
  Zap,
  ChevronRight,
  CheckCircle2,
  Search,
  Cpu,
  RotateCcw,
  X,
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import DashboardPage from "@/components/Dashboard";
import CompetitorsPage from "@/components/Competitors";
import JobsPage from "@/components/Jobs";
import MatchesPage from "@/components/Matches";
import PrioritiesPage from "@/components/Priorities";
import BriefsPage from "@/components/Briefs";
import AlertsPage from "@/components/Alerts";
import { api } from "@/lib/api";
import type { Competitor } from "@/lib/types";

type PipelineStep = "idle" | "scrape" | "review" | "analyze" | "done";

const STEP_META: Record<
  PipelineStep,
  { label: string; icon: React.ElementType; num: number }
> = {
  idle: { label: "Ready", icon: Zap, num: 0 },
  scrape: { label: "Scraping", icon: Search, num: 1 },
  review: { label: "Review Jobs", icon: CheckCircle2, num: 2 },
  analyze: { label: "AI Analysis", icon: Cpu, num: 3 },
  done: { label: "Complete", icon: CheckCircle2, num: 4 },
};

const TOAST_STYLES: Record<
  string,
  { bg: string; border: string; color: string }
> = {
  success: { bg: "#22c55e12", border: "#22c55e40", color: "#22c55e" },
  info: {
    bg: "var(--bg-card)",
    border: "var(--border)",
    color: "var(--text-primary)",
  },
  error: { bg: "#ef444412", border: "#ef444440", color: "#ef4444" },
};

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [alertCount, setAlertCount] = useState(0);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>("idle");
  const [pipelineStatus, setPipelineStatus] = useState("");
  const [briefGenerating, setBriefGenerating] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [resetting, setResetting] = useState(false);

  // Toast notifications
  const [toasts, setToasts] = useState<
    { id: number; message: string; type: string }[]
  >([]);
  const toastIdRef = useRef(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addToast = useCallback(
    (message: string, type: "success" | "info" | "error" = "info") => {
      const id = ++toastIdRef.current;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(
        () => setToasts((prev) => prev.filter((t) => t.id !== id)),
        5000,
      );
    },
    [],
  );

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [selectedCompetitorIds, setSelectedCompetitorIds] = useState<
    Set<string>
  >(new Set());
  const [showScrapePanel, setShowScrapePanel] = useState(false);

  const refreshAlertCount = useCallback(async () => {
    try {
      const alerts = await api.getAlerts(true);
      setAlertCount(alerts.length);
    } catch {}
  }, []);

  useEffect(() => {
    api
      .getCompetitors()
      .then((comps) => {
        setCompetitors(comps.filter((c) => c.is_active));
        setSelectedCompetitorIds(
          new Set(comps.filter((c) => c.is_active).map((c) => c.id)),
        );
      })
      .catch(() => {});
    refreshAlertCount();
  }, [refreshKey, refreshAlertCount]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const toggleCompetitor = (id: string) => {
    setSelectedCompetitorIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllCompetitors = () => {
    setSelectedCompetitorIds(new Set(competitors.map((c) => c.id)));
  };
  const deselectAllCompetitors = () => {
    setSelectedCompetitorIds(new Set());
  };

  const startPolling = useCallback(
    (initialMatchCount: number) => {
      if (pollRef.current) clearInterval(pollRef.current);
      let elapsed = 0;
      let lastKnownMatchCount = initialMatchCount;

      pollRef.current = setInterval(async () => {
        elapsed += 6;
        try {
          const status = await api.getPipelineStatus();
          const matchData = await api.getMatchCount();

          const totalNewMatches = matchData.match_count - initialMatchCount;
          const justFoundNew = matchData.match_count > lastKnownMatchCount;

          if (justFoundNew) {
            const delta = matchData.match_count - lastKnownMatchCount;
            lastKnownMatchCount = matchData.match_count;
            setRefreshKey((k) => k + 1);
            addToast(
              `\u2713 New company match found (${totalNewMatches} total)`,
              "success",
            );
          }

          if (totalNewMatches > 0) {
            setPipelineStatus(
              `AI analysis in progress \u2014 ${totalNewMatches} match${totalNewMatches > 1 ? "es" : ""} found so far...`,
            );
          } else {
            setPipelineStatus(
              `AI analysis in progress... (${elapsed}s elapsed)`,
            );
          }

          if (!status.is_running && status.last_result) {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;

            const r = status.last_result as Record<string, unknown>;
            const processed = r.jobs_processed ?? 0;
            const matched = r.matches_created ?? 0;
            const scored = r.scores_updated ?? 0;
            const errors = (r.errors as string[]) || [];

            setRefreshKey((k) => k + 1);
            refreshAlertCount();

            if (errors.length > 0 && Number(processed) === 0) {
              const isQuota = errors.some(
                (e: string) => e.includes("quota") || e.includes("429"),
              );
              if (isQuota) {
                setPipelineStatus(
                  "API quota exhausted. Replace GEMINI_API_KEY in backend/.env and restart.",
                );
              } else {
                setPipelineStatus(
                  `Processing error: ${errors[0]?.slice(0, 120)}`,
                );
              }
              setPipelineStep("idle");
            } else {
              setPipelineStatus(
                `${processed} processed, ${matched} matched, ${scored} scored \u2014 complete`,
              );
              setPipelineStep("done");
              addToast(
                `Pipeline complete: ${matched} company match${Number(matched) !== 1 ? "es" : ""} identified`,
                "success",
              );
              setTimeout(() => {
                setPipelineStep("idle");
                setPipelineStatus("");
              }, 6000);
            }
          }
        } catch {
          // Polling error — keep trying
        }

        // Safety: stop polling after 10 minutes (LLM rate limiting can be slow)
        if (elapsed >= 600) {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setRefreshKey((k) => k + 1);
          setPipelineStatus(
            "Analysis timed out. Check Matches tab for partial results.",
          );
          setPipelineStep("idle");
          addToast(
            "Analysis timed out — check Matches tab for results so far",
            "info",
          );
        }
      }, 6000);
    },
    [refreshAlertCount, addToast],
  );

  const handleScrape = async () => {
    if (selectedCompetitorIds.size === 0) return;
    setPipelineStep("scrape");
    setPipelineStatus("Scraping selected competitors...");
    setShowScrapePanel(false);
    try {
      const scrapeResult = await api.triggerScrape(
        Array.from(selectedCompetitorIds),
      );
      if (scrapeResult.status === "error") {
        setPipelineStatus(`Scraping error: ${scrapeResult.errors.join(", ")}`);
        setPipelineStep("idle");
        return;
      }
      setPipelineStatus(
        `${scrapeResult.jobs_collected} jobs collected from ${scrapeResult.competitors_scraped} competitor(s). Select jobs to analyze.`,
      );
      setPipelineStep("review");
      setRefreshKey((k) => k + 1);
      addToast(
        `Scraping complete: ${scrapeResult.jobs_collected} jobs collected`,
        "success",
      );
      setActiveTab("jobs");
    } catch (e) {
      setPipelineStatus(`Error: ${String(e)}`);
      setPipelineStep("idle");
    }
  };

  const handleAnalyzeJobs = useCallback(
    async (jobIds: string[]) => {
      if (jobIds.length === 0) return;
      setPipelineStep("analyze");
      setPipelineStatus(`Starting AI analysis on ${jobIds.length} job(s)...`);
      try {
        const { match_count: initialMatchCount } = await api.getMatchCount();
        const processResult = await api.triggerProcess(jobIds);

        if (processResult.status === "error") {
          const errMsg = processResult.errors[0] || "Unknown error";
          const isQuota = errMsg.includes("quota") || errMsg.includes("429");
          setPipelineStatus(
            isQuota
              ? "Gemini API quota exhausted. Replace GEMINI_API_KEY in backend/.env and restart."
              : `Processing error: ${errMsg.slice(0, 120)}`,
          );
          setPipelineStep("idle");
          return;
        }

        if (processResult.status === "accepted") {
          setPipelineStatus("AI analysis running in background...");
          startPolling(initialMatchCount);
          return;
        }

        const remaining = processResult.jobs_remaining ?? 0;
        const doneMsg = `${processResult.jobs_processed} processed, ${processResult.matches_created} matched, ${processResult.scores_updated} scored`;
        const remainMsg =
          remaining > 0 ? ` \u2014 ${remaining} remaining` : " \u2014 complete";
        setPipelineStatus(doneMsg + remainMsg);
        setPipelineStep("done");
        setRefreshKey((k) => k + 1);
        await refreshAlertCount();
        addToast(
          `Analysis complete: ${processResult.matches_created} matches found`,
          "success",
        );
        setTimeout(() => {
          setPipelineStep("idle");
          setPipelineStatus("");
        }, 6000);
      } catch (e) {
        const msg = String(e);
        setPipelineStatus(
          msg.includes("quota") || msg.includes("429")
            ? "API quota exhausted. Replace GEMINI_API_KEY and restart."
            : `Error: ${msg}`,
        );
        setPipelineStep("idle");
      }
    },
    [refreshAlertCount, startPolling, addToast],
  );

  const handleGenerateBrief = useCallback(
    async (companyName: string) => {
      setBriefGenerating(true);
      try {
        await api.generateBrief(companyName);
        setActiveTab("briefs");
        setRefreshKey((k) => k + 1);
        addToast(`Brief generated for ${companyName}`, "success");
      } catch (e) {
        addToast(`Brief generation failed: ${e}`, "error");
      } finally {
        setBriefGenerating(false);
      }
    },
    [addToast],
  );

  const handleReset = useCallback(async () => {
    if (
      !window.confirm(
        "Reset all data?\n\nThis will permanently delete all job postings, company matches, priority scores, briefs, and alerts.\n\nCompetitors will be preserved.\n\nClick OK to confirm.",
      )
    )
      return;
    setResetting(true);
    setPipelineStatus("Resetting all data...");
    try {
      const result = await api.resetAllData();
      if (result.status === "ok") {
        setPipelineStatus("All data cleared. Ready to scrape fresh.");
        setRefreshKey((k) => k + 1);
        setAlertCount(0);
        setPipelineStep("idle");
        addToast("All data has been reset", "info");
        setTimeout(() => setPipelineStatus(""), 4000);
      } else {
        setPipelineStatus(`Reset failed: ${result.message}`);
      }
    } catch (e) {
      setPipelineStatus(`Reset error: ${String(e)}`);
    } finally {
      setResetting(false);
    }
  }, [addToast]);

  const renderPage = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardPage refreshKey={refreshKey} />;
      case "competitors":
        return <CompetitorsPage refreshKey={refreshKey} />;
      case "jobs":
        return (
          <JobsPage
            refreshKey={refreshKey}
            pipelineStep={pipelineStep}
            onAnalyzeJobs={handleAnalyzeJobs}
          />
        );
      case "matches":
        return <MatchesPage refreshKey={refreshKey} />;
      case "priorities":
        return (
          <PrioritiesPage
            onGenerateBrief={handleGenerateBrief}
            refreshKey={refreshKey}
          />
        );
      case "briefs":
        return <BriefsPage refreshKey={refreshKey} />;
      case "alerts":
        return (
          <AlertsPage onCountChange={setAlertCount} refreshKey={refreshKey} />
        );
      default:
        return <DashboardPage refreshKey={refreshKey} />;
    }
  };

  const activeStepNum = STEP_META[pipelineStep].num;

  return (
    <div
      className="flex min-h-screen"
      style={{ background: "var(--bg-primary)" }}
    >
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        alertCount={alertCount}
      />

      <main className="flex-1 ml-[240px] transition-all duration-300">
        {}
        <header
          className="sticky top-0 z-40 h-16 flex items-center justify-between px-6 border-b backdrop-blur-lg"
          style={{
            background: "rgba(10, 10, 15, 0.8)",
            borderColor: "var(--border)",
          }}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {}
            {pipelineStep !== "idle" && (
              <div className="flex items-center gap-1 text-xs animate-fade-in">
                {(
                  ["scrape", "review", "analyze", "done"] as PipelineStep[]
                ).map((step, i) => {
                  const meta = STEP_META[step];
                  const isActive = meta.num === activeStepNum;
                  const isDone = meta.num < activeStepNum;
                  const Icon = meta.icon;
                  return (
                    <div key={step} className="flex items-center gap-1">
                      {i > 0 && (
                        <ChevronRight
                          size={10}
                          style={{ color: "var(--text-secondary)" }}
                        />
                      )}
                      <span
                        className="flex items-center gap-1 px-2 py-1 rounded-md font-medium transition-all"
                        style={{
                          background: isActive
                            ? "var(--accent)"
                            : isDone
                              ? "#22c55e20"
                              : "var(--bg-card)",
                          color: isActive
                            ? "white"
                            : isDone
                              ? "#22c55e"
                              : "var(--text-secondary)",
                        }}
                      >
                        <Icon size={11} />
                        {meta.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {pipelineStatus && (
              <span
                className="text-xs px-3 py-1.5 rounded-lg animate-fade-in truncate max-w-[500px]"
                style={{
                  background: "var(--bg-card)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border)",
                }}
              >
                {pipelineStep === "analyze" && (
                  <Loader2 size={10} className="inline animate-spin mr-1.5" />
                )}
                {pipelineStatus}
              </span>
            )}
            {briefGenerating && (
              <span
                className="text-xs px-3 py-1.5 rounded-lg animate-fade-in flex items-center gap-2"
                style={{
                  background: "var(--bg-card)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent)",
                }}
              >
                <Loader2 size={12} className="animate-spin" /> Generating
                brief...
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {}
            <button
              onClick={handleReset}
              disabled={
                resetting ||
                pipelineStep === "scrape" ||
                pipelineStep === "analyze"
              }
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-all disabled:opacity-40"
              style={{
                borderColor: "#ef444440",
                color: "#ef4444",
                background: "#ef444410",
              }}
              onMouseEnter={(e) => {
                if (!resetting) e.currentTarget.style.background = "#ef444420";
              }}
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "#ef444410")
              }
              title="Clear all jobs, matches, scores, and alerts for a fresh start"
            >
              {resetting ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Resetting...
                </>
              ) : (
                <>
                  <RotateCcw size={14} /> Reset Data
                </>
              )}
            </button>
            <div className="relative">
              <button
                onClick={() => setShowScrapePanel(!showScrapePanel)}
                disabled={
                  pipelineStep === "scrape" || pipelineStep === "analyze"
                }
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all disabled:opacity-50"
                style={{
                  background:
                    "linear-gradient(135deg, var(--accent-dim), var(--accent))",
                }}
                onMouseEnter={(e) => {
                  if (pipelineStep !== "scrape" && pipelineStep !== "analyze")
                    e.currentTarget.style.transform = "translateY(-1px)";
                }}
                onMouseLeave={(e) =>
                  (e.currentTarget.style.transform = "translateY(0)")
                }
              >
                {pipelineStep === "scrape" ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Scraping...
                  </>
                ) : pipelineStep === "analyze" ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Analyzing...
                  </>
                ) : (
                  <>
                    <Zap size={16} /> Run Pipeline
                  </>
                )}
              </button>

              {}
              {showScrapePanel && (
                <div
                  className="absolute right-0 top-full mt-2 w-80 rounded-xl border shadow-2xl animate-fade-in z-50"
                  style={{
                    background: "var(--bg-card)",
                    borderColor: "var(--border)",
                  }}
                >
                  <div className="p-4">
                    <h4
                      className="text-sm font-bold mb-1"
                      style={{ color: "var(--text-primary)" }}
                    >
                      Step 1: Select Competitors to Scrape
                    </h4>
                    <p
                      className="text-xs mb-3"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      Choose which competitors to scrape for new job postings.
                    </p>

                    <div className="flex gap-2 mb-3">
                      <button
                        onClick={
                          selectedCompetitorIds.size === competitors.length
                            ? deselectAllCompetitors
                            : selectAllCompetitors
                        }
                        className="text-xs px-3 py-1.5 rounded border"
                        style={{
                          borderColor: "var(--border)",
                          color:
                            selectedCompetitorIds.size === competitors.length
                              ? "var(--text-secondary)"
                              : "var(--accent)",
                        }}
                      >
                        {selectedCompetitorIds.size === competitors.length
                          ? "Deselect All"
                          : "Select All"}
                      </button>
                    </div>

                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {competitors.map((comp) => (
                        <label
                          key={comp.id}
                          className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all"
                          style={{
                            background: selectedCompetitorIds.has(comp.id)
                              ? "var(--bg-secondary)"
                              : "transparent",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selectedCompetitorIds.has(comp.id)}
                            onChange={() => toggleCompetitor(comp.id)}
                            className="rounded accent-[var(--accent)]"
                          />
                          <div className="flex-1 min-w-0">
                            <span
                              className="text-sm font-medium block"
                              style={{ color: "var(--text-primary)" }}
                            >
                              {comp.name}
                            </span>
                            <span
                              className="text-xs"
                              style={{ color: "var(--text-secondary)" }}
                            >
                              {comp.job_count} jobs tracked
                            </span>
                          </div>
                        </label>
                      ))}
                    </div>

                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => setShowScrapePanel(false)}
                        className="flex-1 py-2 rounded-lg text-sm font-medium border"
                        style={{
                          borderColor: "var(--border)",
                          color: "var(--text-secondary)",
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleScrape}
                        disabled={selectedCompetitorIds.size === 0}
                        className="flex-1 py-2 rounded-lg text-xs font-semibold text-white flex items-center justify-center disabled:opacity-50"
                        style={{ background: "var(--accent)" }}
                      >
                        <span className="flex items-center justify-center gap-1.5">
                          <Search size={13} className="flex-shrink-0" />
                          <span className="text-left leading-tight">
                            Scrape {selectedCompetitorIds.size} <br />
                            competitor
                            {selectedCompetitorIds.size !== 1 ? "s" : ""}
                          </span>
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6">{renderPage()}</div>
      </main>

      {}
      {showScrapePanel && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setShowScrapePanel(false)}
        />
      )}

      {}
      <div
        className="fixed bottom-6 right-6 z-[100] flex flex-col-reverse gap-2 pointer-events-none"
        style={{ maxWidth: "400px" }}
      >
        {toasts.map((toast) => {
          const style = TOAST_STYLES[toast.type] || TOAST_STYLES.info;
          return (
            <div
              key={toast.id}
              className="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border shadow-2xl"
              style={{
                background: "rgba(22, 22, 31, 0.92)",
                backdropFilter: "blur(12px)",
                WebkitBackdropFilter: "blur(12px)",
                borderColor: style.border,
                animation: "slideUp 0.35s ease-out forwards",
              }}
            >
              <div
                className="w-1.5 rounded-full self-stretch flex-shrink-0"
                style={{ background: style.color }}
              />
              <div className="flex-1 min-w-0">
                <p
                  className="text-sm font-medium"
                  style={{ color: style.color }}
                >
                  {toast.message}
                </p>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="flex-shrink-0 p-0.5 rounded transition-colors hover:opacity-80"
                style={{ color: "var(--text-secondary)" }}
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

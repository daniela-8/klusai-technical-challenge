"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
  Briefcase,
  Search,
  Upload,
  MapPin,
  Calendar,
  Building2,
  Loader2,
  Tag,
  ExternalLink,
  Clock,
  Cpu,
  CheckSquare,
  Square,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api";
import type { JobPosting } from "@/lib/types";

type PipelineStep = "idle" | "scrape" | "review" | "analyze" | "done";

const SOURCE_BADGE: Record<
  string,
  { bg: string; color: string; label: string }
> = {
  scraped: { bg: "#22c55e20", color: "#22c55e", label: "Scraped" },
  mocked: { bg: "#f59e0b20", color: "#f59e0b", label: "Mocked" },
  uploaded: { bg: "#6366f120", color: "#6366f1", label: "Uploaded" },
};

interface Props {
  refreshKey?: number;
  pipelineStep?: PipelineStep;
  onAnalyzeJobs?: (jobIds: string[]) => void;
}

export default function JobsPage({
  refreshKey,
  pipelineStep,
  onAnalyzeJobs,
}: Props) {
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedJob, setSelectedJob] = useState<JobPosting | null>(null);
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [filterMode, setFilterMode] = useState<
    "all" | "unprocessed" | "processed"
  >("all");
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadData, setUploadData] = useState({
    job_title: "",
    job_description: "",
    competitor_name: "",
    location: "",
    sector: "",
    salary_range: "",
    job_url: "",
    posting_date: "",
  });
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const loadJobs = useCallback((params?: Record<string, string>) => {
    setLoading(true);
    api
      .getJobs(params)
      .then(setJobs)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadJobs();
  }, [refreshKey, loadJobs]);

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    let result = jobs;
    if (filterMode === "unprocessed")
      result = result.filter((j) => !j.is_processed);
    if (filterMode === "processed")
      result = result.filter((j) => j.is_processed);
    return result;
  }, [jobs, filterMode]);

  const unprocessedJobs = useMemo(
    () => jobs.filter((j) => !j.is_processed),
    [jobs],
  );
  const unprocessedCount = unprocessedJobs.length;

  const toggleJobSelection = (jobId: string) => {
    setSelectedJobIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) next.delete(jobId);
      else next.add(jobId);
      return next;
    });
  };

  const selectAllUnprocessed = () => {
    setSelectedJobIds(new Set(unprocessedJobs.map((j) => j.id)));
  };

  const deselectAll = () => {
    setSelectedJobIds(new Set());
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (value.trim()) {
        loadJobs({ search: value.trim() });
      } else {
        loadJobs();
      }
    }, 400);
  };

  const handleSearch = () => {
    if (search.trim()) {
      loadJobs({ search: search.trim() });
    } else {
      loadJobs();
    }
  };

  const handleUpload = async () => {
    if (!uploadData.job_title.trim() || !uploadData.job_description.trim()) {
      alert("Job title and description are required.");
      return;
    }
    setUploading(true);
    try {
      const newJob = await api.uploadJob({
        ...uploadData,
        competitor_name: uploadData.competitor_name || "Manual Upload",
      });
      setShowUpload(false);
      setUploadData({
        job_title: "",
        job_description: "",
        competitor_name: "",
        location: "",
        sector: "",
        salary_range: "",
        job_url: "",
        posting_date: "",
      });
      loadJobs();

      // Trigger AI analysis for the newly uploaded job
      try {
        await api.triggerProcess([newJob.id]);
        loadJobs();
      } catch {
        // Processing might fail but upload succeeded
      }
    } catch (e) {
      alert(String(e));
    } finally {
      setUploading(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    try {
      return new Date(dateStr).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const isReviewMode = pipelineStep === "review";
  const isAnalyzing = pipelineStep === "analyze";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Job Postings
          </h2>
          <p
            className="text-sm mt-1"
            style={{ color: "var(--text-secondary)" }}
          >
            {jobs.length} posting(s) tracked &middot; {unprocessedCount}{" "}
            awaiting analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          {}
          <div
            className="flex rounded-lg border overflow-hidden"
            style={{ borderColor: "var(--border)" }}
          >
            {(["all", "unprocessed", "processed"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode)}
                className="px-3 py-1.5 text-xs font-medium transition-all"
                style={{
                  background:
                    filterMode === mode ? "var(--accent)" : "var(--bg-card)",
                  color:
                    filterMode === mode ? "white" : "var(--text-secondary)",
                }}
              >
                {mode === "all"
                  ? `All (${jobs.length})`
                  : mode === "unprocessed"
                    ? `New (${unprocessedCount})`
                    : `Processed (${jobs.length - unprocessedCount})`}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
            style={{
              background:
                "linear-gradient(135deg, var(--accent-dim), var(--accent))",
            }}
          >
            <Upload size={16} /> Add Job
          </button>
        </div>
      </div>

      {}
      {(isReviewMode || selectedJobIds.size > 0) && (
        <div
          className="flex items-center justify-between px-4 py-3 rounded-xl border animate-fade-in"
          style={{
            background: isReviewMode
              ? "rgba(99, 102, 241, 0.08)"
              : "var(--bg-card)",
            borderColor: isReviewMode ? "var(--accent)" : "var(--border)",
          }}
        >
          <div className="flex items-center gap-4">
            {isReviewMode && (
              <span
                className="flex items-center gap-2 text-sm font-semibold"
                style={{ color: "var(--accent)" }}
              >
                <Filter size={14} /> Step 2: Select jobs to analyze
              </span>
            )}
            <div className="flex items-center gap-2">
              <button
                onClick={
                  selectedJobIds.size === unprocessedCount &&
                  unprocessedCount > 0
                    ? deselectAll
                    : selectAllUnprocessed
                }
                className="text-xs px-3 py-1.5 rounded border hover:bg-[var(--bg-secondary)] transition-all"
                style={{
                  borderColor: "var(--border)",
                  color:
                    selectedJobIds.size === unprocessedCount &&
                    unprocessedCount > 0
                      ? "var(--text-secondary)"
                      : "var(--accent)",
                }}
              >
                <span className="flex items-center gap-1">
                  <CheckSquare size={11} />
                  {selectedJobIds.size === unprocessedCount &&
                  unprocessedCount > 0
                    ? "Deselect All"
                    : `Select All New (${unprocessedCount})`}
                </span>
              </button>
            </div>
            {selectedJobIds.size > 0 && (
              <span
                className="text-xs font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                {selectedJobIds.size} selected
              </span>
            )}
          </div>
          {selectedJobIds.size > 0 && onAnalyzeJobs && (
            <button
              onClick={() => onAnalyzeJobs(Array.from(selectedJobIds))}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50 transition-all"
              style={{
                background: "linear-gradient(135deg, #7c3aed, #6366f1)",
              }}
              onMouseEnter={(e) => {
                if (!isAnalyzing)
                  e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) =>
                (e.currentTarget.style.transform = "translateY(0)")
              }
            >
              {isAnalyzing ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Analyzing...
                </>
              ) : (
                <>
                  <Cpu size={14} /> Analyze {selectedJobIds.size} Job(s)
                </>
              )}
            </button>
          )}
        </div>
      )}

      {}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: "var(--text-secondary)" }}
          />
          <input
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search by title, description, skills..."
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border text-sm outline-none"
            style={{
              background: "var(--bg-card)",
              borderColor: "var(--border)",
              color: "var(--text-primary)",
            }}
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 rounded-lg text-sm font-medium border"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            background: "var(--bg-card)",
          }}
        >
          Search
        </button>
      </div>

      {}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2
            className="animate-spin"
            size={32}
            style={{ color: "var(--accent)" }}
          />
        </div>
      ) : (
        <div className="space-y-3">
          {filteredJobs.map((job, i) => {
            const badge = SOURCE_BADGE[job.data_source] || SOURCE_BADGE.mocked;
            const isSelected = selectedJobIds.has(job.id);
            return (
              <div
                key={job.id}
                className="rounded-xl p-4 border transition-all duration-200 animate-fade-in"
                style={{
                  background: isSelected
                    ? "rgba(99, 102, 241, 0.06)"
                    : "var(--bg-card)",
                  borderColor: isSelected
                    ? "var(--accent)"
                    : selectedJob?.id === job.id
                      ? "var(--accent)"
                      : "var(--border)",
                  animationDelay: `${i * 30}ms`,
                }}
                onMouseEnter={(e) => {
                  if (selectedJob?.id !== job.id && !isSelected)
                    e.currentTarget.style.borderColor = "var(--border-bright)";
                }}
                onMouseLeave={(e) => {
                  if (selectedJob?.id !== job.id && !isSelected)
                    e.currentTarget.style.borderColor = "var(--border)";
                }}
              >
                <div className="flex items-start gap-3">
                  {}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleJobSelection(job.id);
                    }}
                    className="mt-0.5 flex-shrink-0 transition-all"
                    style={{
                      color: isSelected
                        ? "var(--accent)"
                        : "var(--text-secondary)",
                    }}
                  >
                    {isSelected ? (
                      <CheckSquare size={18} />
                    ) : (
                      <Square size={18} />
                    )}
                  </button>

                  {}
                  <div
                    className="flex-1 min-w-0 cursor-pointer"
                    onClick={() =>
                      setSelectedJob(selectedJob?.id === job.id ? null : job)
                    }
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3
                            className="font-semibold text-sm"
                            style={{ color: "var(--text-primary)" }}
                          >
                            {job.job_title}
                          </h3>
                          <span
                            className="text-xs px-2 py-0.5 rounded-full font-medium"
                            style={{ background: badge.bg, color: badge.color }}
                          >
                            {badge.label}
                          </span>
                          {job.is_processed && job.company_match && (
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-medium"
                              style={{
                                background: "#22c55e20",
                                color: "#22c55e",
                              }}
                            >
                              Matched: {job.company_match.company_name} (
                              {job.company_match.confidence_score}%)
                            </span>
                          )}
                          {!job.is_processed && (
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-medium"
                              style={{
                                background: "#6366f120",
                                color: "#6366f1",
                              }}
                            >
                              Awaiting analysis
                            </span>
                          )}
                        </div>
                        <div
                          className="flex items-center gap-4 mt-2 text-xs flex-wrap"
                          style={{ color: "var(--text-secondary)" }}
                        >
                          <span className="flex items-center gap-1">
                            <Building2 size={12} />
                            {job.competitor_name}
                          </span>
                          {job.location && (
                            <span className="flex items-center gap-1">
                              <MapPin size={12} />
                              {job.location}
                            </span>
                          )}
                          {job.sector && (
                            <span className="flex items-center gap-1">
                              <Tag size={12} />
                              {job.sector}
                            </span>
                          )}
                          {job.posting_date && (
                            <span className="flex items-center gap-1">
                              <Calendar size={12} />
                              Posted {formatDate(job.posting_date)}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock size={12} />
                            Detected {formatDate(job.detected_at)}
                          </span>
                        </div>
                      </div>
                      <span
                        className="text-xs font-medium px-2 py-1 rounded-lg flex-shrink-0"
                        style={{
                          background: job.salary_range
                            ? "var(--bg-secondary)"
                            : "#ef444415",
                          color: job.salary_range
                            ? "var(--success)"
                            : "var(--text-secondary)",
                        }}
                      >
                        {job.salary_range || "Salary unavailable"}
                      </span>
                    </div>

                    {}
                    {selectedJob?.id === job.id && (
                      <div
                        className="mt-4 pt-4 border-t space-y-3 animate-fade-in"
                        style={{ borderColor: "var(--border)" }}
                      >
                        <div>
                          <h4
                            className="text-xs font-semibold uppercase mb-1"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            Description
                          </h4>
                          <p
                            className="text-sm leading-relaxed"
                            style={{ color: "var(--text-primary)" }}
                          >
                            {job.job_description}
                          </p>
                        </div>
                        {job.company_match && (
                          <div
                            className="rounded-lg p-3"
                            style={{ background: "var(--bg-secondary)" }}
                          >
                            <h4
                              className="text-xs font-semibold uppercase mb-2"
                              style={{ color: "var(--accent)" }}
                            >
                              AI Match Analysis
                            </h4>
                            <p
                              className="text-sm mb-2"
                              style={{ color: "var(--text-primary)" }}
                            >
                              <strong>Company:</strong>{" "}
                              {job.company_match.company_name} —{" "}
                              <strong>Confidence:</strong>{" "}
                              {job.company_match.confidence_score}%
                            </p>
                            <p
                              className="text-sm"
                              style={{ color: "var(--text-secondary)" }}
                            >
                              {job.company_match.match_explanation}
                            </p>
                          </div>
                        )}
                        {job.job_url && (
                          <a
                            href={job.job_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs hover:underline"
                            style={{ color: "var(--accent)" }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink size={12} /> View original posting
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          {filteredJobs.length === 0 && (
            <div
              className="rounded-xl p-12 border text-center"
              style={{
                background: "var(--bg-card)",
                borderColor: "var(--border)",
              }}
            >
              <Briefcase
                size={48}
                className="mx-auto mb-4"
                style={{ color: "var(--text-secondary)" }}
              />
              <h3
                className="text-lg font-semibold mb-2"
                style={{ color: "var(--text-primary)" }}
              >
                {filterMode === "unprocessed"
                  ? "All jobs have been analyzed!"
                  : "No postings found"}
              </h3>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                {filterMode === "unprocessed"
                  ? "Switch to 'All' to see processed jobs."
                  : "Run the pipeline or add a job manually."}
              </p>
            </div>
          )}
        </div>
      )}

      {}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div
            className="w-full max-w-lg rounded-xl p-6 border animate-fade-in"
            style={{
              background: "var(--bg-card)",
              borderColor: "var(--border)",
            }}
          >
            <h3
              className="text-lg font-bold mb-1"
              style={{ color: "var(--text-primary)" }}
            >
              Add a Job Posting
            </h3>
            <p
              className="text-xs mb-4"
              style={{ color: "var(--text-secondary)" }}
            >
              Manually add a job posting for AI analysis. Analysis will start
              automatically.
            </p>
            <div className="space-y-3">
              <div>
                <label
                  className="block text-xs font-medium mb-1"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Job Title <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  value={uploadData.job_title}
                  onChange={(e) =>
                    setUploadData({ ...uploadData, job_title: e.target.value })
                  }
                  placeholder="e.g., Senior Sales Director — B2B SaaS"
                  className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                  style={{
                    background: "var(--bg-secondary)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    className="block text-xs font-medium mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Competitor <span style={{ color: "#ef4444" }}>*</span>
                  </label>
                  <input
                    value={uploadData.competitor_name}
                    onChange={(e) =>
                      setUploadData({
                        ...uploadData,
                        competitor_name: e.target.value,
                      })
                    }
                    placeholder="e.g., Michael Page"
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
                <div>
                  <label
                    className="block text-xs font-medium mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Location <span style={{ color: "#ef4444" }}>*</span>
                  </label>
                  <input
                    value={uploadData.location}
                    onChange={(e) =>
                      setUploadData({ ...uploadData, location: e.target.value })
                    }
                    placeholder="e.g., Paris, France"
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    className="block text-xs font-medium mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Sector / Function{" "}
                    <span style={{ color: "#ef4444" }}>*</span>
                  </label>
                  <input
                    value={uploadData.sector}
                    onChange={(e) =>
                      setUploadData({ ...uploadData, sector: e.target.value })
                    }
                    placeholder="e.g., FinTech / Sales Management"
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
                <div>
                  <label
                    className="block text-xs font-medium mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Salary Range
                  </label>
                  <input
                    value={uploadData.salary_range}
                    onChange={(e) =>
                      setUploadData({
                        ...uploadData,
                        salary_range: e.target.value,
                      })
                    }
                    placeholder="e.g., 65K€–80K€ + variable"
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    className="block text-xs font-medium mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Job URL
                  </label>
                  <input
                    value={uploadData.job_url}
                    onChange={(e) =>
                      setUploadData({ ...uploadData, job_url: e.target.value })
                    }
                    placeholder="https://..."
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
                <div>
                  <label
                    className="block text-xs font-medium mb-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Publication Date
                  </label>
                  <input
                    type="date"
                    value={uploadData.posting_date}
                    onChange={(e) =>
                      setUploadData({
                        ...uploadData,
                        posting_date: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                    style={{
                      background: "var(--bg-secondary)",
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
              </div>
              <div>
                <label
                  className="block text-xs font-medium mb-1"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Job Description <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <textarea
                  value={uploadData.job_description}
                  onChange={(e) =>
                    setUploadData({
                      ...uploadData,
                      job_description: e.target.value,
                    })
                  }
                  placeholder="Paste the full job description for AI analysis..."
                  rows={5}
                  className="w-full px-3 py-2 rounded-lg border text-sm outline-none resize-none"
                  style={{
                    background: "var(--bg-secondary)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowUpload(false)}
                className="flex-1 py-2 rounded-lg text-sm font-medium border"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-secondary)",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="flex-1 py-2 rounded-lg text-sm font-medium text-white flex items-center justify-center gap-2 disabled:opacity-50"
                style={{ background: "var(--accent)" }}
              >
                {uploading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Analyzing...
                  </>
                ) : (
                  "Upload & Analyze"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

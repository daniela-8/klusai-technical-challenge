const API_BASE = "/api";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getDashboard: () => fetchApi<import("./types").DashboardStats>("/dashboard"),

  getCompetitors: () =>
    fetchApi<import("./types").Competitor[]>("/competitors"),
  createCompetitor: (data: {
    name: string;
    website_url: string;
    careers_url: string;
    category: string;
  }) =>
    fetchApi<import("./types").Competitor>("/competitors", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteCompetitor: (id: string) =>
    fetchApi<void>(`/competitors/${id}`, { method: "DELETE" }),
  toggleCompetitor: (id: string) =>
    fetchApi<import("./types").Competitor>(`/competitors/${id}/toggle`, {
      method: "PATCH",
    }),

  getJobs: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return fetchApi<import("./types").JobPosting[]>(`/jobs${qs}`);
  },
  getJob: (id: string) => fetchApi<import("./types").JobPosting>(`/jobs/${id}`),
  uploadJob: (data: {
    job_title: string;
    job_description: string;
    competitor_name?: string;
    location?: string;
    sector?: string;
    salary_range?: string;
    job_url?: string;
    posting_date?: string;
  }) =>
    fetchApi<import("./types").JobPosting>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMatches: (minConfidence?: number) => {
    const qs = minConfidence ? `?min_confidence=${minConfidence}` : "";
    return fetchApi<import("./types").CompanyMatchDetail[]>(
      `/companies/matches${qs}`,
    );
  },
  getPriorities: (minScore?: number) => {
    const qs = minScore ? `?min_score=${minScore}` : "";
    return fetchApi<import("./types").PriorityScore[]>(
      `/companies/priorities${qs}`,
    );
  },

  triggerScrape: (competitorIds?: string[]) =>
    fetchApi<import("./types").ScrapeResult>("/pipeline/scrape", {
      method: "POST",
      body: competitorIds
        ? JSON.stringify({ competitor_ids: competitorIds })
        : undefined,
    }),
  triggerProcess: (jobIds?: string[]) =>
    fetchApi<import("./types").ProcessResult>("/pipeline/process", {
      method: "POST",
      body: jobIds
        ? JSON.stringify({ job_ids: jobIds, max_jobs: jobIds.length })
        : undefined,
    }),
  resetAllData: () =>
    fetchApi<{ status: string; message: string }>("/pipeline/reset", {
      method: "POST",
    }),
  getPipelineStatus: () =>
    fetchApi<{
      is_running: boolean;
      started_at: string | null;
      last_result: Record<string, unknown> | null;
    }>("/pipeline/status"),
  getMatchCount: () =>
    fetchApi<{ match_count: number }>("/pipeline/match-count"),
  runFullPipeline: () =>
    fetchApi<Record<string, unknown>>("/pipeline/full-pipeline", {
      method: "POST",
    }),
  generateBrief: (companyName: string) =>
    fetchApi<{
      id: string;
      company_name: string;
      brief_content: import("./types").BriefContent;
    }>("/pipeline/brief", {
      method: "POST",
      body: JSON.stringify({ company_name: companyName }),
    }),

  getBriefs: () => fetchApi<import("./types").ProspectBrief[]>("/briefs"),
  getBrief: (companyName: string) =>
    fetchApi<import("./types").ProspectBrief>(
      `/briefs/${encodeURIComponent(companyName)}`,
    ),

  getAlerts: (unreadOnly?: boolean) => {
    const qs = unreadOnly ? "?unread_only=true" : "";
    return fetchApi<import("./types").Alert[]>(`/alerts${qs}`);
  },
  markAlertRead: (id: string) =>
    fetchApi<void>(`/alerts/${id}/read`, { method: "PATCH" }),
  markAllAlertsRead: () =>
    fetchApi<void>("/alerts/read-all", { method: "PATCH" }),

  getHealth: () =>
    fetchApi<{ status: string; version: string; openai_configured: boolean }>(
      "/health",
    ),
};

export interface Competitor {
  id: string;
  name: string;
  website_url: string;
  careers_url: string;
  category: "large" | "sales_tech" | "finance";
  is_active: boolean;
  last_scraped_at: string | null;
  created_at: string;
  job_count: number;
}

export interface CompanyMatch {
  id: string;
  company_name: string;
  confidence_score: number;
  match_explanation: string;
  signals_used: SignalUsed[];
  enrichment_data: Record<string, unknown> | null;
  alternative_matches: AlternativeMatch[] | null;
  additional_data_needed: string | null;
  created_at: string;
}

export interface SignalUsed {
  signal_type: string;
  signal_value: string;
  inference: string;
}

export interface AlternativeMatch {
  company_name: string;
  confidence_score: number;
  reasoning: string;
}

export interface JobPosting {
  id: string;
  competitor_id: string;
  competitor_name: string;
  job_title: string;
  job_description: string;
  location: string | null;
  sector: string | null;
  salary_range: string | null;
  job_url: string | null;
  posting_date: string | null;
  detected_at: string;
  data_source: "scraped" | "mocked" | "uploaded";
  is_processed: boolean;
  company_match: CompanyMatch | null;
}

export interface PriorityScore {
  id: string;
  company_name: string;
  priority_score: number;
  scoring_breakdown: Record<
    string,
    number | { score: number; justification: string }
  >;
  rationale: string;
  job_count: number;
  created_at: string;
  updated_at: string;
  jobs: JobSummary[];
}

export interface JobSummary {
  id: string;
  job_title: string;
  competitor_name: string;
  location: string | null;
  sector: string | null;
  salary_range: string | null;
  data_source: string | null;
}

export interface DashboardStats {
  total_jobs: number;
  total_companies_matched: number;
  high_priority_targets: number;
  active_competitors: number;
  avg_confidence: number;
  recent_alerts: number;
  jobs_by_source: Record<string, number>;
  jobs_by_competitor: Record<string, number>;
  confidence_distribution: Record<string, number>;
  top_sectors: Array<{ name: string; count: number }>;
}

export interface Alert {
  id: string;
  alert_type: string;
  title: string;
  message: string;
  severity: string;
  related_entity_id: string | null;
  related_entity_type: string | null;
  is_read: boolean;
  created_at: string;
}

export interface ProspectBrief {
  id: string;
  company_name: string;
  brief_content: BriefContent;
  generated_at: string;
}

export interface BriefContent {
  company_overview: {
    name: string;
    industry: string;
    size_estimate: string;
    growth_stage: string;
    headquarters: string;
    key_context: string;
  };
  hiring_intelligence: {
    open_roles_detected: string[];
    hiring_departments: string[];
    hiring_velocity: string;
    role_seniority_mix: string;
  };
  why_target: {
    primary_reason: string;
    supporting_reasons: string[];
    timing_rationale: string;
  };
  competitor_intelligence: {
    triggering_posting: string;
    competitor_involved: string;
    competitive_angle: string;
    trigger_job_url?: string;
  };
  contact_strategy: {
    ideal_contact_title: string;
    alternative_contacts: string[];
    linkedin_search_tips: string;
    email_approach: string;
    hiring_manager_contact?: {
      name?: string;
      title?: string;
      phone?: string;
      email?: string;
      linkedin_url?: string;
    };
  };
  talking_points: string[];
  recommended_action: {
    next_step: string;
    timeline: string;
    preparation_needed: string;
  };
  risk_factors: string[];
}

export interface CompanyMatchDetail {
  id: string;
  company_name: string;
  confidence_score: number;
  match_explanation: string;
  signals_used: SignalUsed[];
  enrichment_data: Record<string, unknown> | null;
  alternative_matches: AlternativeMatch[] | null;
  additional_data_needed: string | null;
  created_at: string;
  job: JobSummary & {
    job_url?: string;
    posting_date?: string;
    data_source?: string;
  };
}

export interface ScrapeResult {
  status: string;
  competitors_scraped: number;
  jobs_collected: number;
  errors: string[];
}

export interface ProcessResult {
  status: string;
  jobs_processed: number;
  matches_created: number;
  scores_updated: number;
  errors: string[];
  jobs_remaining: number;
  message?: string;
}

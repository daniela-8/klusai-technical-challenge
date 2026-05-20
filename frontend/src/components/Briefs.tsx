"use client";

import { useEffect, useState } from "react";
import {
  FileText,
  Loader2,
  Building2,
  Users,
  Target,
  MessageSquare,
  ArrowRight,
  AlertTriangle,
  Crosshair,
  Phone,
  Mail,
  Link,
  ExternalLink,
  UserCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ProspectBrief, BriefContent } from "@/lib/types";

function BriefCard({ brief }: { brief: ProspectBrief }) {
  const c = brief.brief_content as BriefContent;
  const [expanded, setExpanded] = useState(false);

  const formatTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleString("fr-FR", {
        dateStyle: "long",
        timeStyle: "short",
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
    } catch {
      return ts;
    }
  };

  return (
    <div
      className="rounded-xl border animate-fade-in"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      {}
      <div
        className="p-5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3
              className="text-lg font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              {brief.company_name}
            </h3>
            <p
              className="text-xs mt-1"
              style={{ color: "var(--text-secondary)" }}
            >
              Generated on {formatTimestamp(brief.generated_at)}
            </p>
          </div>
          <span
            className="text-xs px-3 py-1 rounded-full font-medium"
            style={{ background: "#6366f120", color: "#6366f1" }}
          >
            {c.company_overview?.industry || "Unknown"}
          </span>
        </div>
        {c.company_overview?.key_context && (
          <p
            className="text-sm mt-3 line-clamp-2"
            style={{ color: "var(--text-secondary)" }}
          >
            {c.company_overview.key_context}
          </p>
        )}
      </div>

      {expanded && (
        <div
          className="px-5 pb-5 pt-2 border-t space-y-5 animate-fade-in"
          style={{ borderColor: "var(--border)" }}
        >
          {}
          <Section icon={Building2} title="Company Overview">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {c.company_overview &&
                Object.entries(c.company_overview)
                  .filter(([k]) => k !== "key_context")
                  .map(([key, val]) => (
                    <InfoBox
                      key={key}
                      label={key.replace(/_/g, " ")}
                      value={String(val || "—")}
                    />
                  ))}
            </div>
            {c.company_overview?.key_context && (
              <p
                className="text-sm mt-2"
                style={{ color: "var(--text-primary)" }}
              >
                {c.company_overview.key_context}
              </p>
            )}
          </Section>

          {}
          <Section icon={Users} title="Open Roles Detected">
            {c.hiring_intelligence?.open_roles_detected && (
              <div className="space-y-1">
                {c.hiring_intelligence.open_roles_detected.map((role, i) => (
                  <span
                    key={i}
                    className="inline-block text-xs px-2 py-1 mr-1 mb-1 rounded-lg"
                    style={{
                      background: "var(--bg-secondary)",
                      color: "var(--text-primary)",
                    }}
                  >
                    {role}
                  </span>
                ))}
              </div>
            )}
            {c.hiring_intelligence?.hiring_velocity && (
              <p
                className="text-sm mt-2"
                style={{ color: "var(--text-secondary)" }}
              >
                {c.hiring_intelligence.hiring_velocity}
              </p>
            )}
            {c.hiring_intelligence?.role_seniority_mix && (
              <p
                className="text-xs mt-1"
                style={{ color: "var(--text-secondary)" }}
              >
                Seniority: {c.hiring_intelligence.role_seniority_mix}
              </p>
            )}
          </Section>

          {}
          {c.competitor_intelligence && (
            <Section icon={Crosshair} title="Triggering Competitor Posting">
              <div
                className="rounded-lg p-3"
                style={{ background: "var(--bg-secondary)" }}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  <div>
                    <span style={{ color: "var(--text-secondary)" }}>
                      Triggering posting
                    </span>
                    <p
                      className="font-medium"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {c.competitor_intelligence.triggering_posting}
                    </p>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-secondary)" }}>
                      Competitor involved
                    </span>
                    <p
                      className="font-medium"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {c.competitor_intelligence.competitor_involved}
                    </p>
                  </div>
                </div>
                {c.competitor_intelligence.competitive_angle && (
                  <p
                    className="text-xs mt-2"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    <strong>Competitive angle:</strong>{" "}
                    {c.competitor_intelligence.competitive_angle}
                  </p>
                )}
                {c.competitor_intelligence.trigger_job_url &&
                  c.competitor_intelligence.trigger_job_url !== "N/A" &&
                  c.competitor_intelligence.trigger_job_url !==
                    "Non disponible" &&
                  c.competitor_intelligence.trigger_job_url !==
                    "Not available" && (
                    <a
                      href={c.competitor_intelligence.trigger_job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs mt-2 hover:underline"
                      style={{ color: "var(--accent)" }}
                    >
                      <ExternalLink size={11} /> View triggering posting
                    </a>
                  )}
              </div>
            </Section>
          )}

          {}
          <Section icon={Target} title="Why Target This Company">
            {c.why_target?.primary_reason && (
              <p
                className="text-sm font-semibold"
                style={{ color: "var(--success)" }}
              >
                {c.why_target.primary_reason}
              </p>
            )}
            {c.why_target?.supporting_reasons?.map((r, i) => (
              <p
                key={i}
                className="text-sm mt-1"
                style={{ color: "var(--text-secondary)" }}
              >
                • {r}
              </p>
            ))}
            {c.why_target?.timing_rationale && (
              <p
                className="text-sm mt-2 italic"
                style={{ color: "var(--warning)" }}
              >
                {c.why_target.timing_rationale}
              </p>
            )}
          </Section>

          {}
          <Section icon={MessageSquare} title="Talking Points">
            <ol className="space-y-2">
              {c.talking_points?.map((tp, i) => (
                <li
                  key={i}
                  className="text-sm flex items-start gap-2"
                  style={{ color: "var(--text-primary)" }}
                >
                  <span
                    className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                    style={{ background: "var(--accent)", color: "white" }}
                  >
                    {i + 1}
                  </span>
                  {tp}
                </li>
              ))}
            </ol>
          </Section>

          {}
          {c.contact_strategy && (
            <Section icon={UserCheck} title="Hiring Manager / HR Contact">
              <div
                className="rounded-lg p-3"
                style={{ background: "var(--bg-secondary)" }}
              >
                <InfoBox
                  label="Primary contact"
                  value={c.contact_strategy.ideal_contact_title || "—"}
                />

                {c.contact_strategy.hiring_manager_contact && (
                  <div
                    className="mt-3 rounded-lg p-3"
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <h5
                      className="text-xs font-semibold uppercase mb-2 flex items-center gap-1"
                      style={{ color: "#f59e0b" }}
                    >
                      <UserCheck size={11} /> Estimated Contact Details
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                      {c.contact_strategy.hiring_manager_contact.name && (
                        <div>
                          <span style={{ color: "var(--text-secondary)" }}>
                            Name
                          </span>
                          <p
                            className="font-medium"
                            style={{ color: "var(--text-primary)" }}
                          >
                            {c.contact_strategy.hiring_manager_contact.name}
                          </p>
                        </div>
                      )}
                      {c.contact_strategy.hiring_manager_contact.title && (
                        <div>
                          <span style={{ color: "var(--text-secondary)" }}>
                            Title
                          </span>
                          <p
                            className="font-medium"
                            style={{ color: "var(--text-primary)" }}
                          >
                            {c.contact_strategy.hiring_manager_contact.title}
                          </p>
                        </div>
                      )}
                      {c.contact_strategy.hiring_manager_contact.phone && (
                        <div className="flex items-center gap-1">
                          <Phone
                            size={11}
                            style={{ color: "var(--text-secondary)" }}
                          />
                          <span style={{ color: "var(--text-primary)" }}>
                            {c.contact_strategy.hiring_manager_contact.phone}
                          </span>
                        </div>
                      )}
                      {c.contact_strategy.hiring_manager_contact.email && (
                        <div className="flex items-center gap-1">
                          <Mail
                            size={11}
                            style={{ color: "var(--text-secondary)" }}
                          />
                          <span style={{ color: "var(--text-primary)" }}>
                            {c.contact_strategy.hiring_manager_contact.email}
                          </span>
                        </div>
                      )}
                      {c.contact_strategy.hiring_manager_contact
                        .linkedin_url && (
                        <div className="col-span-2">
                          <a
                            href={
                              c.contact_strategy.hiring_manager_contact
                                .linkedin_url
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs hover:underline"
                            style={{ color: "var(--accent)" }}
                          >
                            <Link size={11} /> Search on LinkedIn
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {c.contact_strategy.email_approach && (
                  <p
                    className="text-sm mt-2 italic"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {c.contact_strategy.email_approach}
                  </p>
                )}
              </div>
            </Section>
          )}

          {}
          <Section icon={ArrowRight} title="Recommended Action">
            {c.recommended_action && (
              <div
                className="rounded-lg p-3"
                style={{
                  background: "#6366f110",
                  border: "1px solid var(--accent)",
                }}
              >
                <p
                  className="text-sm font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  {c.recommended_action.next_step}
                </p>
                {c.recommended_action.timeline && (
                  <p
                    className="text-xs mt-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Timeline: {c.recommended_action.timeline}
                  </p>
                )}
                {c.recommended_action.preparation_needed && (
                  <p
                    className="text-xs mt-1"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    Preparation: {c.recommended_action.preparation_needed}
                  </p>
                )}
              </div>
            )}
          </Section>

          {}
          {c.risk_factors && c.risk_factors.length > 0 && (
            <Section icon={AlertTriangle} title="Risk Factors">
              {c.risk_factors.map((r, i) => (
                <p
                  key={i}
                  className="text-sm"
                  style={{ color: "var(--warning)" }}
                >
                  ⚠ {r}
                </p>
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4
        className="text-xs font-semibold uppercase mb-2 flex items-center gap-1"
        style={{ color: "var(--accent)" }}
      >
        <Icon size={12} /> {title}
      </h4>
      {children}
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-lg p-2 text-xs"
      style={{ background: "var(--bg-secondary)" }}
    >
      <span className="capitalize" style={{ color: "var(--text-secondary)" }}>
        {label}
      </span>
      <p
        className="font-medium mt-0.5"
        style={{ color: "var(--text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

export default function BriefsPage({ refreshKey }: { refreshKey?: number }) {
  const [briefs, setBriefs] = useState<ProspectBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .getBriefs()
      .then(setBriefs)
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
          Prospect Briefs
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          AI-generated one-pagers for sales call preparation
        </p>
      </div>

      {briefs.length === 0 ? (
        <div
          className="rounded-xl p-12 border text-center"
          style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
        >
          <FileText
            size={48}
            className="mx-auto mb-4"
            style={{ color: "var(--text-secondary)" }}
          />
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)" }}
          >
            No briefs generated
          </h3>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Go to the Priority Board and click &quot;Brief&quot; on a company to
            generate a prospect brief.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {briefs.map((brief) => (
            <BriefCard key={brief.id} brief={brief} />
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import {
  Users,
  Plus,
  ExternalLink,
  Globe,
  Loader2,
  ToggleLeft,
  ToggleRight,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Competitor } from "@/lib/types";
import clsx from "clsx";

const CATEGORY_LABELS: Record<string, string> = {
  large: "Large Firm",
  sales_tech: "Sales / Tech",
  finance: "Finance",
};

const CATEGORY_COLORS: Record<string, string> = {
  large: "#3b82f6",
  sales_tech: "#22c55e",
  finance: "#f59e0b",
};

export default function CompetitorsPage({
  refreshKey,
}: {
  refreshKey?: number;
}) {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newComp, setNewComp] = useState({
    name: "",
    website_url: "",
    careers_url: "",
    category: "large",
  });

  const loadData = () => {
    api
      .getCompetitors()
      .then(setCompetitors)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [refreshKey]);

  const handleAdd = async () => {
    try {
      await api.createCompetitor(newComp);
      setShowAddModal(false);
      setNewComp({
        name: "",
        website_url: "",
        careers_url: "",
        category: "large",
      });
      loadData();
    } catch (e) {
      alert(String(e));
    }
  };

  const handleToggle = async (id: string) => {
    await api.toggleCompetitor(id);
    loadData();
  };

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
      <div className="flex items-center justify-between">
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Competitors
          </h2>
          <p
            className="text-sm mt-1"
            style={{ color: "var(--text-secondary)" }}
          >
            Manage competitor sources for job tracking
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all"
          style={{
            background:
              "linear-gradient(135deg, var(--accent-dim), var(--accent))",
          }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.transform = "translateY(-1px)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.transform = "translateY(0)")
          }
        >
          <Plus size={16} /> Add Competitor
        </button>
      </div>

      {}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {competitors.map((comp, i) => (
          <div
            key={comp.id}
            className="rounded-xl p-5 border transition-all duration-200 animate-fade-in"
            style={{
              background: "var(--bg-card)",
              borderColor: "var(--border)",
              animationDelay: `${i * 50}ms`,
              opacity: comp.is_active ? 1 : 0.5,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--border-bright)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3
                  className="font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  {comp.name}
                </h3>
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{
                    background: `${CATEGORY_COLORS[comp.category]}20`,
                    color: CATEGORY_COLORS[comp.category],
                  }}
                >
                  {CATEGORY_LABELS[comp.category]}
                </span>
              </div>
              <button
                onClick={() => handleToggle(comp.id)}
                style={{
                  color: comp.is_active
                    ? "var(--success)"
                    : "var(--text-secondary)",
                }}
              >
                {comp.is_active ? (
                  <ToggleRight size={24} />
                ) : (
                  <ToggleLeft size={24} />
                )}
              </button>
            </div>

            <div
              className="space-y-2 text-sm"
              style={{ color: "var(--text-secondary)" }}
            >
              <div className="flex items-center gap-2">
                <Globe size={14} />
                <a
                  href={comp.website_url}
                  target="_blank"
                  rel="noopener"
                  className="hover:underline truncate"
                >
                  {comp.website_url.replace(/^https?:\/\//, "")}
                </a>
              </div>
              <div className="flex items-center gap-2">
                <ExternalLink size={14} />
                <span className="truncate">
                  {comp.careers_url.replace(/^https?:\/\//, "")}
                </span>
              </div>
            </div>

            <div
              className="flex items-center justify-between mt-4 pt-3 border-t"
              style={{ borderColor: "var(--border)" }}
            >
              <div>
                <span
                  className="text-2xl font-bold"
                  style={{ color: "var(--accent)" }}
                >
                  {comp.job_count}
                </span>
                <span
                  className="text-xs ml-1"
                  style={{ color: "var(--text-secondary)" }}
                >
                  jobs tracked
                </span>
              </div>
              {comp.last_scraped_at && (
                <span
                  className="text-xs"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Last: {new Date(comp.last_scraped_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div
            className="w-full max-w-md rounded-xl p-6 border animate-fade-in"
            style={{
              background: "var(--bg-card)",
              borderColor: "var(--border)",
            }}
          >
            <h3
              className="text-lg font-bold mb-4"
              style={{ color: "var(--text-primary)" }}
            >
              Add Competitor
            </h3>
            <div className="space-y-3">
              {[
                {
                  key: "name",
                  label: "Competitor Name",
                  placeholder: "e.g., Robert Walters",
                },
                {
                  key: "website_url",
                  label: "Website URL",
                  placeholder: "https://...",
                },
                {
                  key: "careers_url",
                  label: "Careers Page URL",
                  placeholder: "https://.../careers",
                },
              ].map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label
                    className="text-xs font-medium mb-1 block"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {label}
                  </label>
                  <input
                    value={(newComp as Record<string, string>)[key]}
                    onChange={(e) =>
                      setNewComp({ ...newComp, [key]: e.target.value })
                    }
                    placeholder={placeholder}
                    className="w-full px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2"
                    style={
                      {
                        background: "var(--bg-secondary)",
                        borderColor: "var(--border)",
                        color: "var(--text-primary)",
                        "--tw-ring-color": "var(--accent)",
                      } as React.CSSProperties
                    }
                  />
                </div>
              ))}
              <div>
                <label
                  className="text-xs font-medium mb-1 block"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Category
                </label>
                <select
                  value={newComp.category}
                  onChange={(e) =>
                    setNewComp({ ...newComp, category: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                  style={{
                    background: "var(--bg-secondary)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                >
                  <option value="large">Large Firm</option>
                  <option value="sales_tech">Sales / Tech</option>
                  <option value="finance">Finance</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 py-2 rounded-lg text-sm font-medium border"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-secondary)",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                className="flex-1 py-2 rounded-lg text-sm font-medium text-white"
                style={{ background: "var(--accent)" }}
              >
                Add Competitor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

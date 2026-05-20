"use client";

import { useEffect, useState } from "react";
import {
  Bell,
  Check,
  CheckCheck,
  Loader2,
  AlertTriangle,
  Info,
  Briefcase,
  Trophy,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { formatDistanceToNow } from "date-fns";

const ALERT_ICONS: Record<string, React.ElementType> = {
  new_job: Briefcase,
  high_priority: Trophy,
  reposted_job: AlertTriangle,
  new_competitor: Info,
  confidence_change: Info,
};

const SEVERITY_COLORS: Record<string, string> = {
  info: "#3b82f6",
  warning: "#f59e0b",
  error: "#ef4444",
  critical: "#ef4444",
};

export default function AlertsPage({
  onCountChange,
  refreshKey,
}: {
  onCountChange: (count: number) => void;
  refreshKey?: number;
}) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAlerts = () => {
    api
      .getAlerts()
      .then((data) => {
        setAlerts(data);
        onCountChange(data.filter((a) => !a.is_read).length);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAlerts();
  }, [refreshKey]);

  const handleMarkRead = async (id: string) => {
    await api.markAlertRead(id);
    loadAlerts();
  };

  const handleMarkAllRead = async () => {
    await api.markAllAlertsRead();
    loadAlerts();
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

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            Alerts
          </h2>
          <p
            className="text-sm mt-1"
            style={{ color: "var(--text-secondary)" }}
          >
            {unreadCount} unread alert{unreadCount !== 1 ? "s" : ""} ·{" "}
            {alerts.length} total
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
            }}
          >
            <CheckCheck size={16} /> Mark all read
          </button>
        )}
      </div>

      <div className="space-y-2">
        {alerts.map((alert, i) => {
          const Icon = ALERT_ICONS[alert.alert_type] || Bell;
          const color = SEVERITY_COLORS[alert.severity] || "#3b82f6";
          return (
            <div
              key={alert.id}
              className="rounded-xl p-4 border flex items-start gap-3 transition-all duration-200 animate-fade-in"
              style={{
                background: alert.is_read
                  ? "var(--bg-card)"
                  : "var(--bg-card-hover)",
                borderColor: alert.is_read ? "var(--border)" : color,
                animationDelay: `${i * 20}ms`,
                opacity: alert.is_read ? 0.6 : 1,
              }}
            >
              <div
                className="p-2 rounded-lg flex-shrink-0"
                style={{ background: `${color}20` }}
              >
                <Icon size={16} style={{ color }} />
              </div>
              <div className="flex-1 min-w-0">
                <h4
                  className="text-sm font-medium"
                  style={{ color: "var(--text-primary)" }}
                >
                  {alert.title}
                </h4>
                <p
                  className="text-xs mt-0.5"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {alert.message}
                </p>
                <span
                  className="text-xs mt-1 block"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {formatDistanceToNow(new Date(alert.created_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
              {!alert.is_read && (
                <button
                  onClick={() => handleMarkRead(alert.id)}
                  className="p-1.5 rounded-lg transition-colors flex-shrink-0"
                  style={{ color: "var(--text-secondary)" }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = "var(--bg-secondary)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <Check size={14} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from "recharts";
import {
  BarChart2, Link2, ArrowLeft, Clock, Globe,
  MousePointer, TrendingUp, Zap, Activity
} from "lucide-react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { AnalyticsDetail } from "@/types";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <p style={{ fontSize: 11, color: "var(--txt-3)", marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: 14, color: "#a78bfa", fontWeight: 600 }}>
        {payload[0].value}{" "}
        <span style={{ fontWeight: 400, color: "var(--txt-2)" }}>clicks</span>
      </p>
    </div>
  );
};

function Skeleton({ style }: { style?: React.CSSProperties }) {
  return <div className="skeleton" style={style} />;
}

export default function AnalyticsPage() {
  const { shortCode } = useParams() as { shortCode: string };
  const [data, setData]     = useState<AnalyticsDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!shortCode) return;
    api.getAnalytics(shortCode)
      .then(setData)
      .catch(err => setError(err instanceof ApiError ? err.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [shortCode]);

  const clicksMonth = data?.clicks_by_day.reduce((s, d) => s + d.clicks, 0) ?? 0;
  const avgPerDay   = data?.clicks_by_day.length
    ? Math.round(clicksMonth / data.clicks_by_day.length) : 0;
  const maxRef      = data?.top_referers[0]?.count ?? 1;

  return (
    <>
      {/* ── Nav ── */}
      <nav className="nav">
        <div className="nav-inner">
          <Link href="/" className="nav-link" style={{ gap: 6 }}>
            <ArrowLeft size={15} />
            Back to shortener
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <div className="nav-logo-icon" style={{ width: 28, height: 28, borderRadius: 8 }}>
              <Activity size={13} color="white" />
            </div>
            <span className="nav-logo-text" style={{ fontSize: 15 }}>Analytics</span>
          </div>
        </div>
      </nav>

      <div className="page-wrap">

        {/* Error */}
        {error && (
          <div style={{
            padding: "14px 18px", borderRadius: 14, marginBottom: 20,
            background: "rgba(248,113,113,.07)", border: "1px solid rgba(248,113,113,.22)",
            color: "var(--red)", fontSize: 13
          }}>
            {error}
          </div>
        )}

        {/* URL info */}
        {loading
          ? <Skeleton style={{ height: 88, marginBottom: 22 }} />
          : data && (
            <div className="info-card au">
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 7 }}>
                    <span className="code-badge">/{shortCode}</span>
                    <span className={`status-dot ${data.summary.is_active ? "status-active" : "status-inactive"}`}>
                      {data.summary.is_active ? "● Active" : "Inactive"}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--txt-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 520 }}>
                    {data.summary.original_url}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--txt-3)", fontSize: 12, flexShrink: 0 }}>
                  <Clock size={13} />
                  Created {new Date(data.summary.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}
                </div>
              </div>
            </div>
          )}

        {/* Stat cards */}
        {loading
          ? <div className="stats-grid"><Skeleton style={{ height: 120 }} /><Skeleton style={{ height: 120 }} /><Skeleton style={{ height: 120 }} /></div>
          : data && (
            <div className="stats-grid au1">
              {[
                { cls: "stat-v", icon: MousePointer, label: "Total clicks",   val: data.summary.total_clicks.toLocaleString() },
                { cls: "stat-c", icon: TrendingUp,   label: "Last 30 days",   val: clicksMonth.toLocaleString() },
                { cls: "stat-a", icon: BarChart2,     label: "Daily average",  val: avgPerDay },
              ].map(({ cls, icon: Icon, label, val }) => (
                <div key={label} className={`stat-card ${cls}`}>
                  <div className="stat-icon"><Icon size={18} /></div>
                  <p className="stat-value">{val}</p>
                  <p className="stat-label">{label}</p>
                </div>
              ))}
            </div>
          )}

        {/* Chart */}
        {loading
          ? <Skeleton style={{ height: 280, marginBottom: 22 }} />
          : data && data.clicks_by_day.length > 0
            ? (
              <div className="chart-card au2">
                <div className="chart-title">
                  <Zap size={15} color="#7c3aed" />
                  <h2>Click activity</h2>
                  <span className="tag">Last 30 days</span>
                </div>
                <ResponsiveContainer width="100%" height={230}>
                  <AreaChart data={data.clicks_by_day} margin={{ top: 5, right: 4, left: -28, bottom: 0 }}>
                    <defs>
                      <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#7c3aed" stopOpacity={0.28} />
                        <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="strokeGrad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%"   stopColor="#7c3aed" />
                        <stop offset="100%" stopColor="#22d3ee" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "var(--txt-3)", fontSize: 10 }}
                      tickLine={false} axisLine={false}
                      tickFormatter={v => new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    />
                    <YAxis
                      tick={{ fill: "var(--txt-3)", fontSize: 10 }}
                      tickLine={false} axisLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(124,58,237,.25)", strokeWidth: 1 }} />
                    <Area
                      type="monotone" dataKey="clicks"
                      stroke="url(#strokeGrad)" strokeWidth={2}
                      fill="url(#grad)" dot={false}
                      activeDot={{ r: 4, fill: "#a78bfa", stroke: "#7c3aed", strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : data ? (
              <div className="chart-card" style={{ textAlign: "center", padding: "48px 24px", marginBottom: 22 }}>
                <div className="empty-state">
                  <Activity size={32} />
                  <p>No click data yet. Share your short link to start collecting analytics.</p>
                </div>
              </div>
            ) : null
        }

        {/* Bottom panels */}
        {loading
          ? <div className="bottom-grid"><Skeleton style={{ height: 220 }} /><Skeleton style={{ height: 220 }} /></div>
          : data && (
            <div className="bottom-grid au3">

              {/* Top referers */}
              <div className="panel">
                <div className="panel-title">
                  <Link2 size={15} color="#7c3aed" />
                  Top referers
                </div>
                {data.top_referers.length === 0
                  ? <div className="empty-state"><p>No referer data yet</p></div>
                  : data.top_referers.slice(0, 5).map((r, i) => (
                    <div key={i} className="ref-item">
                      <div className="ref-row">
                        <span className="ref-name">{r.referer || "Direct"}</span>
                        <span className="ref-count">{r.count}</span>
                      </div>
                      <div className="ref-track">
                        <div className="ref-fill" style={{ width: `${(r.count / maxRef) * 100}%` }} />
                      </div>
                    </div>
                  ))
                }
              </div>

              {/* Recent clicks */}
              <div className="panel">
                <div className="panel-title">
                  <Globe size={15} color="#22d3ee" />
                  Recent clicks
                </div>
                {data.recent_clicks.length === 0
                  ? <div className="empty-state"><p>No clicks yet</p></div>
                  : data.recent_clicks.slice(0, 6).map((c, i) => (
                    <div key={i} className="click-row">
                      <span className="click-time">
                        {new Date(c.clicked_at).toLocaleString("en-US", {
                          month: "short", day: "numeric",
                          hour: "2-digit", minute: "2-digit"
                        })}
                      </span>
                      {c.country && <span className="click-country">{c.country}</span>}
                    </div>
                  ))
                }
              </div>

            </div>
          )}
      </div>
    </>
  );
}

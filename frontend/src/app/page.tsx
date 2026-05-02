"use client";

import { useState } from "react";
import {
  Link2, Zap, BarChart2, Shield, Copy, Check,
  ExternalLink, ChevronDown, Sparkles, ArrowRight
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { ShortenResponse } from "@/types";

export default function HomePage() {
  const [url, setUrl]               = useState("");
  const [alias, setAlias]           = useState("");
  const [expiryDays, setExpiryDays] = useState<string>("");
  const [showAdv, setShowAdv]       = useState(false);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [result, setResult]         = useState<ShortenResponse | null>(null);
  const [copied, setCopied]         = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const data = await api.shorten({
        url: url.trim(),
        ...(alias.trim()  && { custom_alias: alias.trim() }),
        ...(expiryDays    && { expiry_days: parseInt(expiryDays) }),
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function copyToClipboard() {
    if (!result) return;
    await navigator.clipboard.writeText(result.short_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function reset() {
    setResult(null); setUrl(""); setAlias(""); setExpiryDays(""); setError(null);
  }

  return (
    <>
      {/* ── Nav ── */}
      <nav className="nav">
        <div className="nav-inner">
          <a href="/" className="nav-logo">
            <div className="nav-logo-icon">
              <Zap size={16} color="white" />
            </div>
            <span className="nav-logo-text">ShortURL</span>
          </a>
          <a href="/analytics" className="nav-link">
            <BarChart2 size={15} />
            Analytics
          </a>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="hero">

        {/* Live badge */}
        <div className="badge-live au">
          <span className="dot" />
          Sub-100ms redirects · Live
        </div>

        {/* Heading */}
        <h1 className="hero-title au1">
          Shorten.{" "}
          <span className="accent">Analyze.</span>
          <br />
          Share anything.
        </h1>

        <p className="hero-sub au2">
          Production-grade URL shortener with real-time click analytics,
          custom aliases, and expiry controls.
        </p>

        {/* ── Main card ── */}
        <div className="main-card au3">
          {!result ? (
            <form onSubmit={handleSubmit}>

              {/* URL row */}
              <div className="input-wrap">
                <div className="url-input-box">
                  <Link2 className="icon" size={16} />
                  <input
                    type="url"
                    className="url-input"
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    placeholder="Paste your long URL here…"
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-violet"
                  disabled={loading || !url.trim()}
                >
                  {loading ? (
                    <><span className="spinner" />Shortening…</>
                  ) : (
                    <><Sparkles size={15} />Shorten</>
                  )}
                </button>
              </div>

              {/* Advanced toggle */}
              <button
                type="button"
                className={`adv-toggle${showAdv ? " open" : ""}`}
                onClick={() => setShowAdv(v => !v)}
              >
                <ChevronDown className="chevron" size={14} />
                Advanced options
              </button>

              {showAdv && (
                <div className="adv-fields">
                  <div>
                    <label className="field-label">Custom alias</label>
                    <input
                      type="text"
                      className="field-input"
                      value={alias}
                      onChange={e => setAlias(e.target.value)}
                      placeholder="my-custom-link"
                      pattern="[a-zA-Z0-9_-]+"
                      maxLength={32}
                    />
                  </div>
                  <div>
                    <label className="field-label">Expires after (days)</label>
                    <input
                      type="number"
                      className="field-input"
                      value={expiryDays}
                      onChange={e => setExpiryDays(e.target.value)}
                      placeholder="365"
                      min={1} max={3650}
                    />
                  </div>
                </div>
              )}

              {error && (
                <div className="error-box">
                  <Shield size={15} style={{ flexShrink: 0, marginTop: 1 }} />
                  {error}
                </div>
              )}
            </form>

          ) : (
            /* ── Success ── */
            <div className="success-wrap">
              <div className="success-header">
                <div className="success-check">
                  <Check size={15} color="#10b981" />
                </div>
                <div>
                  <p style={{ fontSize: 14, fontWeight: 600, color: "#10b981" }}>
                    Link created successfully!
                  </p>
                  <p style={{ fontSize: 11, color: "var(--txt-3)", marginTop: 2 }}>
                    Ready to share
                  </p>
                </div>
              </div>

              {/* Short URL box */}
              <div className="url-result-box">
                <p className="url-result-label">Your short URL</p>
                <div className="url-result-row">
                  <span className="url-short">{result.short_url}</span>
                  <button
                    onClick={copyToClipboard}
                    className={`icon-btn${copied ? " copied" : ""}`}
                    title="Copy"
                  >
                    {copied
                      ? <Check size={15} />
                      : <Copy size={15} />}
                  </button>
                  <a
                    href={result.short_url}
                    target="_blank" rel="noopener noreferrer"
                    className="icon-btn"
                    title="Open"
                  >
                    <ExternalLink size={15} />
                  </a>
                </div>
              </div>

              {/* Meta chips */}
              <div className="meta-row">
                <div className="meta-chip" style={{ flex: 2 }}>
                  <p className="meta-chip-label">Original URL</p>
                  <p className="meta-chip-val">{result.original_url}</p>
                </div>
                {result.expires_at && (
                  <div className="meta-chip meta-chip-amber">
                    <p className="meta-chip-label">Expires</p>
                    <p className="meta-chip-val">
                      {new Date(result.expires_at).toLocaleDateString("en-US", {
                        year: "numeric", month: "short", day: "numeric"
                      })}
                    </p>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="action-row">
                <a
                  href={`/analytics/${result.short_code}`}
                  className="action-btn action-btn-ghost"
                >
                  <BarChart2 size={15} />
                  View analytics
                </a>
                <button onClick={reset} className="action-btn action-btn-primary">
                  <ArrowRight size={15} />
                  Shorten another
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Feature pills */}
        <div className="pills au4">
          {[
            { icon: Zap,      label: "Sub-100ms redirects" },
            { icon: BarChart2, label: "Click analytics" },
            { icon: Shield,   label: "Rate limited" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="pill">
              <Icon size={13} />
              {label}
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

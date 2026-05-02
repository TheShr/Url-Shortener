export interface ShortenRequest {
  url: string;
  custom_alias?: string;
  expiry_days?: number;
}

export interface ShortenResponse {
  short_code: string;
  short_url: string;
  original_url: string;
  expires_at: string | null;
  created_at: string;
}

export interface ClickDataPoint {
  date: string;
  clicks: number;
}

export interface AnalyticsSummary {
  short_code: string;
  original_url: string;
  total_clicks: number;
  created_at: string;
  expires_at: string | null;
  is_active: boolean;
}

export interface AnalyticsDetail {
  summary: AnalyticsSummary;
  clicks_by_day: ClickDataPoint[];
  top_referers: Array<{ referer: string; count: number }>;
  recent_clicks: Array<{
    clicked_at: string;
    ip: string | null;
    referer: string | null;
    country: string | null;
  }>;
}

export interface ApiError {
  detail: string;
}

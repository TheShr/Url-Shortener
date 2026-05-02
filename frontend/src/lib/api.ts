import type { AnalyticsDetail, ShortenRequest, ShortenResponse } from "@/types";

const envBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const baseUrl = envBase.replace(/\/+$/, "");
const API_BASE = baseUrl.endsWith("/api/v1") ? baseUrl : `${baseUrl}/api/v1`;

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail ?? message;
    } catch {}
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

export const api = {
  shorten: (data: ShortenRequest): Promise<ShortenResponse> =>
    request<ShortenResponse>("/shorten", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getAnalytics: (shortCode: string): Promise<AnalyticsDetail> =>
    request<AnalyticsDetail>(`/analytics/${shortCode}`),
};

export { ApiError };

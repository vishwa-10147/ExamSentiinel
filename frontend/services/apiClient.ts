export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "proctor" | "reviewer" | "candidate";
  institution_id?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
  services: {
    database: { status: string; latency_ms?: number; error?: string };
    redis: { status: string; latency_ms?: number; error?: string };
  };
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "https://examsentinel-backend.onrender.com" : "http://localhost:8000");

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("refresh_token");
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
  }

  public clearTokens(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_profile");
  }

  public async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    const token = this.getAccessToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Do not set Content-Type to application/json for FormData
    if (!(options.body instanceof FormData) && !headers["Content-Type"] && options.method !== "GET") {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle token expiration & automatic refresh
    if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        // Retry the request with new token
        headers["Authorization"] = `Bearer ${this.getAccessToken()}`;
        const retryResponse = await fetch(url, {
          ...options,
          headers,
        });
        if (!retryResponse.ok) {
          const errorData = await retryResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || `Request failed with status ${retryResponse.status}`);
        }
        return retryResponse.json();
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMsg = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMsg = errorData.detail.map((e: any) => e.msg || 'Validation Error').join(', ');
        }
      }
      throw new Error(errorMsg);
    }

    // Return empty object for 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  private async tryRefreshToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      this.clearTokens();
      return false;
    }

    try {
      const refreshUrl = `${this.baseUrl}/api/auth/refresh`;
      const res = await fetch(refreshUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) {
        this.clearTokens();
        return false;
      }

      const data: TokenResponse = await res.json();
      this.setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  // REST method helpers
  public get<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: "GET", headers });
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? (data instanceof FormData ? data : JSON.stringify(data)) : undefined,
    });
  }

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: formData,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? (data instanceof FormData ? data : JSON.stringify(data)) : undefined,
    });
  }

  public delete<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE", headers });
  }

  // Auth specific methods
  public async login(email: string, password: string): Promise<any> {
    const data = await this.post<any>("/api/auth/login", { email, password });
    if (data.requires_2fa) {
      return data;
    }
    this.setTokens(data.access_token, data.refresh_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("user_profile", JSON.stringify(data.user));
    }
    return data;
  }

  public async verifyOTP(userId: string, otpCode: string): Promise<TokenResponse> {
    const data = await this.post<TokenResponse>("/api/auth/verify-otp", { user_id: userId, otp_code: otpCode });
    this.setTokens(data.access_token, data.refresh_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("user_profile", JSON.stringify(data.user));
    }
    return data;
  }

  public async register(payload: {
    email: string;
    password: string;
    full_name: string;
    role?: string;
    institution_id?: string;
  }): Promise<UserProfile> {
    return this.post<UserProfile>("/api/auth/register", payload);
  }

  public async getMe(): Promise<UserProfile> {
    return this.get<UserProfile>("/api/auth/me");
  }

  public async getHealth(): Promise<HealthCheckResponse> {
    return this.get<HealthCheckResponse>("/api/health");
  }

  // Appeals methods
  public async getAppeals(status?: string): Promise<AppealItem[]> {
    const query = status && status !== "ALL" ? `?status_filter=${encodeURIComponent(status)}` : "";
    return this.get<AppealItem[]>(`/api/compliance/appeals${query}`);
  }

  public async getAppeal(id: string): Promise<AppealDetail> {
    return this.get<AppealDetail>(`/api/compliance/appeals/${id}`);
  }

  public async resolveAppeal(id: string, payload: { status: string; resolution: string }): Promise<any> {
    return this.post<any>(`/api/compliance/appeals/${id}/resolve`, payload);
  }
}

export interface TelemetryEvent {
  id: string;
  time: string;
  type: "CRITICAL" | "WARNING" | "INFO";
  source: string;
  description: string;
  sensorDetail?: string;
  frameTimestampSec?: number;
}

export interface AppealItem {
  id: string;
  case_id: string;
  candidate_id?: string;
  candidate_name: string;
  candidate_email?: string;
  exam_name: string;
  original_finding: string;
  risk_score: number;
  appeal_date: string;
  status: "PENDING" | "UNDER_REVIEW" | "RESOLVED" | "OVERTURNED" | "UPHELD" | string;
  reason?: string;
  resolution?: string | null;
  original_reviewer_name?: string;
}

export interface AppealDetail extends AppealItem {
  session_id?: string | null;
  original_reviewer_id?: string | null;
  proctor_notes?: string;
  timeline?: TelemetryEvent[];
  videoSnapshotUrl?: string;
  telemetryMetrics?: {
    audioSpikes: number;
    gazeDeviations: number;
    headRotations: number;
    tabSwitches: number;
    confidence: number;
  };
}

export const apiClient = new ApiClient(API_BASE_URL);


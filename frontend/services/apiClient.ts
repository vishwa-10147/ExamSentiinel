export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "proctor" | "reviewer" | "candidate";
  institution_id?: string | null;
  department?: string | null;
  section?: string | null;
  batch_year?: number | null;
  phone?: string | null;
  roll_no?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  /** Always null for the browser: tokens live in httpOnly cookies the page cannot read. */
  access_token: string | null;
  refresh_token: string | null;
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

  // Sessions live in httpOnly cookies set by the API (see backend app/core/auth_cookies.py):
  // page scripts never see the tokens. Every request sends the cookies, asks for cookie mode,
  // and carries X-Requested-With, which the API requires for cookie-authenticated writes (CSRF).
  private static readonly SESSION_HEADERS = { "X-Auth-Mode": "cookie", "X-Requested-With": "ExamSentinel" };

  private storeProfile(user: UserProfile): void {
    if (typeof window === "undefined") return;
    localStorage.setItem("user_profile", JSON.stringify(user));
  }

  /** Forget the local session state (the cookies themselves are cleared by POST /api/auth/logout). */
  public clearTokens(): void {
    if (typeof window === "undefined") return;
    // Tokens from older versions, which kept them in localStorage.
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
      ...ApiClient.SESSION_HEADERS,
      ...(options.headers as Record<string, string>),
    };

    // Do not set Content-Type to application/json for FormData
    if (!(options.body instanceof FormData) && !headers["Content-Type"] && options.method !== "GET") {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    // Handle token expiration & single-session displacement
    if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
      const cloneData = await response.clone().json().catch(() => ({}));
      if (typeof cloneData?.detail === "string" && cloneData.detail.includes("Logged in from another browser")) {
        this.clearTokens();
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("user_profile");
          window.location.href = "/auth/login?reason=session_terminated";
        }
        throw new Error(cloneData.detail);
      }

      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        // Retry the request; the refreshed session cookie is sent automatically.
        const retryResponse = await fetch(url, {
          ...options,
          headers,
          credentials: "include",
        });
        if (!retryResponse.ok) {
          const errorData = await retryResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || `Request failed with status ${retryResponse.status}`);
        }
        return retryResponse.json();
      } else if (typeof window !== "undefined") {
        this.clearTokens();
        window.localStorage.removeItem("user_profile");
        window.location.href = "/auth/login";
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
    try {
      // The refresh token is an httpOnly cookie scoped to /api/auth; the API reads it from there.
      const res = await fetch(`${this.baseUrl}/api/auth/refresh`, {
        method: "POST",
        headers: ApiClient.SESSION_HEADERS,
        credentials: "include",
      });

      if (!res.ok) {
        this.clearTokens();
        return false;
      }

      const data: TokenResponse = await res.json();
      this.storeProfile(data.user);
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
    this.storeProfile(data.user);
    return data;
  }

  /** End the session on the server (revokes refresh tokens, clears the cookies), then locally. */
  public async logout(): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/api/auth/logout`, {
        method: "POST",
        headers: ApiClient.SESSION_HEADERS,
        credentials: "include",
      });
    } catch {
      /* offline or already signed out: still clear local state */
    }
    this.clearTokens();
  }

  /** Configured single sign-on providers (empty when SSO isn't set up). */
  public getSsoProviders(): Promise<{ id: string; name: string }[]> {
    return this.get<{ id: string; name: string }[]>("/api/auth/sso/providers");
  }

  /** Top-level navigation target that starts the provider's sign-in. */
  public ssoLoginUrl(providerId: string): string {
    return `${this.baseUrl}/api/auth/sso/${encodeURIComponent(providerId)}/login`;
  }

  /** Exchange the single-use ticket from the SSO redirect for a session. */
  public async completeSsoLogin(ticket: string): Promise<TokenResponse> {
    const data = await this.post<TokenResponse>("/api/auth/sso/exchange", { ticket });
    this.storeProfile(data.user);
    return data;
  }

  public async verifyOTP(userId: string, otpCode: string): Promise<TokenResponse> {
    const data = await this.post<TokenResponse>("/api/auth/verify-otp", { user_id: userId, otp_code: otpCode });
    this.storeProfile(data.user);
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


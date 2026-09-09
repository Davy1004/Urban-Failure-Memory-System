/**
 * The API client, and the response types it returns.
 *
 * The types mirror `app/schemas/dashboard.py`. Several fields there exist to
 * stop a number being read as more than it is — `oracle_at_k`, `random_at_k`,
 * `caveats`, `ground_truth_available`, `retraction` — and they are **required**
 * here, not optional, so a screen that forgets to render one fails to compile
 * rather than shipping a figure without its context.
 */

/**
 * Where the API is.
 *
 * Empty by default, which makes every request same-origin: in development the
 * Vite proxy forwards `/api` to :8000, and a deploy that puts both behind one
 * host (a Vercel rewrite) needs no configuration at all. Set
 * `VITE_API_BASE_URL` at **build** time — Vite inlines it, so it is baked into
 * the bundle and cannot be changed afterwards without rebuilding — to point a
 * separately-hosted frontend at a separately-hosted API:
 *
 *     VITE_API_BASE_URL=https://ufms-api.example.com npm run build
 *
 * A cross-origin value makes CORS load-bearing: the API must then name that
 * exact frontend origin in `CORS_ORIGINS`, or every screen renders empty
 * against a backend that is working perfectly.
 */
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const BASE = `${API_ORIGIN}/api/v1`;

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/**
 * The token lives in `sessionStorage`, and nowhere else.
 *
 * **Never `localStorage`.** The rule this has to satisfy is that a bearer
 * credential must not survive a tab close on a shared municipal machine.
 * `sessionStorage` satisfies it exactly: the browser clears it when the tab
 * closes, and it is not shared with other tabs. `localStorage` would persist
 * until something explicitly deleted it, which is the case the rule exists to
 * prevent.
 *
 * It was in memory only until 9 Sep 2026. That was tighter than the rule
 * required rather than more correct: it also destroyed the token on F5 and on
 * any deep link, so an officer paging through four screens was one accidental
 * refresh from signing in again. See `DECISIONS.md`.
 *
 * The module variable is the read path, so a request never touches storage and
 * the app still works where storage throws — private mode, or a browser
 * configured to block site data.
 */
const TOKEN_KEY = "ufms.access_token";

function readStoredToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

let accessToken: string | null = readStoredToken();

export function setToken(token: string | null): void {
  accessToken = token;
  try {
    if (token === null) sessionStorage.removeItem(TOKEN_KEY);
    else sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* Storage unavailable. The token stays in memory for this page load, which
       degrades to the pre-9-Sep behaviour rather than to a broken sign-in. */
  }
}

export function getToken(): string | null {
  return accessToken;
}

type ErrorBody = { error?: { message?: string; code?: string } };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    let code: string | undefined;
    try {
      const body = (await res.json()) as ErrorBody;
      if (body.error?.message) message = body.error.message;
      code = body.error?.code;
    } catch {
      /* a non-JSON error body is still an error; keep the status message */
    }
    throw new ApiError(res.status, message, code);
  }
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export type Role = "admin" | "officer";

export interface CurrentUser {
  user_id: number;
  name: string;
  email: string;
  role: Role;
  department: string | null;
  city_id: number | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: CurrentUser;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function me(): Promise<CurrentUser> {
  return request<CurrentUser>("/auth/me");
}

// ---------------------------------------------------------------------------
// Screen 1 — the ward index
// ---------------------------------------------------------------------------

export interface IndexPoint {
  period: string;
  period_start: string;
  event_days: number;
  total_complaints: number;
  city_share: number;
  expected_event_days: number;
  rel_index: number;
}

export interface IndexSeries {
  location_id: number;
  ward: string;
  ward_no: string | null;
  zone: string | null;
  smoothing: number;
  mean_rel_index: number;
  quarters: number;
  points: IndexPoint[];
  definition: string;
}

export async function fetchIndex(ward: string): Promise<IndexSeries> {
  return request<IndexSeries>(`/index/${encodeURIComponent(ward)}`);
}

export interface CityIndexWard {
  location_id: number;
  ward: string;
  ward_no: string | null;
  zone: string | null;
  event_days: number;
  total_complaints: number;
  expected_event_days: number;
  rel_index: number;
}

export interface CityIndexSnapshot {
  city: string;
  period: string;
  period_start: string;
  city_share: number;
  available_periods: string[];
  wards: CityIndexWard[];
  definition: string;
}

/** Every ward for one quarter — one request, because a map assembled from 198
 *  of them renders half-shaded when one fails. */
export async function fetchCityIndex(period?: string): Promise<CityIndexSnapshot> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return request<CityIndexSnapshot>(`/index${qs}`);
}

// ---------------------------------------------------------------------------
// Screen 2 — the standing watchlist
// ---------------------------------------------------------------------------

export interface WatchlistItem {
  rank_position: number;
  location_id: number;
  ward: string;
  ward_no: string | null;
  zone: string | null;
  prior_events: number;
  test_events: number | null;
}

export interface WatchlistContext {
  precision_at_k: number | null;
  oracle_at_k: number | null;
  random_at_k: number | null;
  share_of_ceiling: number | null;
  test_rain_days: number | null;
  test_events: number | null;
  test_start: string | null;
  test_end: string | null;
  rain_threshold_mm: number | null;
  weather_model: string | null;
  reading: string;
}

export interface Watchlist {
  snapshot_id: number;
  city: string;
  failure_type: string;
  as_of_date: string;
  k: number;
  train_start: string;
  computed_at: string;
  context: WatchlistContext;
  items: WatchlistItem[];
}

export async function fetchWatchlist(): Promise<Watchlist> {
  return request<Watchlist>("/watchlist");
}

// ---------------------------------------------------------------------------
// Screen 3 — the emerging watch
// ---------------------------------------------------------------------------

export interface EmergingItem {
  rank_position: number;
  location_id: number;
  ward: string;
  ward_no: string | null;
  zone: string | null;
  is_flagged: boolean;
  on_register: boolean;
  event_days: number;
  half1_slope: number;
  half1_p: number;
  half1_level: number;
  half2_level: number;
  level_delta: number;
  full_slope: number;
  full_p: number;
}

export interface EmergingEvidence {
  flagged_n: number;
  flagged_half1_level: number;
  flagged_half2_level: number;
  all_half2_level: number;
  flagged_above_norm: number;
  p_vs_other_wards: number;
  p_vs_own_first_half: number;
}

export interface Emerging {
  city: string;
  as_of_date: string;
  window_start: string;
  eligible_wards: number;
  min_event_days: number;
  flagged: number;
  label: string;
  ground_truth_available: boolean;
  evidence: EmergingEvidence;
  items: EmergingItem[];
  caveats: string[];
}

export async function fetchEmerging(): Promise<Emerging> {
  return request<Emerging>("/emerging");
}

// ---------------------------------------------------------------------------
// Screen 4 — allocation
// ---------------------------------------------------------------------------

export interface Correlation {
  rho: number;
  p: number;
}

export interface AllocationItem {
  location_id: number;
  ward: string;
  ward_no: string | null;
  zone: string | null;
  is_treated: boolean;
  drainage_works: number;
  drainage_spend: number;
  ward_area_sqkm: number | null;
  spend_per_sqkm: number | null;
  event_days_total: number;
  pre_index: number;
  post_index: number;
  delta_index: number;
}

export interface AllocationFinding {
  n_wards: number;
  n_treated: number;
  n_untreated: number;
  total_spend: number;
  median_spend_treated: number;
  spend_vs_area: Correlation;
  spend_vs_pre_index: Correlation;
  spend_vs_absolute_events: Correlation;
  area_vs_absolute_events: Correlation;
  spend_vs_events_controlling_area: Correlation;
}

export interface Allocation {
  city: string;
  window_start: string;
  window_end: string;
  finding: AllocationFinding;
  headline: string;
  retraction: string;
  items: AllocationItem[];
}

export async function fetchAllocation(): Promise<Allocation> {
  return request<Allocation>("/allocation");
}

// ---------------------------------------------------------------------------
// Locations — for the ward picker and the choropleth join
// ---------------------------------------------------------------------------

export interface Location {
  location_id: number;
  area_name: string;
  ward_no: string | null;
  zone: string | null;
  latitude: number | null;
  longitude: number | null;
  geom_level: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchWards(): Promise<Location[]> {
  const page = await request<Page<Location>>("/locations?limit=500");
  return page.items.filter((l) => l.geom_level === "ward");
}

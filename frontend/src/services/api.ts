const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

type TokenPair = { access: string; refresh: string };
const AUTH_STORAGE_KEY = "waytogether.auth";

function parseTokenPair(raw: string | null): TokenPair | null {
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (
      value &&
      typeof value === "object" &&
      typeof (value as TokenPair).access === "string" &&
      typeof (value as TokenPair).refresh === "string"
    ) {
      return { access: (value as TokenPair).access, refresh: (value as TokenPair).refresh };
    }
  } catch {
    // Ignore malformed or unavailable browser storage.
  }
  return null;
}

function readStoredTokens(): TokenPair | null {
  try {
    const persistent = parseTokenPair(window.localStorage.getItem(AUTH_STORAGE_KEY));
    if (persistent) return persistent;
  } catch {
    // localStorage may be blocked by browser privacy settings.
  }

  // Migrate sessions created by older releases from tab-scoped sessionStorage.
  try {
    const legacy = parseTokenPair(window.sessionStorage.getItem(AUTH_STORAGE_KEY));
    if (legacy) {
      try {
        window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(legacy));
        window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
      } catch {
        // Continue using the legacy tab-scoped copy if persistent storage is unavailable.
      }
      return legacy;
    }
  } catch {
    // Storage can be unavailable in private or restricted browser contexts.
  }
  return null;
}

export type AuthUser = {
  id: number;
  email: string;
  phone: string | null;
  first_name: string;
  last_name: string;
  display_name: string;
  role: "passenger" | "driver" | "admin";
  is_email_verified: boolean;
};

const storedTokens = readStoredTokens();
let accessToken: string | null = storedTokens?.access ?? null;
let refreshToken: string | null = storedTokens?.refresh ?? null;
let refreshInFlight: Promise<boolean> | null = null;

function persistAuthTokens() {
  if (accessToken && refreshToken) {
    const serialized = JSON.stringify({ access: accessToken, refresh: refreshToken });
    try {
      window.localStorage.setItem(AUTH_STORAGE_KEY, serialized);
      try {
        window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
      } catch {
        // The persistent copy is already saved.
      }
      return;
    } catch {
      // Fall back to session storage when persistent storage is blocked.
    }
    try {
      window.sessionStorage.setItem(AUTH_STORAGE_KEY, serialized);
    } catch {
      // Keep the in-memory session usable if browser storage is unavailable.
    }
    return;
  }

  try {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // Ignore unavailable storage.
  }
  try {
    window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // Ignore unavailable storage.
  }
}

export function setAuthTokens(tokens: TokenPair) {
  accessToken = tokens.access;
  refreshToken = tokens.refresh;
  persistAuthTokens();
}

export function clearAuthTokens() {
  accessToken = null;
  refreshToken = null;
  persistAuthTokens();
}

export function hasAuthSession(): boolean {
  // The refresh token represents a restorable session even when the access token
  // has expired or the API is temporarily unavailable.
  return Boolean(refreshToken);
}

export async function logoutCurrentSession(): Promise<void> {
  const tokenToRevoke = refreshToken;
  clearAuthTokens();

  // Local sign-out is immediate even when the network is unavailable.
  if (!tokenToRevoke) return;
  try {
    await fetch(`${API_BASE_URL}/auth/token/blacklist/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: tokenToRevoke }),
    });
  } catch {
    // The browser session is cleared; an expired refresh token will also become unusable.
  }
}

function collectApiErrors(value: unknown, field = ""): string[] {
  if (typeof value === "string") return [field ? `${field}: ${value}` : value];
  if (Array.isArray(value)) return value.flatMap(item => collectApiErrors(item, field));
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nested]) => {
      const label = key === "detail" || key === "non_field_errors"
        ? field
        : key.replaceAll("_", " ");
      return collectApiErrors(nested, label);
    });
  }
  return [];
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages = collectApiErrors(payload);
    const detail = [...new Set(messages)].filter(Boolean).join(" ");
    throw new Error(detail || `Request failed with status ${response.status}.`);
  }
  return payload as T;
}

async function performTokenRefresh(): Promise<boolean> {
  const tokenBeingRefreshed = refreshToken;
  if (!tokenBeingRefreshed) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: tokenBeingRefreshed }),
    });

    if (!response.ok) {
      // Only a definitive invalid/expired refresh response ends the saved session.
      // Network errors, rate limits and server errors must not sign the user out.
      if (
        (response.status === 400 || response.status === 401) &&
        refreshToken === tokenBeingRefreshed
      ) {
        clearAuthTokens();
      }
      return false;
    }

    const payload = await response.json() as { access?: string; refresh?: string };
    if (!payload.access) return false;

    // Do not let a late refresh response overwrite a newer login or an explicit logout.
    if (refreshToken !== tokenBeingRefreshed) {
      return Boolean(accessToken && refreshToken);
    }

    accessToken = payload.access;
    if (payload.refresh) refreshToken = payload.refresh;
    persistAuthTokens();
    return true;
  } catch {
    // Keep the refresh token so the next request can retry after a temporary outage.
    return false;
  }
}

function refreshAccessToken(): Promise<boolean> {
  // SimpleJWT rotates and blacklists refresh tokens. Coalesce simultaneous 401s
  // into one refresh request so parallel dashboard requests cannot invalidate
  // each other's refresh token.
  if (!refreshInFlight) {
    refreshInFlight = performTokenRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function sessionUnavailableError(): Error {
  return new Error(
    hasAuthSession()
      ? "WayTogether could not reconnect right now. Your saved sign-in is still here; check your connection and try again."
      : "Your sign-in session has expired. Please sign in again."
  );
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  if (authenticated && !accessToken) {
    const refreshed = await refreshAccessToken();
    if (!refreshed || !accessToken) throw sessionUnavailableError();
  }

  if (authenticated && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  let response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (authenticated && response.status === 401) {
    if (await refreshAccessToken()) {
      headers.set("Authorization", `Bearer ${accessToken}`);
      response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
    }
    if (response.status === 401) {
      // The retried request was rejected too, or refresh was definitively invalid.
      // Preserve the session only when refresh failed for a transient reason.
      if (!hasAuthSession()) throw sessionUnavailableError();
      throw sessionUnavailableError();
    }
  }
  return parseResponse<T>(response);
}

export async function getCurrentUser() {
  return apiRequest<AuthUser>("/auth/me/", {}, true);
}


export async function downloadPrivateFile(path: string, filename: string): Promise<void> {
  if (!accessToken && !(await refreshAccessToken())) throw sessionUnavailableError();
  if (!accessToken) throw sessionUnavailableError();

  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  let response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (response.status === 401) {
    if (await refreshAccessToken() && accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
      response = await fetch(`${API_BASE_URL}${path}`, { headers });
    }
  }
  if (!response.ok) {
    if (response.status === 401 && !hasAuthSession()) throw sessionUnavailableError();
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || (response.status === 401
      ? "WayTogether could not reconnect right now. Your saved sign-in is still here; try again."
      : "The document could not be downloaded."));
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

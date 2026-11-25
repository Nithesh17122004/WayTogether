const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

type TokenPair = { access: string; refresh: string };
export type AuthUser = {
  id: number;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  display_name: string;
  role: "passenger" | "driver" | "admin";
  is_email_verified: boolean;
  is_phone_verified: boolean;
};

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setAuthTokens(tokens: TokenPair) {
  accessToken = tokens.access;
  refreshToken = tokens.refresh;
}

export function clearAuthTokens() {
  accessToken = null;
  refreshToken = null;
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

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail
      || payload.verification_required
      || Object.values(payload).flat().filter(Boolean).join(" ")
      || `Request failed with status ${response.status}.`;
    throw new Error(String(detail));
  }
  return payload as T;
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    if (!response.ok) {
      clearAuthTokens();
      return false;
    }
    const payload = await response.json() as { access: string; refresh?: string };
    accessToken = payload.access;
    if (payload.refresh) refreshToken = payload.refresh;
    return true;
  } catch {
    clearAuthTokens();
    return false;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (authenticated && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  let response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (authenticated && response.status === 401 && await refreshAccessToken()) {
    headers.set("Authorization", `Bearer ${accessToken}`);
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  }
  return parseResponse<T>(response);
}

export async function getCurrentUser() {
  return apiRequest<AuthUser>("/auth/me/", {}, true);
}


export async function downloadPrivateFile(path: string, filename: string): Promise<void> {
  if (!accessToken) throw new Error("Sign in again to download this private document.");
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  let response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (response.status === 401 && await refreshAccessToken()) {
    headers.set("Authorization", `Bearer ${accessToken}`);
    response = await fetch(`${API_BASE_URL}${path}`, { headers });
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "The document could not be downloaded.");
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

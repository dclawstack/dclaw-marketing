/**
 * Auth library — JWT token storage + login/logout helpers.
 *
 * Token lives in localStorage. Every API call goes through the
 * fetch wrapper in api.ts which attaches the Bearer header.
 *
 * MVP-only: localStorage means the token isn't readable by Next.js
 * middleware (edge runtime). We rely on client-side guards + backend
 * 401s. Move to httpOnly cookies post-MVP for stronger security.
 */

const TOKEN_KEY = "dclaw_jwt";
const USER_KEY = "dclaw_user";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  password_reset_required: boolean;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setUser(user: AuthUser): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export async function login(
  email: string,
  password: string,
): Promise<AuthUser> {
  // FastAPI-Users JWT auth uses application/x-www-form-urlencoded with
  // OAuth2 form fields (username, password).
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const res = await fetch(`${apiBase()}/api/v1/auth/jwt/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Login failed (${res.status}): ${detail}`);
  }

  const data = (await res.json()) as { access_token: string; token_type: string };
  setToken(data.access_token);

  // Fetch the user record so we know is_superuser + password_reset_required
  const meRes = await fetch(`${apiBase()}/api/v1/me`, {
    headers: { Authorization: `Bearer ${data.access_token}` },
  });
  if (!meRes.ok) {
    clearToken();
    throw new Error(`Could not fetch user profile after login (${meRes.status})`);
  }
  const user = (await meRes.json()) as AuthUser;
  setUser(user);
  return user;
}

export async function logout(): Promise<void> {
  const token = getToken();
  if (token) {
    // Best-effort: ask the server to invalidate. FastAPI-Users JWT
    // logout is a no-op server-side (stateless tokens) but the
    // endpoint exists for symmetry.
    try {
      await fetch(`${apiBase()}/api/v1/auth/jwt/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      /* ignore network errors during logout */
    }
  }
  clearToken();
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const token = getToken();
  if (!token) throw new Error("Not authenticated.");

  const res = await fetch(`${apiBase()}/api/v1/me/password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Password change failed (${res.status}).`);
  }

  // Refresh the cached user so password_reset_required clears
  const u = getUser();
  if (u) setUser({ ...u, password_reset_required: false });
}

function apiBase(): string {
  // Public env var baked at build time
  return process.env.NEXT_PUBLIC_API_URL || "";
}

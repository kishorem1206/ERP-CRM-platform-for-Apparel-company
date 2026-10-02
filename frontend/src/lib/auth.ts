// Reads the current user's id out of the already-trusted access token stored
// by the login flow (src/lib/api.ts) — a lightweight payload decode, not a
// signature check, since the token is only ever used here to pre-fill "my"
// filters client-side.
export function getCurrentUserId(): string | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("access_token");
  if (!token) return null;
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return (JSON.parse(json).sub as string) ?? null;
  } catch {
    return null;
  }
}

// This app's real error envelope is {"error": "..."} or {"error": {"message": "..."}}
// (see backend/app/main.py's exception handlers), not FastAPI's default
// {"detail": ...} — reading only `.detail` silently swallows every
// business-rule error.
export function parseApiError(e: unknown, fallback: string): string {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  const err = data.error;
  if (typeof err === "string") return err;
  if (err && typeof (err as { message?: string }).message === "string")
    return (err as { message: string }).message;
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0)
    return (detail as Array<{ msg: string }>)[0]?.msg ?? fallback;
  return fallback;
}

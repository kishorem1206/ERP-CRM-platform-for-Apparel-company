import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Refresh tokens rotate on use, so concurrent refreshes would revoke each other.
// All callers share one in-flight refresh.
let refreshing: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
  if (!refreshing) {
    refreshing = axios
      .post("/api/v1/auth/refresh", {}, { withCredentials: true })
      .then(({ data }) => {
        const token: string = data.data?.access_token ?? data.access_token;
        localStorage.setItem("access_token", token);
        return token;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

// 401 = session ended: refresh, or send to login.
// "Permission required" 403 = the user lacks access: refresh once in case the
// token is stale, but never log them out. The page shows the error instead.
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean };
    const status = error.response?.status;
    const errMsg: string =
      (error.response?.data as Record<string, unknown> | undefined)
        ?.error instanceof Object
        ? ((error.response?.data as Record<string, { message?: string }>)?.error?.message ?? "")
        : String((error.response?.data as Record<string, unknown> | undefined)?.error ?? "");
    const isStalePermission =
      status === 403 && errMsg.startsWith("Permission required:");

    if ((status === 401 || isStalePermission) && original && !original._retry) {
      original._retry = true;
      try {
        const token = await refreshAccessToken();
        original.headers!.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        if (status === 401) {
          localStorage.removeItem("access_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export { api };
export default api;

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

// Handle 401 and stale-permission 403 — try refresh, then redirect to login
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

    if ((status === 401 || isStalePermission) && !original._retry) {
      original._retry = true;
      try {
        const { data } = await axios.post("/api/v1/auth/refresh", {}, { withCredentials: true });
        const token = data.data?.access_token ?? data.access_token;
        localStorage.setItem("access_token", token);
        original.headers!.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export { api };
export default api;

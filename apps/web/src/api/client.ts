export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const r = await fetch(`/api/v1${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  if (r.status === 204) return undefined as T;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? "Please check the details you entered." : "Something went wrong";
    throw new ApiError(r.status, msg);
  }
  return data as T;
}

export type User = { id: number; email: string };

export const api = {
  me: () => request<User>("/auth/me"),
  login: (email: string, password: string) => request<User>("/auth/login", "POST", { email, password }),
  signup: (email: string, password: string) => request<User>("/auth/signup", "POST", { email, password }),
  logout: () => request<void>("/auth/logout", "POST"),
  forgot: (email: string) => request<{ message: string }>("/auth/forgot-password", "POST", { email }),
  reset: (token: string, password: string) => request<{ message: string }>("/auth/reset-password", "POST", { token, password }),
  createRun: (category: string, keywords: string[]) => request<{ id: number; status: string }>("/runs", "POST", { category, keywords }),
};

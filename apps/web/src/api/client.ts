export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

// Called when a signed-in request comes back 401 (session expired or password changed elsewhere).
let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn; };

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const form = body instanceof FormData;   // file uploads: the browser sets the multipart header
  const r = await fetch(`/api/v1${path}`, {
    method,
    headers: body && !form ? { "Content-Type": "application/json" } : undefined,
    body: form ? body : body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  if (r.status === 204) return undefined as T;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
    const d = data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? "Please check the details you entered." : "Something went wrong";
    throw new ApiError(r.status, msg);
  }
  return data as T;
}

export type User = { id: number; email: string };
export type Role = "owner" | "editor" | "viewer";
export type RunStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type Workspace = { id: number; name: string; region: string; role: Role };

export type Run = {
  id: number;
  category: string;
  keywords: string[];
  region: string;
  language: string;
  status: RunStatus;
  ad_count: number;
  spent_usd: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};

export type RunPage = { items: Run[]; total: number; limit: number; offset: number };

export type ViewerInterest = {
  analysed_at: string;
  video_count: number;
  interested_people: number;      // across all videos in the analysis
  top_videos: { title: string; url: string; interested_people: number; interested_comments: number; comments_read: number }[];
};

export type Dashboard = {
  workspace: Workspace;
  stats: {
    total_runs: number;
    active_runs: number;
    completed_runs: number;
    ads_analysed: number;
    spent_this_month_usd: number;
    run_spend_cap_usd: number;
  };
  recent_runs: Run[];
  can_edit: boolean;
  viewer_interest: ViewerInterest | null;   // null until a Laya analysis has read some comments
};

export type YouTubeVideo = {
  video_id: string;
  url: string;
  title: string;
  channel_id: string;
  channel_title: string;
  thumbnail_url: string;
  published_at: string;
  duration_seconds: number;
  views: number;
  likes: number;
  comments: number;
  engagement_rate: number;
};

export type YouTubeOrder = "relevance" | "viewCount" | "date";

export type YouTubeResult = {
  query: string;
  mode: "search" | "lookup";
  videos: YouTubeVideo[];
  summary: { count: number; total_views: number; avg_views: number; avg_engagement_rate: number; top_video_id: string | null };
};

export type YouTubeComment = {
  comment_id: string;
  author: string;
  text: string;
  likes: number;
  replies: number;
  published_at: string;
};

export type YouTubeVideoComments = { video_id: string; comments_disabled: boolean; comments: YouTubeComment[] };

export type Reception = "loved" | "liked" | "mixed" | "disliked" | "no comments";

// One row per ad from Laya reading its top comments (see apps/api/.../pipeline/youtube_insights.py)
export type AdInsight = {
  video_id: string;
  title: string;
  channel: string;
  url: string;
  views: number;
  duration_seconds: number;
  engagement_rate: number;
  million_views: boolean;
  comments_read: number;
  positive_pct: number | null;    // 0-100, weighted by comment likes
  negative_pct: number | null;
  reception: Reception;
  best_comment: string;
  worst_comment: string;
  main_complaint: string;         // topic of the negative comments, "" when none
  age_group_guess: string;        // from what commenters say about themselves, "unknown" if nothing
  age_hints: number;              // how many comments revealed an age
  interested_comments: number;    // top comments showing interest in the product
  interested_people: number | null; // those commenters + the likes on their comments, null with no comments
};

export type AdBrief = Pick<AdInsight, "video_id" | "title" | "views" | "engagement_rate" | "reception">;

export type YouTubeInsights = {
  videos: AdInsight[];
  summary: {
    videos: number;
    million_view_ads: number;
    best_ads: AdBrief[];
    worst_received: AdBrief[];
    top_complaints: Record<string, number>;
    engagement_by_length: Record<string, { ads: number; avg_engagement_rate: number }>;
    age_groups_from_comments: Record<string, number>;
  };
};

// Best vs worst ad from one search (see apps/api/.../pipeline/ad_compare.py)
export type ComparedAd = {
  video: YouTubeVideo;
  views_per_day: number;
  score: number;                  // 0-100, rank within the compared set
  comments_disabled: boolean;
  top_comments: YouTubeComment[];
};

export type AdComparison = {
  best: ComparedAd;
  worst: ComparedAd;
  ads_judged: number;
  ads_too_new: number;            // left out: under 3 days old or under 100 views
  analysis: {
    headline: string;
    best_strengths: string[];
    worst_weaknesses: string[];
    differences: { aspect: string; best: string; worst: string; why_it_matters: string }[];
    recommendations: string[];
    caveat: string;
    analysed_by: "laya" | "rules";  // laya: also read the top comments (free, local model)
    notice: string;                 // why Laya wasn't used, when it was expected
  };
};

// A CSV queued for the model machine (see apps/api/.../api/v1/tasks.py)
export type TaskStatus = "queued" | "processing" | "done" | "failed";

export type AnalysisTask = {
  task_id: string;
  status: TaskStatus;
  task_complete: 0 | 1;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  output: YouTubeInsights | null;   // set once status is "done"
};

export type NewRun ={ category: string; keywords: string[]; language: string };

const ws = (id: number) => `/workspaces/${id}`;

export const api = {
  me: () => request<User>("/auth/me"),
  login: (email: string, password: string) => request<User>("/auth/login", "POST", { email, password }),
  signup: (email: string, password: string) => request<User>("/auth/signup", "POST", { email, password }),
  logout: () => request<void>("/auth/logout", "POST"),
  forgot: (email: string) => request<{ message: string }>("/auth/forgot-password", "POST", { email }),
  reset: (token: string, password: string) => request<{ message: string }>("/auth/reset-password", "POST", { token, password }),

  workspaces: () => request<Workspace[]>("/workspaces"),
  dashboard: (wsId: number) => request<Dashboard>(`${ws(wsId)}/dashboard`),
  runs: (wsId: number, limit = 20, offset = 0) =>
    request<RunPage>(`${ws(wsId)}/runs?limit=${limit}&offset=${offset}`),
  run: (wsId: number, runId: number) => request<Run>(`${ws(wsId)}/runs/${runId}`),
  createRun: (wsId: number, body: NewRun) => request<Run>(`${ws(wsId)}/runs`, "POST", body),
  cancelRun: (wsId: number, runId: number) => request<Run>(`${ws(wsId)}/runs/${runId}/cancel`, "POST"),

  youtubeSearch: (wsId: number, q: string, limit: number, order: YouTubeOrder, language: string) =>
    request<YouTubeResult>(`${ws(wsId)}/youtube/search?${new URLSearchParams({ q, limit: String(limit), order, language })}`),
  youtubeComments: (wsId: number, videoIds: string[], limit = 10) =>
    request<{ videos: YouTubeVideoComments[] }>(`${ws(wsId)}/youtube/comments?${new URLSearchParams({ ids: videoIds.join(","), limit: String(limit) })}`),
  youtubeCompare: (wsId: number, videoIds: string[], q: string) =>
    request<AdComparison>(`${ws(wsId)}/youtube/compare?${new URLSearchParams({ ids: videoIds.join(","), q })}`),
  // Queue the CSV for the model; poll analysisTask until task_complete is 1
  taskInput: (wsId: number, csv: Blob, filename = "youtube.csv") => {
    const form = new FormData();
    form.append("file", csv, filename);
    return request<{ task_id: string; status: TaskStatus; poll_after_seconds: number }>(`${ws(wsId)}/taskinput`, "POST", form);
  },
  analysisTask: (wsId: number, taskId: string) =>
    request<AnalysisTask>(`${ws(wsId)}/taskinput/${encodeURIComponent(taskId)}`),
};

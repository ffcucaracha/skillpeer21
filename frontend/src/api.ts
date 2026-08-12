export type User = {
  id: number;
  login: string;
  display_name: string;
  role: "admin" | "member";
  must_change_password: boolean;
  telegram_username: string | null;
  telegram_visibility: "everyone" | "admin_only";
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type Skill = {
  id: number;
  name: string;
  created_by_user_id: number | null;
};

export type UserSkill = {
  id: number;
  skill_id: number;
  skill_name: string;
  intent: "teach" | "learn";
};

export type Dashboard = {
  summary: {
    members_count: number;
    skills_count: number;
    teaching_offers_count: number;
    learning_goals_count: number;
    matched_learning_goals_count: number;
  };
  matches: Array<{
    skill_id: number;
    skill_name: string;
    learners_count: number;
    teachers: Array<{
      id: number;
      display_name: string;
      telegram_username: string | null;
    }>;
  }>;
  skills: Array<{
    skill_id: number;
    skill_name: string;
    teachers_count: number;
    learners_count: number;
  }>;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const ACCESS_KEY = "skillpeer21.access";
const REFRESH_KEY = "skillpeer21.refresh";

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

export function saveTokens(tokens: TokenPair): void {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const accessToken = getAccessToken();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  login: (login: string, password: string) =>
    request<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ login, password }),
    }),
  me: () => request<User>("/auth/me"),
  dashboard: () => request<Dashboard>("/dashboard"),
  skills: () => request<Skill[]>("/skills"),
  mySkills: () => request<UserSkill[]>("/skills/me"),
  createSkill: (name: string) =>
    request<Skill>("/skills", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  addSkillIntent: (skillId: number, intent: "teach" | "learn") =>
    request<UserSkill>(`/skills/${skillId}/links`, {
      method: "POST",
      body: JSON.stringify({ intent }),
    }),
};

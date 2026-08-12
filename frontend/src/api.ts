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

export type EventTimeOption = {
  id: number;
  starts_at: string;
  votes_count: number;
  voted_by_me: boolean;
  teacher_voted: boolean;
};

export type CommunityEvent = {
  id: number;
  skill_id: number;
  skill_name: string;
  creator_id: number;
  teacher_id: number;
  title: string;
  description: string | null;
  status: "scheduling" | "confirmed" | "completed" | "cancelled";
  confirmed_time_option_id: number | null;
  participants: Array<{
    user_id: number;
    display_name: string;
    role: "teacher" | "learner";
    kudos_received: number;
    kudos_given_by_me: boolean;
  }>;
  time_options: EventTimeOption[];
  created_at: string;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const ACCESS_KEY = "skillpeer21.access";
const REFRESH_KEY = "skillpeer21.refresh";
const AUTH_EVENT = "skillpeer21-auth";

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

export function saveTokens(tokens: TokenPair): void {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function clearTokens(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function onAuthChange(listener: () => void): () => void {
  window.addEventListener(AUTH_EVENT, listener);
  return () => window.removeEventListener(AUTH_EVENT, listener);
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
  events: () => request<CommunityEvent[]>("/events"),
  createEvent: (payload: {
    skill_id: number;
    teacher_id: number;
    title: string;
    description?: string;
    time_options: string[];
  }) => request<CommunityEvent>("/events", { method: "POST", body: JSON.stringify(payload) }),
  joinEvent: (eventId: number) => request<CommunityEvent>(`/events/${eventId}/join`, { method: "POST" }),
  voteEventTime: (eventId: number, optionId: number) =>
    request<CommunityEvent>(`/events/${eventId}/time-options/${optionId}/vote`, { method: "POST" }),
  confirmEventTime: (eventId: number, optionId: number) =>
    request<CommunityEvent>(`/events/${eventId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ time_option_id: optionId }),
    }),
  completeEvent: (eventId: number) =>
    request<CommunityEvent>(`/events/${eventId}/complete`, { method: "POST" }),
  giveKudos: (eventId: number, recipientId: number) =>
    request<CommunityEvent>(`/events/${eventId}/kudos/${recipientId}`, { method: "POST" }),
};

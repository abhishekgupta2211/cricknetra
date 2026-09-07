const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8023/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cricnetra_token') : null;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (username_or_email: string, password_hash: string) => {
    const data = await request<any>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username_or_email, password_hash }),
    });
    if (data.access_token && typeof window !== 'undefined') {
      localStorage.setItem('cricnetra_token', data.access_token);
    }
    return data;
  },
  register: (data: any) => request<any>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request<any>('/auth/me'),

  // Matches
  createMatch: (data: any) => request<any>('/matches/', { method: 'POST', body: JSON.stringify(data) }),
  matches: () => request<any[]>('/matches/'),
  match: (id: string) => request<any>(`/matches/${id}`),

  // Ball Scoring
  scoreBall: (matchId: string, ballData: any) =>
    request<any>(`/matches/${matchId}/balls`, { method: 'POST', body: JSON.stringify(ballData) }),

  // Tournaments
  tournaments: () => request<any[]>('/tournaments/'),
  tournament: (id: string) => request<any>(`/tournaments/${id}`),

  // Teams & Players
  teams: () => request<any[]>('/teams/'),
  players: () => request<any[]>('/players/'),

  // Leaderboards
  leaderboard: () => request<any>('/leaderboards/'),

  // Custom Rules
  templates: () => request<any[]>('/rules/templates'),
};

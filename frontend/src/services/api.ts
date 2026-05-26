import axios from 'axios';
import type { Article, Stats, SentimentOverview, TrendData, StoryComparison, Story, Source, ChatMessage, QaStatus } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const SESSION_STORAGE_KEY = 'news-summarizer:session-id';

function readStoredSessionId(): string | null {
  try {
    return typeof localStorage !== 'undefined' ? localStorage.getItem(SESSION_STORAGE_KEY) : null;
  } catch {
    return null;
  }
}

function writeStoredSessionId(id: string): void {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(SESSION_STORAGE_KEY, id);
    }
  } catch {
    /* localStorage unavailable (private mode, SSR) — fall through */
  }
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const sessionId = readStoredSessionId();
  if (sessionId) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>)['X-Session-Id'] = sessionId;
  }
  return config;
});

api.interceptors.response.use((response) => {
  const minted = response.headers?.['x-session-id'];
  if (typeof minted === 'string' && minted && minted !== readStoredSessionId()) {
    writeStoredSessionId(minted);
  }
  return response;
});

export const articlesApi = {
  fetch: (source = 'rss', maxPerSource = 5, process = true) =>
    api.post<{ articles: Article[]; total: number; message: string }>('/fetch', { source, max_per_source: maxPerSource, process }),

  getAll: (params: Record<string, string> = {}) =>
    api.get<{ articles: Article[]; total: number; limit: number; offset: number }>('/articles', { params }),

  getById: (id: string | undefined) => api.get<Article>(`/articles/${id}`),

  search: (query: string, limit = 20) =>
    api.get<{ results: Article[]; total: number; query: string }>('/articles/search', { params: { q: query, limit } }),

  getStats: () => api.get<Stats>('/stats'),

  clear: () => api.delete<{ message: string }>('/articles'),
};

export const sentimentApi = {
  getOverview: () => api.get<SentimentOverview>('/sentiment'),

  getByType: (type: string, limit = 50) =>
    api.get<{ articles: Article[]; type: string }>(`/sentiment/${type}`, { params: { limit } }),

  getByCategory: () => api.get('/sentiment/distribution/by-category'),

  getBySource: () => api.get('/sentiment/distribution/by-source'),
};

export const trendingApi = {
  getTrending: (useLlm = true, topN = 10) =>
    api.get<TrendData>('/trending', { params: { use_llm: useLlm, top_n: topN } }),

  getTrendingFast: (topN = 10) =>
    api.get<TrendData>('/trending/fast', { params: { top_n: topN } }),

  getKeywords: (topN = 20) =>
    api.get('/trending/keywords', { params: { top_n: topN } }),

  getEntities: (topN = 10) =>
    api.get('/trending/entities', { params: { top_n: topN } }),

  getArticlesByKeyword: (keyword: string) =>
    api.get(`/trending/keyword/${encodeURIComponent(keyword)}`),
};

export const similarityApi = {
  getSimilar: (articleId: string | undefined, threshold = 0.2, maxResults = 5) =>
    api.get<{ similar_articles: Article[] }>(`/articles/${articleId}/similar`, {
      params: { threshold, max_results: maxResults }
    }),

  getRelationships: (useLlm = true) =>
    api.get('/relationships', { params: { use_llm: useLlm } }),

  getPairs: (threshold = 0.3, limit = 20) =>
    api.get('/relationships/pairs', { params: { threshold, limit } }),

  compareTwo: (idA: number, idB: number) =>
    api.get(`/compare/${idA}/${idB}`),
};

export const comparisonApi = {
  getStories: () => api.get<{ stories: Story[] }>('/comparison/stories'),

  compareAll: () => api.get<{ comparisons: StoryComparison[] }>('/comparison'),

  compareSpecific: (articleIds: number[]) =>
    api.post('/comparison/specific', { article_ids: articleIds }),

  getBiasAnalysis: () => api.get('/comparison/bias'),

  getSources: () => api.get<{ sources: Source[] }>('/sources'),
};

export const qaApi = {
  ask: (question: string) =>
    api.post<{ question: string; answer: string; article_count: number }>('/qa/ask', { question }),

  getHistory: () => api.get<{ history: ChatMessage[]; message_count: number }>('/qa/history'),

  clearHistory: () => api.delete<{ message: string }>('/qa/history'),

  getStatus: () => api.get<QaStatus>('/qa/status'),
};

export const healthCheck = () => api.get('/health');

export default api;

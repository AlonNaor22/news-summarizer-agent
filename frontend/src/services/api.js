import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Articles API
export const articlesApi = {
  fetch: (source = 'rss', maxPerSource = 5, process = true) =>
    api.post('/fetch', { source, max_per_source: maxPerSource, process }),

  getAll: (params = {}) => api.get('/articles', { params }),

  getById: (id) => api.get(`/articles/${id}`),

  search: (query, limit = 20) =>
    api.get('/articles/search', { params: { q: query, limit } }),

  getStats: () => api.get('/stats'),

  clear: () => api.delete('/articles'),
};

// Sentiment API
export const sentimentApi = {
  getOverview: () => api.get('/sentiment'),

  getByType: (type, limit = 50) =>
    api.get(`/sentiment/${type}`, { params: { limit } }),

  getByCategory: () => api.get('/sentiment/distribution/by-category'),

  getBySource: () => api.get('/sentiment/distribution/by-source'),
};

// Trending API
export const trendingApi = {
  getTrending: (useLlm = true, topN = 10) =>
    api.get('/trending', { params: { use_llm: useLlm, top_n: topN } }),

  getTrendingFast: (topN = 10) =>
    api.get('/trending/fast', { params: { top_n: topN } }),

  getKeywords: (topN = 20) =>
    api.get('/trending/keywords', { params: { top_n: topN } }),

  getEntities: (topN = 10) =>
    api.get('/trending/entities', { params: { top_n: topN } }),

  getArticlesByKeyword: (keyword) =>
    api.get(`/trending/keyword/${encodeURIComponent(keyword)}`),
};

// Similarity API
export const similarityApi = {
  getSimilar: (articleId, threshold = 0.2, maxResults = 5) =>
    api.get(`/articles/${articleId}/similar`, {
      params: { threshold, max_results: maxResults }
    }),

  getRelationships: (useLlm = true) =>
    api.get('/relationships', { params: { use_llm: useLlm } }),

  getPairs: (threshold = 0.3, limit = 20) =>
    api.get('/relationships/pairs', { params: { threshold, limit } }),

  compareTwo: (idA, idB) =>
    api.get(`/compare/${idA}/${idB}`),
};

// Comparison API
export const comparisonApi = {
  getStories: () => api.get('/comparison/stories'),

  compareAll: () => api.get('/comparison'),

  compareSpecific: (articleIds) =>
    api.post('/comparison/specific', { article_ids: articleIds }),

  getBiasAnalysis: () => api.get('/comparison/bias'),

  getSources: () => api.get('/sources'),
};

// Q&A API
export const qaApi = {
  ask: (question) =>
    api.post('/qa/ask', { question }),

  getHistory: () => api.get('/qa/history'),

  clearHistory: () => api.delete('/qa/history'),

  getStatus: () => api.get('/qa/status'),
};

// Health check
export const healthCheck = () => api.get('/health');

export default api;

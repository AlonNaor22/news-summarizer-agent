import { vi, describe, test, expect, beforeEach } from 'vitest';

// vi.hoisted ensures these mocks are available when the vi.mock factory runs
const { mockPost, mockGet } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockGet: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: () => ({
      post: mockPost,
      get: mockGet,
      delete: vi.fn().mockResolvedValue({ data: {} }),
    }),
  },
}));

import { articlesApi } from './api.js';

describe('articlesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: {} });
    mockGet.mockResolvedValue({ data: {} });
  });

  test('fetch posts to /fetch with the right body shape', async () => {
    await articlesApi.fetch('rss', 5, true);
    expect(mockPost).toHaveBeenCalledWith('/fetch', {
      source: 'rss',
      max_per_source: 5,
      process: true,
    });
  });

  test('fetch uses default parameters when called with no arguments', async () => {
    await articlesApi.fetch();
    expect(mockPost).toHaveBeenCalledWith('/fetch', {
      source: 'rss',
      max_per_source: 5,
      process: true,
    });
  });
});

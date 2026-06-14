/**
 * Centralized user-facing copy for the React app.
 *
 * Everything a user reads on screen lives here so wording stays consistent and
 * a future translation is a drop-in: swap this module (or select by locale) and
 * no JSX needs to change. Parameterized copy is exposed as small functions so
 * call sites stay declarative.
 *
 * Deliberately NOT here: decorative emoji, CSS class names, route paths, and
 * any value that comes from the API/LLM (article text, categories, sentiments).
 */

export const strings = {
  nav: {
    brand: 'News Summarizer',
    dashboard: 'Dashboard',
    articles: 'Articles',
    trending: 'Trending',
    compare: 'Compare',
    chat: 'Chat',
  },

  common: {
    loading: 'Loading...',
    search: 'Search',
    goToDashboard: 'Go to Dashboard',
    backToArticles: 'Back to Articles',
    viewAll: 'View all',
    clearAll: 'Clear All',
    unknown: 'Unknown',
  },

  articleCard: {
    readFull: 'Read full article',
  },

  dashboard: {
    title: 'News Dashboard',
    subtitle: 'Fetch, summarize, and analyze news articles with AI',
    fetchHeading: 'Fetch News',
    sourceLabel: 'Source',
    perSourceLabel: 'Articles per source',
    sourceRss: 'RSS Feeds',
    sourceNewsapi: 'NewsAPI',
    sourceBoth: 'Both',
    fetchButton: 'Fetch News',
    fetchingButton: 'Fetching & Processing...',
    fetchError: 'Error fetching articles',
    fetchProgress: 'Fetching and processing articles with AI... This may take a moment.',
    loading: 'Loading dashboard...',
    totalArticles: 'Total Articles',
    positive: 'Positive',
    negative: 'Negative',
    neutral: 'Neutral',
    sentimentDistribution: 'Sentiment Distribution',
    trendingKeywords: 'Trending Keywords',
    articlesByCategory: 'Articles by Category',
  },

  articles: {
    title: 'Articles',
    found: (count: number) => `${count} articles found`,
    searchPlaceholder: 'Search articles...',
    allCategories: 'All Categories',
    allSentiments: 'All Sentiments',
    allSources: 'All Sources',
    positive: 'Positive',
    negative: 'Negative',
    neutral: 'Neutral',
    clearFilters: 'Clear Filters',
    loading: 'Loading articles...',
    none: 'No articles found.',
    adjustFilters: 'Try adjusting your filters or search query.',
    filterByCategory: 'Filter by category',
    filterBySentiment: 'Filter by sentiment',
    filterBySource: 'Filter by source',
  },

  articleDetail: {
    loading: 'Loading article...',
    notFoundTitle: 'Article Not Found',
    notFound: 'Article not found',
    notFoundBody: 'The article you are looking for does not exist.',
    summary: 'Summary',
    sentimentAnalysis: 'Sentiment Analysis',
    confidenceLabel: 'Confidence:',
    tagsAndEntities: 'Tags & Entities',
    keywords: 'Keywords',
    people: 'People',
    organizations: 'Organizations',
    locations: 'Locations',
    readOriginal: 'Read Original Article',
    similar: 'Similar Articles',
    percentSimilar: (percent: number) => `${percent}% similar`,
  },

  trending: {
    title: 'Trending Topics',
    subtitle: (articleCount: number) =>
      `See what topics are being discussed across ${articleCount} articles`,
    analyzeWithAi: 'Analyze with AI',
    analyzing: 'Analyzing...',
    analyzingBanner: 'AI is analyzing article themes and patterns...',
    aiThemes: 'AI-Detected Themes',
    keywordsLabel: 'Keywords:',
    trendingKeywords: 'Trending Keywords',
    noKeywords: 'No trending keywords yet',
    trendingPeople: 'Trending People',
    trendingOrganizations: 'Trending Organizations',
    trendingLocations: 'Trending Locations',
    articlesCount: (count: number) => `${count} articles`,
    loading: 'Loading trending topics...',
    none: 'No trending topics yet.',
    fetchFirst: 'Fetch some articles first',
  },

  compare: {
    title: 'Source Comparison',
    subtitle: 'Compare how different news sources cover the same stories',
    compareButton: 'Compare Sources with AI',
    comparing: 'Analyzing...',
    comparingBanner: 'AI is comparing source coverage...',
    newsSources: 'News Sources',
    multiSourceStories: 'Multi-Source Stories',
    storiesCovered: (count: number) => `${count} stories covered by multiple sources`,
    articlesCount: (count: number) => `${count} articles`,
    readyTitle: 'Ready to Compare',
    readyBody: (count: number) => `Found ${count} stories covered by multiple sources.`,
    readyHint:
      'Click "Compare Sources with AI" to analyze how different outlets cover the same events.',
    noStoriesTitle: 'No Multi-Source Stories Found',
    noStoriesBody:
      'To compare sources, you need stories that are covered by multiple news outlets.',
    noStoriesHint: 'Try fetching more articles from different sources.',
    loading: 'Loading comparison data...',
    sourcesLabel: 'Sources:',
    storySummary: 'Story Summary',
    commonFacts: 'Common Facts (All Sources Agree)',
    sourceBySource: 'Source-by-Source Analysis',
    focusLabel: 'Focus:',
    uniqueDetailsLabel: 'Unique Details:',
    potentialBiasLabel: 'Potential Bias:',
    keyDifferences: 'Key Differences',
    overallAssessment: 'Overall Assessment',
  },

  chat: {
    title: 'Chat with News',
    articlesLoaded: (count: number) => `${count} articles loaded`,
    clearChat: 'Clear Chat',
    noArticlesTitle: 'No Articles Loaded',
    noArticlesBody: 'Fetch some news articles first to start chatting about them.',
    welcomeTitle: 'Ask questions about your news',
    welcomeBody: "I can help you understand, compare, and analyze the articles you've fetched.",
    tryAsking: 'Try asking:',
    inputPlaceholder: 'Ask a question about the news...',
    inputLabel: 'Ask a question about the news',
    send: 'Send',
    sending: '...',
    suggestedQuestions: [
      'What are the main technology news today?',
      'Which articles have negative sentiment?',
      'Summarize the business news',
      'What topics are most covered?',
      'Compare different news sources',
    ],
    streamingFailed: 'Streaming failed.',
    genericError: 'Sorry, something went wrong.',
    midStreamError: (detail: string) => `\n\n[Error mid-stream: ${detail}]`,
    errorPrefix: (message: string) => `Error: ${message}`,
  },
};

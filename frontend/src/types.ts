export type SentimentType = 'positive' | 'negative' | 'neutral';

export interface Article {
  id?: number;
  title: string;
  description?: string;
  summary?: string;
  url: string;
  source: string;
  published?: string;
  category?: string;
  secondary_categories?: string[];
  sentiment?: SentimentType;
  sentiment_confidence?: number;
  sentiment_reason?: string;
  keywords?: string[];
  people?: string[];
  organizations?: string[];
  locations?: string[];
  author?: string;
  image_url?: string;
  similarity?: {
    overall: number;
    shared_keywords?: string[];
    shared_entities?: string[];
    [key: string]: unknown;
  };
}

export interface Stats {
  total: number;
  by_category: Record<string, number>;
  by_sentiment: Record<string, number>;
  by_source: Record<string, number>;
}

export interface SentimentOverview {
  positive: number;
  negative: number;
  neutral: number;
  breakdown?: Record<string, number>;
}

export interface KeywordTrend {
  keyword: string;
  count: number;
  percentage: number;
}

export interface LlmTrend {
  name: string;
  strength: 'high' | 'medium' | 'low';
  description: string;
  keywords?: string[];
  article_count: number;
}

export interface TrendData {
  keyword_trends: KeywordTrend[];
  llm_trends?: LlmTrend[];
  entity_trends?: {
    people?: [string, number][];
    organizations?: [string, number][];
    locations?: [string, number][];
  };
  total_articles?: number;
}

export interface SourceAnalysis {
  source: string;
  tone: SentimentType;
  emphasis: string;
  unique_details?: string;
  potential_bias?: string;
}

export interface StoryComparison {
  story_title?: string;
  story_summary?: string;
  common_facts?: string[];
  source_analyses?: Record<string, SourceAnalysis>;
  key_differences?: string[];
  overall_assessment?: string;
  sources?: string[];
  article_count?: number;
  error?: string;
}

export interface Story {
  story_title: string;
  sources: string[];
  source_count: number;
  articles: Article[];
}

export interface Source {
  name: string;
  article_count: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface QaStatus {
  articles_loaded: number;
  history_length: number;
  ready: boolean;
}

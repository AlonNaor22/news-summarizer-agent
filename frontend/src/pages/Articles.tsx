import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { articlesApi } from '../services/api';
import type { Article, Stats } from '../types';
import { strings } from '../strings';
import ArticleCard from '../components/ArticleCard';
import SearchBar from '../components/SearchBar';
import LoadingSpinner from '../components/LoadingSpinner';
import './Articles.css';

function Articles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [articles, setArticles] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats | null>(null);

  const category = searchParams.get('category') || '';
  const sentiment = searchParams.get('sentiment') || '';
  const source = searchParams.get('source') || '';
  const keyword = searchParams.get('keyword') || '';

  const loadArticles = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (category) params.category = category;
      if (sentiment) params.sentiment = sentiment;
      if (source) params.source = source;
      if (keyword) params.keyword = keyword;

      const [articlesRes, statsRes] = await Promise.all([
        articlesApi.getAll(params),
        articlesApi.getStats()
      ]);

      setArticles(articlesRes.data.articles);
      setTotal(articlesRes.data.total);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Error loading articles:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArticles();
  }, [category, sentiment, source, keyword]);

  const handleSearch = (query: string) => {
    setSearchParams({ keyword: query });
  };

  const handleFilterChange = (type: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(type, value);
    } else {
      newParams.delete(type);
    }
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  const hasFilters = category || sentiment || source || keyword;

  return (
    <div className="articles-page">
      <div className="articles-header">
        <h1>{strings.articles.title}</h1>
        <p>{strings.articles.found(total)}</p>
      </div>

      <div className="articles-filters">
        <SearchBar onSearch={handleSearch} placeholder={strings.articles.searchPlaceholder} />

        <div className="filter-group">
          <select
            value={category}
            onChange={(e) => handleFilterChange('category', e.target.value)}
            aria-label={strings.articles.filterByCategory}
          >
            <option value="">{strings.articles.allCategories}</option>
            {stats?.by_category && Object.keys(stats.by_category).map(cat => (
              <option key={cat} value={cat}>{cat} ({stats.by_category[cat]})</option>
            ))}
          </select>

          <select
            value={sentiment}
            onChange={(e) => handleFilterChange('sentiment', e.target.value)}
            aria-label={strings.articles.filterBySentiment}
          >
            <option value="">{strings.articles.allSentiments}</option>
            <option value="positive">{strings.articles.positive} ({stats?.by_sentiment?.positive || 0})</option>
            <option value="negative">{strings.articles.negative} ({stats?.by_sentiment?.negative || 0})</option>
            <option value="neutral">{strings.articles.neutral} ({stats?.by_sentiment?.neutral || 0})</option>
          </select>

          <select
            value={source}
            onChange={(e) => handleFilterChange('source', e.target.value)}
            aria-label={strings.articles.filterBySource}
          >
            <option value="">{strings.articles.allSources}</option>
            {stats?.by_source && Object.keys(stats.by_source).map(src => (
              <option key={src} value={src}>{src} ({stats.by_source[src]})</option>
            ))}
          </select>

          {hasFilters && (
            <button className="btn-clear" onClick={clearFilters}>
              {strings.articles.clearFilters}
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message={strings.articles.loading} />
      ) : articles.length === 0 ? (
        <div className="no-articles">
          <p>{strings.articles.none}</p>
          {hasFilters && <p>{strings.articles.adjustFilters}</p>}
        </div>
      ) : (
        <div className="articles-grid">
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Articles;

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { articlesApi } from '../services/api';
import ArticleCard from '../components/ArticleCard';
import SearchBar from '../components/SearchBar';
import LoadingSpinner from '../components/LoadingSpinner';
import './Articles.css';

function Articles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [articles, setArticles] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);

  const category = searchParams.get('category') || '';
  const sentiment = searchParams.get('sentiment') || '';
  const source = searchParams.get('source') || '';
  const keyword = searchParams.get('keyword') || '';

  const loadArticles = async () => {
    setLoading(true);
    try {
      const params = {};
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

  const handleSearch = async (query) => {
    setSearchParams({ keyword: query });
  };

  const handleFilterChange = (type, value) => {
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
        <h1>Articles</h1>
        <p>{total} articles found</p>
      </div>

      <div className="articles-filters">
        <SearchBar onSearch={handleSearch} placeholder="Search articles..." />

        <div className="filter-group">
          <select
            value={category}
            onChange={(e) => handleFilterChange('category', e.target.value)}
          >
            <option value="">All Categories</option>
            {stats?.by_category && Object.keys(stats.by_category).map(cat => (
              <option key={cat} value={cat}>{cat} ({stats.by_category[cat]})</option>
            ))}
          </select>

          <select
            value={sentiment}
            onChange={(e) => handleFilterChange('sentiment', e.target.value)}
          >
            <option value="">All Sentiments</option>
            <option value="positive">Positive ({stats?.by_sentiment?.positive || 0})</option>
            <option value="negative">Negative ({stats?.by_sentiment?.negative || 0})</option>
            <option value="neutral">Neutral ({stats?.by_sentiment?.neutral || 0})</option>
          </select>

          <select
            value={source}
            onChange={(e) => handleFilterChange('source', e.target.value)}
          >
            <option value="">All Sources</option>
            {stats?.by_source && Object.keys(stats.by_source).map(src => (
              <option key={src} value={src}>{src} ({stats.by_source[src]})</option>
            ))}
          </select>

          {hasFilters && (
            <button className="btn-clear" onClick={clearFilters}>
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading articles..." />
      ) : articles.length === 0 ? (
        <div className="no-articles">
          <p>No articles found.</p>
          {hasFilters && <p>Try adjusting your filters or search query.</p>}
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

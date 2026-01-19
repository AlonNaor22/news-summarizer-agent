import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { articlesApi, sentimentApi, trendingApi } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import TrendingKeywords from '../components/TrendingKeywords';
import './Dashboard.css';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);
  const [fetchSource, setFetchSource] = useState('rss');
  const [maxArticles, setMaxArticles] = useState(5);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, sentimentRes, keywordsRes] = await Promise.all([
        articlesApi.getStats(),
        sentimentApi.getOverview(),
        trendingApi.getTrendingFast(10)
      ]);

      setStats(statsRes.data);
      setSentiment(sentimentRes.data);
      setKeywords(keywordsRes.data.keyword_trends || []);
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleFetchNews = async () => {
    setFetching(true);
    setError(null);

    try {
      const response = await articlesApi.fetch(fetchSource, maxArticles, true);
      console.log('Fetch response:', response.data);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error fetching articles');
      console.error('Fetch error:', err);
    } finally {
      setFetching(false);
    }
  };

  const handleClearArticles = async () => {
    try {
      await articlesApi.clear();
      await loadData();
    } catch (err) {
      console.error('Clear error:', err);
    }
  };

  if (loading && !stats) {
    return <LoadingSpinner message="Loading dashboard..." />;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>News Dashboard</h1>
        <p>Fetch, summarize, and analyze news articles with AI</p>
      </div>

      <div className="fetch-section card">
        <h2>Fetch News</h2>

        <div className="fetch-controls">
          <div className="control-group">
            <label>Source</label>
            <select
              value={fetchSource}
              onChange={(e) => setFetchSource(e.target.value)}
              disabled={fetching}
            >
              <option value="rss">RSS Feeds</option>
              <option value="newsapi">NewsAPI</option>
              <option value="both">Both</option>
            </select>
          </div>

          <div className="control-group">
            <label>Articles per source</label>
            <select
              value={maxArticles}
              onChange={(e) => setMaxArticles(Number(e.target.value))}
              disabled={fetching}
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </div>

          <button
            className="btn btn-primary"
            onClick={handleFetchNews}
            disabled={fetching}
          >
            {fetching ? 'Fetching & Processing...' : 'Fetch News'}
          </button>

          {stats?.total > 0 && (
            <button
              className="btn btn-secondary"
              onClick={handleClearArticles}
              disabled={fetching}
            >
              Clear All
            </button>
          )}
        </div>

        {error && <p className="error-message">{error}</p>}

        {fetching && (
          <div className="fetch-progress">
            <LoadingSpinner size="small" message="Fetching and processing articles with AI... This may take a moment." />
          </div>
        )}
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.total || 0}</div>
          <div className="stat-label">Total Articles</div>
        </div>

        <div className="stat-card positive">
          <div className="stat-value">{sentiment?.positive || 0}</div>
          <div className="stat-label">Positive</div>
        </div>

        <div className="stat-card negative">
          <div className="stat-value">{sentiment?.negative || 0}</div>
          <div className="stat-label">Negative</div>
        </div>

        <div className="stat-card neutral">
          <div className="stat-value">{sentiment?.neutral || 0}</div>
          <div className="stat-label">Neutral</div>
        </div>
      </div>

      {stats?.total > 0 && (
        <>
          <div className="dashboard-section">
            <div className="section-header">
              <h2>Sentiment Distribution</h2>
            </div>
            <div className="sentiment-bars">
              {sentiment?.breakdown && Object.entries(sentiment.breakdown).map(([type, percentage]) => (
                <div key={type} className="sentiment-bar-group">
                  <div className="sentiment-bar-label">{type}</div>
                  <div className="sentiment-bar-track">
                    <div
                      className={`sentiment-bar-fill ${type}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <div className="sentiment-bar-value">{percentage}%</div>
                </div>
              ))}
            </div>
          </div>

          <div className="dashboard-section">
            <div className="section-header">
              <h2>Trending Keywords</h2>
              <Link to="/trending" className="section-link">View all</Link>
            </div>
            <TrendingKeywords keywords={keywords} />
          </div>

          <div className="dashboard-section">
            <div className="section-header">
              <h2>Articles by Category</h2>
              <Link to="/articles" className="section-link">View all</Link>
            </div>
            <div className="category-list">
              {stats?.by_category && Object.entries(stats.by_category).map(([category, count]) => (
                <Link
                  key={category}
                  to={`/articles?category=${encodeURIComponent(category)}`}
                  className="category-item"
                >
                  <span className="category-name">{category}</span>
                  <span className="category-count">{count}</span>
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;

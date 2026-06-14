import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { articlesApi, sentimentApi, trendingApi } from '../services/api';
import type { Stats, SentimentOverview, KeywordTrend } from '../types';
import { strings } from '../strings';
import LoadingSpinner from '../components/LoadingSpinner';
import TrendingKeywords from '../components/TrendingKeywords';
import './Dashboard.css';

function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [sentiment, setSentiment] = useState<SentimentOverview | null>(null);
  const [keywords, setKeywords] = useState<KeywordTrend[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchSource, setFetchSource] = useState('rss');
  const [maxArticles, setMaxArticles] = useState(5);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, sentimentRes, keywordsRes] = await Promise.all([
        articlesApi.getStats(),
        sentimentApi.getOverview(),
        trendingApi.getTrendingFast(10),
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
      await articlesApi.fetch(fetchSource, maxArticles, true);
      await loadData();
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null;
      setError(detail || strings.dashboard.fetchError);
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
    return <LoadingSpinner message={strings.dashboard.loading} />;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>{strings.dashboard.title}</h1>
        <p>{strings.dashboard.subtitle}</p>
      </div>

      <div className="fetch-section card">
        <h2>{strings.dashboard.fetchHeading}</h2>

        <div className="fetch-controls">
          <div className="control-group">
            <label htmlFor="fetch-source">{strings.dashboard.sourceLabel}</label>
            <select
              id="fetch-source"
              value={fetchSource}
              onChange={(e) => setFetchSource(e.target.value)}
              disabled={fetching}
            >
              <option value="rss">{strings.dashboard.sourceRss}</option>
              <option value="newsapi">{strings.dashboard.sourceNewsapi}</option>
              <option value="both">{strings.dashboard.sourceBoth}</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="fetch-max">{strings.dashboard.perSourceLabel}</label>
            <select
              id="fetch-max"
              value={maxArticles}
              onChange={(e) => setMaxArticles(Number(e.target.value))}
              disabled={fetching}
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </div>

          <button className="btn btn-primary" onClick={handleFetchNews} disabled={fetching}>
            {fetching ? strings.dashboard.fetchingButton : strings.dashboard.fetchButton}
          </button>

          {(stats?.total ?? 0) > 0 && (
            <button className="btn btn-secondary" onClick={handleClearArticles} disabled={fetching}>
              {strings.common.clearAll}
            </button>
          )}
        </div>

        {error && <p className="error-message">{error}</p>}

        {fetching && (
          <div className="fetch-progress">
            <LoadingSpinner size="small" message={strings.dashboard.fetchProgress} />
          </div>
        )}
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.total || 0}</div>
          <div className="stat-label">{strings.dashboard.totalArticles}</div>
        </div>

        <div className="stat-card positive">
          <div className="stat-value">{sentiment?.positive || 0}</div>
          <div className="stat-label">{strings.dashboard.positive}</div>
        </div>

        <div className="stat-card negative">
          <div className="stat-value">{sentiment?.negative || 0}</div>
          <div className="stat-label">{strings.dashboard.negative}</div>
        </div>

        <div className="stat-card neutral">
          <div className="stat-value">{sentiment?.neutral || 0}</div>
          <div className="stat-label">{strings.dashboard.neutral}</div>
        </div>
      </div>

      {(stats?.total ?? 0) > 0 && (
        <>
          <div className="dashboard-section">
            <div className="section-header">
              <h2>{strings.dashboard.sentimentDistribution}</h2>
            </div>
            <div className="sentiment-bars">
              {sentiment?.breakdown &&
                Object.entries(sentiment.breakdown).map(([type, percentage]) => (
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
              <h2>{strings.dashboard.trendingKeywords}</h2>
              <Link to="/trending" className="section-link">
                {strings.common.viewAll}
              </Link>
            </div>
            <TrendingKeywords keywords={keywords} />
          </div>

          <div className="dashboard-section">
            <div className="section-header">
              <h2>{strings.dashboard.articlesByCategory}</h2>
              <Link to="/articles" className="section-link">
                {strings.common.viewAll}
              </Link>
            </div>
            <div className="category-list">
              {stats?.by_category &&
                Object.entries(stats.by_category).map(([category, count]) => (
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

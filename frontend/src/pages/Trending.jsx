import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { trendingApi } from '../services/api';
import TrendingKeywords from '../components/TrendingKeywords';
import LoadingSpinner from '../components/LoadingSpinner';
import './Trending.css';

function Trending() {
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [useLlm, setUseLlm] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const loadTrends = async (withLlm = false) => {
    if (withLlm) {
      setAnalyzing(true);
    } else {
      setLoading(true);
    }

    try {
      const response = withLlm
        ? await trendingApi.getTrending(true, 15)
        : await trendingApi.getTrendingFast(15);

      setTrends(response.data);
      setUseLlm(withLlm);
    } catch (err) {
      console.error('Error loading trends:', err);
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    loadTrends(false);
  }, []);

  const handleAnalyzeWithAI = () => {
    loadTrends(true);
  };

  if (loading) {
    return <LoadingSpinner message="Loading trending topics..." />;
  }

  return (
    <div className="trending-page">
      <div className="trending-header">
        <div>
          <h1>Trending Topics</h1>
          <p>See what topics are being discussed across {trends?.total_articles || 0} articles</p>
        </div>

        {!useLlm && (
          <button
            className="btn btn-ai"
            onClick={handleAnalyzeWithAI}
            disabled={analyzing}
          >
            {analyzing ? 'Analyzing...' : 'Analyze with AI'}
          </button>
        )}
      </div>

      {analyzing && (
        <div className="analyzing-banner">
          <LoadingSpinner size="small" message="AI is analyzing article themes and patterns..." />
        </div>
      )}

      {useLlm && trends?.llm_trends?.length > 0 && (
        <section className="trend-section">
          <h2>AI-Detected Themes</h2>
          <div className="llm-trends">
            {trends.llm_trends.map((trend, i) => (
              <div key={i} className={`llm-trend-card strength-${trend.strength}`}>
                <div className="trend-header">
                  <h3>{trend.name}</h3>
                  <span className={`strength-badge ${trend.strength}`}>
                    {trend.strength}
                  </span>
                </div>
                <p className="trend-description">{trend.description}</p>
                <div className="trend-meta">
                  <span>{trend.article_count} articles</span>
                  {trend.keywords?.length > 0 && (
                    <span className="trend-keywords">
                      Keywords: {trend.keywords.slice(0, 5).join(', ')}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="trend-section">
        <h2>Trending Keywords</h2>
        <TrendingKeywords
          keywords={trends?.keyword_trends || []}
          onKeywordClick={(kw) => window.location.href = `/articles?keyword=${encodeURIComponent(kw)}`}
        />
      </section>

      <div className="entity-sections">
        {trends?.entity_trends?.people?.length > 0 && (
          <section className="entity-section">
            <h2>Trending People</h2>
            <div className="entity-list">
              {trends.entity_trends.people.map(([name, count], i) => (
                <div key={i} className="entity-item">
                  <span className="entity-icon">👤</span>
                  <span className="entity-name">{name}</span>
                  <span className="entity-count">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {trends?.entity_trends?.organizations?.length > 0 && (
          <section className="entity-section">
            <h2>Trending Organizations</h2>
            <div className="entity-list">
              {trends.entity_trends.organizations.map(([name, count], i) => (
                <div key={i} className="entity-item">
                  <span className="entity-icon">🏢</span>
                  <span className="entity-name">{name}</span>
                  <span className="entity-count">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {trends?.entity_trends?.locations?.length > 0 && (
          <section className="entity-section">
            <h2>Trending Locations</h2>
            <div className="entity-list">
              {trends.entity_trends.locations.map(([name, count], i) => (
                <div key={i} className="entity-item">
                  <span className="entity-icon">📍</span>
                  <span className="entity-name">{name}</span>
                  <span className="entity-count">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {(!trends?.keyword_trends || trends.keyword_trends.length === 0) && (
        <div className="empty-state">
          <p>No trending topics yet.</p>
          <Link to="/" className="btn btn-primary">Fetch some articles first</Link>
        </div>
      )}
    </div>
  );
}

export default Trending;

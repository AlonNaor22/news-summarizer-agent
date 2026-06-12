import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { trendingApi } from '../services/api';
import type { TrendData } from '../types';
import { strings } from '../strings';
import TrendingKeywords from '../components/TrendingKeywords';
import LoadingSpinner from '../components/LoadingSpinner';
import './Trending.css';

function Trending() {
  const navigate = useNavigate();
  const [trends, setTrends] = useState<TrendData | null>(null);
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
    return <LoadingSpinner message={strings.trending.loading} />;
  }

  return (
    <div className="trending-page">
      <div className="trending-header">
        <div>
          <h1>{strings.trending.title}</h1>
          <p>{strings.trending.subtitle(trends?.total_articles || 0)}</p>
        </div>

        {!useLlm && (
          <button
            className="btn btn-ai"
            onClick={handleAnalyzeWithAI}
            disabled={analyzing}
          >
            {analyzing ? strings.trending.analyzing : strings.trending.analyzeWithAi}
          </button>
        )}
      </div>

      {analyzing && (
        <div className="analyzing-banner">
          <LoadingSpinner size="small" message={strings.trending.analyzingBanner} />
        </div>
      )}

      {useLlm && (trends?.llm_trends?.length ?? 0) > 0 && (
        <section className="trend-section">
          <h2>{strings.trending.aiThemes}</h2>
          <div className="llm-trends">
            {trends?.llm_trends?.map((trend) => (
              <div key={trend.name} className={`llm-trend-card strength-${trend.strength}`}>
                <div className="trend-header">
                  <h3>{trend.name}</h3>
                  <span className={`strength-badge ${trend.strength}`}>
                    {trend.strength}
                  </span>
                </div>
                <p className="trend-description">{trend.description}</p>
                <div className="trend-meta">
                  <span>{strings.trending.articlesCount(trend.article_count)}</span>
                  {(trend.keywords?.length ?? 0) > 0 && (
                    <span className="trend-keywords">
                      {strings.trending.keywordsLabel} {trend.keywords?.slice(0, 5).join(', ')}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="trend-section">
        <h2>{strings.trending.trendingKeywords}</h2>
        <TrendingKeywords
          keywords={trends?.keyword_trends || []}
          onKeywordClick={(kw) => navigate(`/articles?keyword=${encodeURIComponent(kw)}`)}
        />
      </section>

      <div className="entity-sections">
        {(trends?.entity_trends?.people?.length ?? 0) > 0 && (
          <section className="entity-section">
            <h2>{strings.trending.trendingPeople}</h2>
            <div className="entity-list">
              {trends?.entity_trends?.people?.map(([name, count]) => (
                <div key={name} className="entity-item">
                  <span className="entity-icon">👤</span>
                  <span className="entity-name">{name}</span>
                  <span className="entity-count">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {(trends?.entity_trends?.organizations?.length ?? 0) > 0 && (
          <section className="entity-section">
            <h2>{strings.trending.trendingOrganizations}</h2>
            <div className="entity-list">
              {trends?.entity_trends?.organizations?.map(([name, count]) => (
                <div key={name} className="entity-item">
                  <span className="entity-icon">🏢</span>
                  <span className="entity-name">{name}</span>
                  <span className="entity-count">{count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {(trends?.entity_trends?.locations?.length ?? 0) > 0 && (
          <section className="entity-section">
            <h2>{strings.trending.trendingLocations}</h2>
            <div className="entity-list">
              {trends?.entity_trends?.locations?.map(([name, count]) => (
                <div key={name} className="entity-item">
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
          <p>{strings.trending.none}</p>
          <Link to="/" className="btn btn-primary">{strings.trending.fetchFirst}</Link>
        </div>
      )}
    </div>
  );
}

export default Trending;

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { comparisonApi } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import SentimentBadge from '../components/SentimentBadge';
import './Compare.css';

function Compare() {
  const [stories, setStories] = useState([]);
  const [comparisons, setComparisons] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [selectedComparison, setSelectedComparison] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [storiesRes, sourcesRes] = await Promise.all([
          comparisonApi.getStories(),
          comparisonApi.getSources()
        ]);

        setStories(storiesRes.data.stories || []);
        setSources(sourcesRes.data.sources || []);
      } catch (err) {
        console.error('Error loading comparison data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleCompareAll = async () => {
    setComparing(true);
    try {
      const response = await comparisonApi.compareAll();
      setComparisons(response.data.comparisons || []);
      if (response.data.comparisons?.length > 0) {
        setSelectedComparison(response.data.comparisons[0]);
      }
    } catch (err) {
      console.error('Error comparing:', err);
    } finally {
      setComparing(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading comparison data..." />;
  }

  return (
    <div className="compare-page">
      <div className="compare-header">
        <div>
          <h1>Source Comparison</h1>
          <p>Compare how different news sources cover the same stories</p>
        </div>

        {stories.length > 0 && comparisons.length === 0 && (
          <button
            className="btn btn-ai"
            onClick={handleCompareAll}
            disabled={comparing}
          >
            {comparing ? 'Analyzing...' : 'Compare Sources with AI'}
          </button>
        )}
      </div>

      {comparing && (
        <div className="comparing-banner">
          <LoadingSpinner size="small" message="AI is comparing source coverage..." />
        </div>
      )}

      <div className="compare-content">
        <aside className="sources-sidebar">
          <h2>News Sources</h2>
          <div className="sources-list">
            {sources.map((source, i) => (
              <div key={i} className="source-item">
                <span className="source-name">{source.name}</span>
                <span className="source-count">{source.article_count} articles</span>
              </div>
            ))}
          </div>

          {stories.length > 0 && (
            <>
              <h2>Multi-Source Stories</h2>
              <p className="sidebar-note">
                {stories.length} stories covered by multiple sources
              </p>
              <div className="stories-list">
                {stories.map((story, i) => (
                  <div key={i} className="story-item">
                    <div className="story-title">{story.story_title.slice(0, 60)}...</div>
                    <div className="story-sources">{story.sources.join(', ')}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </aside>

        <main className="comparison-main">
          {comparisons.length === 0 ? (
            <div className="empty-comparison">
              {stories.length > 0 ? (
                <>
                  <h2>Ready to Compare</h2>
                  <p>Found {stories.length} stories covered by multiple sources.</p>
                  <p>Click "Compare Sources with AI" to analyze how different outlets cover the same events.</p>
                </>
              ) : (
                <>
                  <h2>No Multi-Source Stories Found</h2>
                  <p>To compare sources, you need stories that are covered by multiple news outlets.</p>
                  <p>Try fetching more articles from different sources.</p>
                  <Link to="/" className="btn btn-primary">Go to Dashboard</Link>
                </>
              )}
            </div>
          ) : (
            <>
              <div className="comparison-tabs">
                {comparisons.map((comp, i) => (
                  <button
                    key={i}
                    className={`comparison-tab ${selectedComparison === comp ? 'active' : ''}`}
                    onClick={() => setSelectedComparison(comp)}
                  >
                    {comp.story_title?.slice(0, 30)}...
                  </button>
                ))}
              </div>

              {selectedComparison && (
                <div className="comparison-detail">
                  <div className="comparison-header-detail">
                    <h2>{selectedComparison.story_title}</h2>
                    <div className="comparison-sources">
                      Sources: {selectedComparison.sources?.join(', ')}
                    </div>
                  </div>

                  <section className="comparison-section">
                    <h3>Story Summary</h3>
                    <p>{selectedComparison.story_summary}</p>
                  </section>

                  {selectedComparison.common_facts?.length > 0 && (
                    <section className="comparison-section">
                      <h3>Common Facts (All Sources Agree)</h3>
                      <ul className="facts-list">
                        {selectedComparison.common_facts.map((fact, i) => (
                          <li key={i}>{fact}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {Object.keys(selectedComparison.source_analyses || {}).length > 0 && (
                    <section className="comparison-section">
                      <h3>Source-by-Source Analysis</h3>
                      <div className="source-analyses">
                        {Object.entries(selectedComparison.source_analyses).map(([source, analysis]) => (
                          <div key={source} className="source-analysis-card">
                            <div className="source-analysis-header">
                              <span className="source-name">{source}</span>
                              <SentimentBadge sentiment={analysis.tone} />
                            </div>
                            <div className="source-analysis-body">
                              <div className="analysis-item">
                                <strong>Focus:</strong> {analysis.emphasis}
                              </div>
                              {analysis.unique_details && analysis.unique_details.toLowerCase() !== 'none' && (
                                <div className="analysis-item">
                                  <strong>Unique Details:</strong> {analysis.unique_details}
                                </div>
                              )}
                              {analysis.potential_bias && analysis.potential_bias.toLowerCase() !== 'none' && analysis.potential_bias.toLowerCase() !== 'none detected' && (
                                <div className="analysis-item bias">
                                  <strong>Potential Bias:</strong> {analysis.potential_bias}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {selectedComparison.key_differences?.length > 0 && (
                    <section className="comparison-section">
                      <h3>Key Differences</h3>
                      <ul className="differences-list">
                        {selectedComparison.key_differences.map((diff, i) => (
                          <li key={i}>{diff}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {selectedComparison.overall_assessment && (
                    <section className="comparison-section assessment">
                      <h3>Overall Assessment</h3>
                      <p>{selectedComparison.overall_assessment}</p>
                    </section>
                  )}
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default Compare;

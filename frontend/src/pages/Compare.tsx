import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { comparisonApi } from '../services/api';
import type { StoryComparison, Story, Source } from '../types';
import { strings } from '../strings';
import LoadingSpinner from '../components/LoadingSpinner';
import SentimentBadge from '../components/SentimentBadge';
import './Compare.css';

function Compare() {
  const [stories, setStories] = useState<Story[]>([]);
  const [comparisons, setComparisons] = useState<StoryComparison[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [selectedComparison, setSelectedComparison] = useState<StoryComparison | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [storiesRes, sourcesRes] = await Promise.all([
          comparisonApi.getStories(),
          comparisonApi.getSources(),
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
    return <LoadingSpinner message={strings.compare.loading} />;
  }

  return (
    <div className="compare-page">
      <div className="compare-header">
        <div>
          <h1>{strings.compare.title}</h1>
          <p>{strings.compare.subtitle}</p>
        </div>

        {stories.length > 0 && comparisons.length === 0 && (
          <button className="btn btn-ai" onClick={handleCompareAll} disabled={comparing}>
            {comparing ? strings.compare.comparing : strings.compare.compareButton}
          </button>
        )}
      </div>

      {comparing && (
        <div className="comparing-banner">
          <LoadingSpinner size="small" message={strings.compare.comparingBanner} />
        </div>
      )}

      <div className="compare-content">
        <aside className="sources-sidebar">
          <h2>{strings.compare.newsSources}</h2>
          <div className="sources-list">
            {sources.map((source) => (
              <div key={source.name} className="source-item">
                <span className="source-name">{source.name}</span>
                <span className="source-count">
                  {strings.compare.articlesCount(source.article_count)}
                </span>
              </div>
            ))}
          </div>

          {stories.length > 0 && (
            <>
              <h2>{strings.compare.multiSourceStories}</h2>
              <p className="sidebar-note">{strings.compare.storiesCovered(stories.length)}</p>
              <div className="stories-list">
                {stories.map((story) => (
                  <div key={story.story_title} className="story-item">
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
                  <h2>{strings.compare.readyTitle}</h2>
                  <p>{strings.compare.readyBody(stories.length)}</p>
                  <p>{strings.compare.readyHint}</p>
                </>
              ) : (
                <>
                  <h2>{strings.compare.noStoriesTitle}</h2>
                  <p>{strings.compare.noStoriesBody}</p>
                  <p>{strings.compare.noStoriesHint}</p>
                  <Link to="/" className="btn btn-primary">
                    {strings.common.goToDashboard}
                  </Link>
                </>
              )}
            </div>
          ) : (
            <>
              <div className="comparison-tabs">
                {comparisons.map((comp) => (
                  <button
                    key={comp.story_title}
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
                      {strings.compare.sourcesLabel} {selectedComparison.sources?.join(', ')}
                    </div>
                  </div>

                  <section className="comparison-section">
                    <h3>{strings.compare.storySummary}</h3>
                    <p>{selectedComparison.story_summary}</p>
                  </section>

                  {(selectedComparison.common_facts?.length ?? 0) > 0 && (
                    <section className="comparison-section">
                      <h3>{strings.compare.commonFacts}</h3>
                      <ul className="facts-list">
                        {selectedComparison.common_facts?.map((fact, i) => (
                          <li key={i}>{fact}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {Object.keys(selectedComparison.source_analyses || {}).length > 0 && (
                    <section className="comparison-section">
                      <h3>{strings.compare.sourceBySource}</h3>
                      <div className="source-analyses">
                        {Object.entries(selectedComparison.source_analyses || {}).map(
                          ([source, analysis]) => (
                            <div key={source} className="source-analysis-card">
                              <div className="source-analysis-header">
                                <span className="source-name">{source}</span>
                                <SentimentBadge sentiment={analysis.tone} />
                              </div>
                              <div className="source-analysis-body">
                                <div className="analysis-item">
                                  <strong>{strings.compare.focusLabel}</strong> {analysis.emphasis}
                                </div>
                                {analysis.unique_details &&
                                  analysis.unique_details.toLowerCase() !== 'none' && (
                                    <div className="analysis-item">
                                      <strong>{strings.compare.uniqueDetailsLabel}</strong>{' '}
                                      {analysis.unique_details}
                                    </div>
                                  )}
                                {analysis.potential_bias &&
                                  analysis.potential_bias.toLowerCase() !== 'none' &&
                                  analysis.potential_bias.toLowerCase() !== 'none detected' && (
                                    <div className="analysis-item bias">
                                      <strong>{strings.compare.potentialBiasLabel}</strong>{' '}
                                      {analysis.potential_bias}
                                    </div>
                                  )}
                              </div>
                            </div>
                          ),
                        )}
                      </div>
                    </section>
                  )}

                  {(selectedComparison.key_differences?.length ?? 0) > 0 && (
                    <section className="comparison-section">
                      <h3>{strings.compare.keyDifferences}</h3>
                      <ul className="differences-list">
                        {selectedComparison.key_differences?.map((diff, i) => (
                          <li key={i}>{diff}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {selectedComparison.overall_assessment && (
                    <section className="comparison-section assessment">
                      <h3>{strings.compare.overallAssessment}</h3>
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

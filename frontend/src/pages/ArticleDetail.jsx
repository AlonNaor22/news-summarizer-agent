import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { articlesApi, similarityApi } from '../services/api';
import SentimentBadge from '../components/SentimentBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import './ArticleDetail.css';

function ArticleDetail() {
  const { id } = useParams();
  const [article, setArticle] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadArticle = async () => {
      setLoading(true);
      setError(null);

      try {
        const [articleRes, similarRes] = await Promise.all([
          articlesApi.getById(id),
          similarityApi.getSimilar(id, 0.2, 5)
        ]);

        setArticle(articleRes.data);
        setSimilar(similarRes.data.similar_articles || []);
      } catch (err) {
        setError('Article not found');
        console.error('Error loading article:', err);
      } finally {
        setLoading(false);
      }
    };

    loadArticle();
  }, [id]);

  if (loading) {
    return <LoadingSpinner message="Loading article..." />;
  }

  if (error || !article) {
    return (
      <div className="article-detail-page">
        <div className="error-state">
          <h2>Article Not Found</h2>
          <p>{error || 'The article you are looking for does not exist.'}</p>
          <Link to="/articles" className="btn btn-primary">Back to Articles</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="article-detail-page">
      <div className="back-link">
        <Link to="/articles">Back to Articles</Link>
      </div>

      <article className="article-content">
        <header className="article-header">
          <div className="article-meta-top">
            <span className="article-source">{article.source}</span>
            <span className="article-category">{article.category}</span>
          </div>

          <h1>{article.title}</h1>

          <div className="article-meta-bottom">
            {article.published && (
              <span className="article-date">{article.published}</span>
            )}
            <SentimentBadge sentiment={article.sentiment} />
          </div>
        </header>

        <section className="article-summary">
          <h2>Summary</h2>
          <p>{article.summary}</p>
        </section>

        {article.sentiment_reason && (
          <section className="article-sentiment-reason">
            <h2>Sentiment Analysis</h2>
            <div className="sentiment-detail">
              <SentimentBadge sentiment={article.sentiment} />
              <span className="confidence">
                Confidence: {article.sentiment_confidence}
              </span>
            </div>
            <p>{article.sentiment_reason}</p>
          </section>
        )}

        {(article.keywords?.length > 0 || article.people?.length > 0 ||
          article.organizations?.length > 0 || article.locations?.length > 0) && (
          <section className="article-tags">
            <h2>Tags & Entities</h2>

            {article.keywords?.length > 0 && (
              <div className="tag-group">
                <h3>Keywords</h3>
                <div className="tags">
                  {article.keywords.map((kw, i) => (
                    <Link key={i} to={`/articles?keyword=${encodeURIComponent(kw)}`} className="tag keyword">
                      {kw}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {article.people?.length > 0 && (
              <div className="tag-group">
                <h3>People</h3>
                <div className="tags">
                  {article.people.map((person, i) => (
                    <span key={i} className="tag person">{person}</span>
                  ))}
                </div>
              </div>
            )}

            {article.organizations?.length > 0 && (
              <div className="tag-group">
                <h3>Organizations</h3>
                <div className="tags">
                  {article.organizations.map((org, i) => (
                    <span key={i} className="tag organization">{org}</span>
                  ))}
                </div>
              </div>
            )}

            {article.locations?.length > 0 && (
              <div className="tag-group">
                <h3>Locations</h3>
                <div className="tags">
                  {article.locations.map((loc, i) => (
                    <span key={i} className="tag location">{loc}</span>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {article.url && (
          <section className="article-original">
            <a href={article.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
              Read Original Article
            </a>
          </section>
        )}
      </article>

      {similar.length > 0 && (
        <aside className="similar-articles">
          <h2>Similar Articles</h2>
          <div className="similar-list">
            {similar.map((item) => (
              <Link key={item.id} to={`/articles/${item.id}`} className="similar-item">
                <div className="similar-title">{item.title}</div>
                <div className="similar-meta">
                  <span className="similar-source">{item.source}</span>
                  <span className="similar-score">
                    {Math.round((item.similarity?.overall || 0) * 100)}% similar
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}

export default ArticleDetail;

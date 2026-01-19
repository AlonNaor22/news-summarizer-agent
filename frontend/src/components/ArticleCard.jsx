import { Link } from 'react-router-dom';
import SentimentBadge from './SentimentBadge';
import './ArticleCard.css';

function ArticleCard({ article }) {
  const {
    id,
    title,
    summary,
    source,
    category,
    sentiment,
    published,
    keywords = [],
    url
  } = article;

  return (
    <div className="article-card">
      <div className="article-card-header">
        <span className="article-source">{source}</span>
        <span className="article-category">{category}</span>
      </div>

      <h3 className="article-title">
        <Link to={`/articles/${id}`}>{title}</Link>
      </h3>

      <p className="article-summary">
        {summary?.slice(0, 200)}
        {summary?.length > 200 && '...'}
      </p>

      <div className="article-meta">
        <SentimentBadge sentiment={sentiment} />

        {keywords.length > 0 && (
          <div className="article-keywords">
            {keywords.slice(0, 3).map((kw, i) => (
              <span key={i} className="keyword-tag">{kw}</span>
            ))}
          </div>
        )}
      </div>

      <div className="article-footer">
        {published && <span className="article-date">{published}</span>}
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="article-link">
            Read full article
          </a>
        )}
      </div>
    </div>
  );
}

export default ArticleCard;

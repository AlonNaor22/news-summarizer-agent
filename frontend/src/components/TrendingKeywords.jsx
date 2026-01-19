import './TrendingKeywords.css';

function TrendingKeywords({ keywords, onKeywordClick }) {
  if (!keywords || keywords.length === 0) {
    return <p className="no-keywords">No trending keywords yet</p>;
  }

  const maxCount = Math.max(...keywords.map(k => k.count));

  return (
    <div className="trending-keywords">
      {keywords.map((item, index) => {
        const size = Math.max(0.75, (item.count / maxCount) * 1.25);

        return (
          <button
            key={index}
            className="keyword-pill"
            style={{ fontSize: `${size}rem` }}
            onClick={() => onKeywordClick?.(item.keyword)}
          >
            {item.keyword}
            <span className="keyword-count">{item.count}</span>
          </button>
        );
      })}
    </div>
  );
}

export default TrendingKeywords;

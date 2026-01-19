import './SentimentBadge.css';

function SentimentBadge({ sentiment, showLabel = true }) {
  const getEmoji = () => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return '😊';
      case 'negative':
        return '😟';
      case 'neutral':
      default:
        return '😐';
    }
  };

  const getClass = () => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'sentiment-badge positive';
      case 'negative':
        return 'sentiment-badge negative';
      case 'neutral':
      default:
        return 'sentiment-badge neutral';
    }
  };

  return (
    <span className={getClass()}>
      <span className="sentiment-emoji">{getEmoji()}</span>
      {showLabel && <span className="sentiment-label">{sentiment || 'Unknown'}</span>}
    </span>
  );
}

export default SentimentBadge;

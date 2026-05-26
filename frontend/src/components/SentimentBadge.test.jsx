import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SentimentBadge from './SentimentBadge';

describe('SentimentBadge', () => {
  test('renders "positive" label and 😊 emoji when sentiment="positive"', () => {
    render(<SentimentBadge sentiment="positive" />);
    expect(screen.getByText('😊')).toBeInTheDocument();
    expect(screen.getByText('positive')).toBeInTheDocument();
  });

  test('renders "Unknown" when sentiment is undefined', () => {
    render(<SentimentBadge />);
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  test('renders "negative" label and 😟 emoji when sentiment="negative"', () => {
    render(<SentimentBadge sentiment="negative" />);
    expect(screen.getByText('😟')).toBeInTheDocument();
    expect(screen.getByText('negative')).toBeInTheDocument();
  });

  test('hides label when showLabel=false', () => {
    render(<SentimentBadge sentiment="positive" showLabel={false} />);
    expect(screen.queryByText('positive')).not.toBeInTheDocument();
    expect(screen.getByText('😊')).toBeInTheDocument();
  });
});

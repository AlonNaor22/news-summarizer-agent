import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import ArticleCard from './ArticleCard';
import type { Article } from '../types';
import { strings } from '../strings';

const baseArticle: Article = {
  id: 3,
  title: 'Breaking: AI does something',
  summary: 'A concise summary of the article body.',
  source: 'BBC News',
  category: 'Technology',
  sentiment: 'positive',
  keywords: ['ai', 'research', 'policy', 'extra'],
  url: 'https://example.com/article',
};

function renderCard(overrides: Partial<Article> = {}) {
  return render(
    <MemoryRouter>
      <ArticleCard article={{ ...baseArticle, ...overrides }} />
    </MemoryRouter>,
  );
}

describe('ArticleCard', () => {
  test('renders the core article fields', () => {
    renderCard();
    expect(screen.getByText('Breaking: AI does something')).toBeInTheDocument();
    expect(screen.getByText('BBC News')).toBeInTheDocument();
    expect(screen.getByText('Technology')).toBeInTheDocument();
    expect(screen.getByText('positive')).toBeInTheDocument(); // sentiment badge label
  });

  test('shows at most the first three keywords', () => {
    renderCard();
    expect(screen.getByText('ai')).toBeInTheDocument();
    expect(screen.getByText('research')).toBeInTheDocument();
    expect(screen.getByText('policy')).toBeInTheDocument();
    expect(screen.queryByText('extra')).not.toBeInTheDocument();
  });

  test('links to the detail page and opens the original in a new tab', () => {
    renderCard();

    const detailLink = screen.getByRole('link', { name: 'Breaking: AI does something' });
    expect(detailLink).toHaveAttribute('href', '/articles/3');

    const sourceLink = screen.getByRole('link', { name: strings.articleCard.readFull });
    expect(sourceLink).toHaveAttribute('href', 'https://example.com/article');
    expect(sourceLink).toHaveAttribute('target', '_blank');
    expect(sourceLink).toHaveAttribute('rel', 'noopener noreferrer');
  });
});

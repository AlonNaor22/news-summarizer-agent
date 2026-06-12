import { useState } from 'react';
import './SearchBar.css';

interface Props {
  onSearch: (query: string) => void;
  placeholder?: string;
}

function SearchBar({ onSearch, placeholder = 'Search articles...' }: Props) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        className="search-input"
        placeholder={placeholder}
        aria-label={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button type="submit" className="search-button">
        Search
      </button>
    </form>
  );
}

export default SearchBar;

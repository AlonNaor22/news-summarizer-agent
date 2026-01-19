import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { qaApi } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import './Chat.css';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadStatus();
    loadHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadStatus = async () => {
    try {
      const response = await qaApi.getStatus();
      setStatus(response.data);
    } catch (err) {
      console.error('Error loading status:', err);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await qaApi.getHistory();
      setMessages(response.data.history || []);
    } catch (err) {
      console.error('Error loading history:', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      const response = await qaApi.ask(question);

      // Add assistant response
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.answer }]);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Sorry, something went wrong.';
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${errorMessage}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await qaApi.clearHistory();
      setMessages([]);
    } catch (err) {
      console.error('Error clearing history:', err);
    }
  };

  const suggestedQuestions = [
    "What are the main technology news today?",
    "Which articles have negative sentiment?",
    "Summarize the business news",
    "What topics are most covered?",
    "Compare different news sources"
  ];

  const handleSuggestion = (question) => {
    setInput(question);
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-title">
            <h1>Chat with News</h1>
            {status?.articles_loaded > 0 && (
              <span className="article-count">
                {status.articles_loaded} articles loaded
              </span>
            )}
          </div>

          {messages.length > 0 && (
            <button className="btn-clear" onClick={handleClearHistory}>
              Clear Chat
            </button>
          )}
        </div>

        {!status?.ready ? (
          <div className="chat-empty">
            <div className="empty-icon">💬</div>
            <h2>No Articles Loaded</h2>
            <p>Fetch some news articles first to start chatting about them.</p>
            <Link to="/" className="btn btn-primary">Go to Dashboard</Link>
          </div>
        ) : (
          <>
            <div className="messages-container">
              {messages.length === 0 && (
                <div className="chat-welcome">
                  <h2>Ask questions about your news</h2>
                  <p>I can help you understand, compare, and analyze the articles you've fetched.</p>

                  <div className="suggestions">
                    <p className="suggestions-label">Try asking:</p>
                    <div className="suggestion-buttons">
                      {suggestedQuestions.map((q, i) => (
                        <button
                          key={i}
                          className="suggestion-btn"
                          onClick={() => handleSuggestion(q)}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === 'user' ? '👤' : '🤖'}
                  </div>
                  <div className="message-content">
                    {msg.content}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message assistant">
                  <div className="message-avatar">🤖</div>
                  <div className="message-content typing">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-form" onSubmit={handleSubmit}>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about the news..."
                disabled={loading}
                className="chat-input"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="send-button"
              >
                {loading ? '...' : 'Send'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export default Chat;

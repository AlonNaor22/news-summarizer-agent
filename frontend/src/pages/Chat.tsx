import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { qaApi } from '../services/api';
import type { ChatMessage, QaStatus } from '../types';
import './Chat.css';

function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<QaStatus | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  const appendToLastAssistant = (chunk: string) => {
    setMessages(prev => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.role !== 'assistant') return prev;
      const updated = [...prev];
      updated[updated.length - 1] = { role: 'assistant', content: last.content + chunk };
      return updated;
    });
  };

  const replaceLastAssistant = (content: string) => {
    setMessages(prev => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.role !== 'assistant') return prev;
      const updated = [...prev];
      updated[updated.length - 1] = { role: 'assistant', content };
      return updated;
    });
  };

  const askNonStreaming = async (question: string): Promise<string> => {
    const response = await qaApi.ask(question);
    return response.data.answer;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');

    setMessages(prev => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '' },
    ]);
    setLoading(true);

    let receivedAnyChunk = false;
    let streamErrorDetail: string | null = null;

    try {
      await qaApi.askStream(question, {
        onChunk: (text) => {
          receivedAnyChunk = true;
          appendToLastAssistant(text);
        },
        onError: (detail) => {
          streamErrorDetail = detail;
        },
      });
    } catch (err) {
      streamErrorDetail = err instanceof Error ? err.message : 'Streaming failed.';
    }

    if (streamErrorDetail && !receivedAnyChunk) {
      try {
        const answer = await askNonStreaming(question);
        replaceLastAssistant(answer);
      } catch (fallbackErr) {
        const detail = axios.isAxiosError(fallbackErr)
          ? fallbackErr.response?.data?.detail
          : null;
        const errorMessage = detail || streamErrorDetail || 'Sorry, something went wrong.';
        replaceLastAssistant(`Error: ${errorMessage}`);
      }
    } else if (streamErrorDetail) {
      appendToLastAssistant(`\n\n[Error mid-stream: ${streamErrorDetail}]`);
    }

    setLoading(false);
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

  const handleSuggestion = (question: string) => {
    setInput(question);
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-title">
            <h1>Chat with News</h1>
            {(status?.articles_loaded ?? 0) > 0 && (
              <span className="article-count">
                {status?.articles_loaded} articles loaded
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
                      {suggestedQuestions.map((q) => (
                        <button
                          key={q}
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

              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1;
                const isStreamingPlaceholder =
                  loading && isLast && msg.role === 'assistant' && msg.content === '';
                return (
                  <div key={i} className={`message ${msg.role}`}>
                    <div className="message-avatar">
                      {msg.role === 'user' ? '👤' : '🤖'}
                    </div>
                    {isStreamingPlaceholder ? (
                      <div className="message-content typing">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    ) : (
                      <div className="message-content">{msg.content}</div>
                    )}
                  </div>
                );
              })}

              <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-form" onSubmit={handleSubmit}>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about the news..."
                aria-label="Ask a question about the news"
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

import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { qaApi } from '../services/api';
import type { ChatMessage, QaStatus } from '../types';
import { strings } from '../strings';
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
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.role !== 'assistant') return prev;
      const updated = [...prev];
      updated[updated.length - 1] = { role: 'assistant', content: last.content + chunk };
      return updated;
    });
  };

  const replaceLastAssistant = (content: string) => {
    setMessages((prev) => {
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

    setMessages((prev) => [
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
      streamErrorDetail = err instanceof Error ? err.message : strings.chat.streamingFailed;
    }

    if (streamErrorDetail && !receivedAnyChunk) {
      try {
        const answer = await askNonStreaming(question);
        replaceLastAssistant(answer);
      } catch (fallbackErr) {
        const detail = axios.isAxiosError(fallbackErr) ? fallbackErr.response?.data?.detail : null;
        const errorMessage = detail || streamErrorDetail || strings.chat.genericError;
        replaceLastAssistant(strings.chat.errorPrefix(errorMessage));
      }
    } else if (streamErrorDetail) {
      appendToLastAssistant(strings.chat.midStreamError(streamErrorDetail));
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

  const suggestedQuestions = strings.chat.suggestedQuestions;

  const handleSuggestion = (question: string) => {
    setInput(question);
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-title">
            <h1>{strings.chat.title}</h1>
            {(status?.articles_loaded ?? 0) > 0 && (
              <span className="article-count">
                {strings.chat.articlesLoaded(status?.articles_loaded ?? 0)}
              </span>
            )}
          </div>

          {messages.length > 0 && (
            <button className="btn-clear" onClick={handleClearHistory}>
              {strings.chat.clearChat}
            </button>
          )}
        </div>

        {!status?.ready ? (
          <div className="chat-empty">
            <div className="empty-icon">💬</div>
            <h2>{strings.chat.noArticlesTitle}</h2>
            <p>{strings.chat.noArticlesBody}</p>
            <Link to="/" className="btn btn-primary">
              {strings.common.goToDashboard}
            </Link>
          </div>
        ) : (
          <>
            <div className="messages-container">
              {messages.length === 0 && (
                <div className="chat-welcome">
                  <h2>{strings.chat.welcomeTitle}</h2>
                  <p>{strings.chat.welcomeBody}</p>

                  <div className="suggestions">
                    <p className="suggestions-label">{strings.chat.tryAsking}</p>
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
                    <div className="message-avatar">{msg.role === 'user' ? '👤' : '🤖'}</div>
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
                placeholder={strings.chat.inputPlaceholder}
                aria-label={strings.chat.inputLabel}
                disabled={loading}
                className="chat-input"
              />
              <button type="submit" disabled={loading || !input.trim()} className="send-button">
                {loading ? strings.chat.sending : strings.chat.send}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export default Chat;

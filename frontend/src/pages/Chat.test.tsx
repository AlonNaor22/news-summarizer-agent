import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, test, expect, beforeAll, beforeEach } from 'vitest';

// Chat depends on the API client; replace it with controllable mocks.
vi.mock('../services/api', () => ({
  qaApi: {
    getStatus: vi.fn(),
    getHistory: vi.fn(),
    askStream: vi.fn(),
    ask: vi.fn(),
    clearHistory: vi.fn(),
  },
}));

import { qaApi } from '../services/api';
import Chat from './Chat';
import { strings } from '../strings';

beforeAll(() => {
  // jsdom doesn't implement scrollIntoView; Chat calls it on every message change.
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
  vi.clearAllMocks();
  (qaApi.getStatus as any).mockResolvedValue({
    data: { articles_loaded: 2, history_length: 0, ready: true },
  });
  (qaApi.getHistory as any).mockResolvedValue({
    data: { history: [], message_count: 0 },
  });
});

function renderChat() {
  return render(
    <MemoryRouter>
      <Chat />
    </MemoryRouter>,
  );
}

describe('Chat', () => {
  test('falls back to the non-streaming answer when the stream fails before any chunk', async () => {
    // Stream reports an error and never delivers a chunk.
    (qaApi.askStream as any).mockImplementation(
      async (_question: string, callbacks: { onError?: (d: string) => void }) => {
        callbacks.onError?.('stream down');
      },
    );
    (qaApi.ask as any).mockResolvedValue({
      data: { answer: 'Fallback answer' },
    });

    renderChat();

    const input = await screen.findByLabelText(strings.chat.inputLabel);
    fireEvent.change(input, { target: { value: 'What happened?' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Fallback answer')).toBeInTheDocument();
    });
    expect(qaApi.ask).toHaveBeenCalledWith('What happened?');
  });

  test('renders streamed chunks directly without invoking the fallback', async () => {
    (qaApi.askStream as any).mockImplementation(
      async (_question: string, callbacks: { onChunk: (t: string) => void; onDone?: (i: unknown) => void }) => {
        callbacks.onChunk('Streamed ');
        callbacks.onChunk('answer');
        callbacks.onDone?.({ article_count: 2 });
      },
    );

    renderChat();

    const input = await screen.findByLabelText(strings.chat.inputLabel);
    fireEvent.change(input, { target: { value: 'Tell me' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Streamed answer')).toBeInTheDocument();
    });
    expect(qaApi.ask).not.toHaveBeenCalled();
  });
});

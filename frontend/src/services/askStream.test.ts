import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';
import { qaApi } from './api';

// Build a fake streaming Response whose body yields the given strings as
// successive `reader.read()` results — one network chunk per array entry.
function makeReader(chunks: string[]) {
  const encoder = new TextEncoder();
  let i = 0;
  return {
    read: vi.fn(async () => {
      if (i < chunks.length) {
        const value = encoder.encode(chunks[i]);
        i += 1;
        return { value, done: false };
      }
      return { value: undefined, done: true };
    }),
    releaseLock: vi.fn(),
  };
}

function streamingResponse(chunks: string[]) {
  return {
    ok: true,
    status: 200,
    headers: { get: () => null },
    body: { getReader: () => makeReader(chunks) },
  };
}

function stubFetch(response: unknown) {
  vi.stubGlobal('fetch', vi.fn(async () => response));
}

describe('qaApi.askStream', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('emits one chunk per token, then done with the article count', async () => {
    stubFetch(
      streamingResponse([
        'event: chunk\ndata: {"text": "Hello "}\n\n' +
          'event: chunk\ndata: {"text": "world"}\n\n' +
          'event: done\ndata: {"article_count": 2}\n\n',
      ]),
    );

    const onChunk = vi.fn();
    const onDone = vi.fn();
    await qaApi.askStream('hi', { onChunk, onDone });

    expect(onChunk.mock.calls.map((c) => c[0])).toEqual(['Hello ', 'world']);
    expect(onDone).toHaveBeenCalledWith({ article_count: 2 });
  });

  test('reassembles a single SSE message split across two reads', async () => {
    // The chunk message is cut mid-JSON; the boundary + done arrive next read.
    stubFetch(
      streamingResponse([
        'event: chunk\ndata: {"text": "par',
        'tial"}\n\nevent: done\ndata: {"article_count": 1}\n\n',
      ]),
    );

    const onChunk = vi.fn();
    const onDone = vi.fn();
    await qaApi.askStream('hi', { onChunk, onDone });

    expect(onChunk).toHaveBeenCalledTimes(1);
    expect(onChunk).toHaveBeenCalledWith('partial');
    expect(onDone).toHaveBeenCalledWith({ article_count: 1 });
  });

  test('routes an error event to onError and stops before done', async () => {
    stubFetch(
      streamingResponse([
        'event: chunk\ndata: {"text": "x"}\n\n' +
          'event: error\ndata: {"detail": "boom"}\n\n' +
          'event: done\ndata: {"article_count": 9}\n\n',
      ]),
    );

    const onChunk = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();
    await qaApi.askStream('hi', { onChunk, onDone, onError });

    expect(onChunk).toHaveBeenCalledWith('x');
    expect(onError).toHaveBeenCalledWith('boom');
    expect(onDone).not.toHaveBeenCalled();
  });

  test('ignores SSE comment / heartbeat lines', async () => {
    stubFetch(
      streamingResponse([
        ': keep-alive\n\n' +
          'event: chunk\ndata: {"text": "ok"}\n\n' +
          'event: done\ndata: {"article_count": 0}\n\n',
      ]),
    );

    const onChunk = vi.fn();
    const onDone = vi.fn();
    await qaApi.askStream('hi', { onChunk, onDone });

    expect(onChunk).toHaveBeenCalledTimes(1);
    expect(onChunk).toHaveBeenCalledWith('ok');
    expect(onDone).toHaveBeenCalledWith({ article_count: 0 });
  });

  test('rejects with the backend detail on a non-ok response', async () => {
    stubFetch({
      ok: false,
      status: 400,
      headers: { get: () => null },
      json: async () => ({ detail: 'No articles loaded. Please fetch articles first.' }),
    });

    await expect(qaApi.askStream('hi', { onChunk: vi.fn() })).rejects.toThrow(
      'No articles loaded. Please fetch articles first.',
    );
  });

  test('rejects when the response has no readable body', async () => {
    stubFetch({
      ok: true,
      status: 200,
      headers: { get: () => null },
      body: null,
    });

    await expect(qaApi.askStream('hi', { onChunk: vi.fn() })).rejects.toThrow(
      'Streaming not supported',
    );
  });
});

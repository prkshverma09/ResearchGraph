import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError } from '@/lib/api';

describe('API Client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('search', () => {
    it('should return papers from search endpoint', async () => {
      const mockPapers = [
        {
          title: 'Test Paper 1',
          abstract: 'Abstract 1',
          paper_id: 'paper1',
          relevance_score: 0.95,
        },
        {
          title: 'Test Paper 2',
          abstract: 'Abstract 2',
          paper_id: 'paper2',
          relevance_score: 0.85,
        },
      ];

      const mockResponse = {
        ok: true,
        json: async () => ({ papers: mockPapers }),
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse as Response);

      const result = await api.search('test query', 5);

      expect(result.papers).toHaveLength(2);
      expect(result.papers[0].title).toBe('Test Paper 1');
      expect(result.papers[0].paper_id).toBe('paper1');
      expect(result.papers[1].title).toBe('Test Paper 2');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/search'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ query: 'test query', top_k: 5 }),
        })
      );
    });

    it('should handle API errors', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Server error' }),
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse as Response);

      await expect(api.search('test query')).rejects.toThrow(ApiError);
    });
  });

  describe('askStream', () => {
    it('should stream response chunks', async () => {
      const mockChunks = [
        'data: {"type":"chunk","chunk":"Hello"}\n',
        'data: {"type":"chunk","chunk":" World"}\n',
        'data: {"type":"done"}\n',
      ];

      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < mockChunks.length) {
            const chunk = mockChunks[chunkIndex++];
            return Promise.resolve({
              done: false,
              value: new TextEncoder().encode(chunk),
            });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
        releaseLock: vi.fn(),
      };

      const mockBody = {
        getReader: () => mockReader,
      };

      const mockResponse = {
        ok: true,
        body: mockBody,
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse as Response);

      const chunks: string[] = [];
      for await (const chunk of api.askStream('test question')) {
        if (chunk.chunk) {
          chunks.push(chunk.chunk);
        }
      }

      expect(chunks).toEqual(['Hello', ' World']);
      expect(mockReader.releaseLock).toHaveBeenCalled();
    });

    it('should handle streaming errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const mockChunks = [
        'data: {"type":"error","error":"Stream error"}\n',
        'data: {"type":"done"}\n',
      ];
      
      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < mockChunks.length) {
            const chunk = mockChunks[chunkIndex++];
            return Promise.resolve({
              done: false,
              value: new TextEncoder().encode(chunk),
            });
          }
          return Promise.resolve({ done: true, value: undefined });
        }),
        releaseLock: vi.fn(),
      };

      const mockBody = {
        getReader: () => mockReader,
      };

      const mockResponse = {
        ok: true,
        body: mockBody,
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse as Response);

      const chunks: any[] = [];
      for await (const chunk of api.askStream('test question')) {
        chunks.push(chunk);
      }
      
      expect(chunks).toHaveLength(0);
      expect(consoleSpy).toHaveBeenCalled();
      expect(mockReader.releaseLock).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });

    it('should handle non-ok response', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
      };

      global.fetch = vi.fn().mockResolvedValue(mockResponse as Response);

      await expect(async () => {
        for await (const _ of api.askStream('test question')) {
          // consume stream
        }
      }).rejects.toThrow(ApiError);
    });
  });
});

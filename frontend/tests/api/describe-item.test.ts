/**
 * @jest-environment node
 */

import { POST } from '@/app/api/ai/describe-item/route';
import { NextRequest } from 'next/server';
import { createClient } from '@/utils/supabase/server';
import { redis } from '@/lib/redis';

jest.mock('@/utils/supabase/server', () => ({
  createClient: jest.fn(),
}));

jest.mock('@/lib/redis', () => ({
  redis: {
    get: jest.fn(),
    incr: jest.fn(),
    decr: jest.fn(),
    expire: jest.fn(),
  },
}));

describe('Describe Item API Route Handler Tests', () => {
  let mockSupabase: any;
  let originalEnv: NodeJS.ProcessEnv;

  beforeAll(() => {
    originalEnv = { ...process.env };
    process.env.OPENROUTER_API_KEY = 'mock-key';
    process.env.OPENROUTER_BASE_URL = 'https://mock.openrouter.ai';
    process.env.OPENROUTER_MODEL = 'google/gemma-2-9b-it:free';
    process.env.AI_DAILY_RATE_LIMIT = '10';
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();

    // Mock Supabase
    mockSupabase = {
      auth: {
        getSession: jest.fn(),
      },
    };
    (createClient as jest.Mock).mockResolvedValue(mockSupabase);
  });

  function createMockRequest(body: any) {
    return new NextRequest(new URL('http://localhost:3000/api/ai/describe-item'), {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  it('should return 401 when no user session is active', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({ data: { session: null } });

    const req = createMockRequest({ title: 'Chair' });
    const res = await POST(req);

    expect(res.status).toBe(401);
    const data = await res.json();
    expect(data.error).toBe('Unauthorized');
  });

  it('should return 400 when title is missing or empty', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });

    // Empty title
    const req1 = createMockRequest({ title: '' });
    const res1 = await POST(req1);
    expect(res1.status).toBe(400);

    // Missing title
    const req2 = createMockRequest({ notes: 'Only notes' });
    const res2 = await POST(req2);
    expect(res2.status).toBe(400);
  });

  it('should return 429 when daily rate limit has already been reached', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });

    // Mock Redis to return 10 (the limit)
    (redis.get as jest.Mock).mockResolvedValue('10');

    const req = createMockRequest({ title: 'Sofa' });
    const res = await POST(req);

    expect(res.status).toBe(429);
    const data = await res.json();
    expect(data.error).toBe('Daily AI limit reached');
  });

  it('should return 429 on concurrent calls that breach the limit boundary', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });

    // Mock Redis get to return '9' (under limit of 10)
    (redis.get as jest.Mock).mockResolvedValue('9');
    // Mock Redis incr to return '11' (the second concurrent call increments it past 10)
    (redis.incr as jest.Mock).mockResolvedValue(11);

    const req = createMockRequest({ title: 'Sofa' });
    const res = await POST(req);

    expect(res.status).toBe(429);
    // Verifies decrement is called to refund the concurrent count
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 503 when OpenRouter is unreachable or returns non-200 status', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    // Mock Fetch to return 500 error from OpenRouter
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
    });

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);

    expect(res.status).toBe(503);
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 422 when OpenRouter returns non-conforming JSON structure', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    // Mock OpenRouter returning invalid keys (no condition)
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                description: 'A great book.',
                category: 'books',
                // missing condition
              }),
            },
          },
        ],
      }),
    });

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);

    expect(res.status).toBe(422);
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 200 with generated item details on successful happy path', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    // Mock OpenRouter successful response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                description: 'A comfortable wooden chair in excellent condition.',
                category: 'furniture',
                condition: 'good',
              }),
            },
          },
        ],
      }),
    });

    const req = createMockRequest({ title: 'Wooden Chair' });
    const res = await POST(req);

    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data).toEqual({
      description: 'A comfortable wooden chair in excellent condition.',
      category: 'furniture',
      condition: 'good',
    });

    // Counter incr and expire should be called
    expect(redis.incr).toHaveBeenCalled();
    expect(redis.expire).toHaveBeenCalledWith(expect.any(String), 86400);
    expect(redis.decr).not.toHaveBeenCalled();
  });

  it('should not leak the OpenRouter API Key in any client response', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                description: 'Book info',
                category: 'books',
                condition: 'good',
              }),
            },
          },
        ],
      }),
    });

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);

    const bodyString = await res.text();
    expect(bodyString).not.toContain('mock-key');
  });

  it('should return 400 when request body is invalid JSON', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    const req = {
      json: () => Promise.reject(new Error('Invalid JSON')),
    } as unknown as NextRequest;
    const res = await POST(req);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe('Invalid JSON request body');
  });

  it('should return 503 when OPENROUTER_API_KEY is not configured', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    const oldKey = process.env.OPENROUTER_API_KEY;
    delete process.env.OPENROUTER_API_KEY;

    try {
      const req = createMockRequest({ title: 'Book' });
      const res = await POST(req);
      expect(res.status).toBe(503);
      const data = await res.json();
      expect(data.error).toBe('OpenRouter API key is not configured');
      expect(redis.decr).toHaveBeenCalled();
    } finally {
      process.env.OPENROUTER_API_KEY = oldKey;
    }
  });

  it('should return 503 when OpenRouter fetch throws an error', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);
    expect(res.status).toBe(503);
    const data = await res.json();
    expect(data.error).toBe('OpenRouter is unreachable');
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 503 when OpenRouter returns invalid non-JSON response structure', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.reject(new Error('JSON parse error')),
    });

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);
    expect(res.status).toBe(503);
    const data = await res.json();
    expect(data.error).toBe('OpenRouter returned malformed data');
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 503 when OpenRouter choices content is empty', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ choices: [] }),
    });

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);
    expect(res.status).toBe(503);
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 422 when OpenRouter choice content is not valid JSON string', async () => {
    mockSupabase.auth.getSession.mockResolvedValue({
      data: { session: { user: { id: 'user123' } } },
    });
    (redis.get as jest.Mock).mockResolvedValue('0');
    (redis.incr as jest.Mock).mockResolvedValue(1);

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: 'this is not JSON at all',
            },
          },
        ],
      }),
    });

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);
    expect(res.status).toBe(422);
    const data = await res.json();
    expect(data.error).toBe('OpenRouter response is not valid JSON');
    expect(redis.decr).toHaveBeenCalled();
  });

  it('should return 500 when an unexpected global error occurs', async () => {
    mockSupabase.auth.getSession.mockRejectedValue(new Error('Global DB failure'));

    const req = createMockRequest({ title: 'Book' });
    const res = await POST(req);
    expect(res.status).toBe(500);
    const data = await res.json();
    expect(data.error).toBe('Internal server error');
  });
});


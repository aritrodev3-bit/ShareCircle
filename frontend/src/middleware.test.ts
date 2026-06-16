/**
 * @jest-environment node
 */

import { middleware } from './middleware';
import { NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';

jest.mock('@supabase/ssr', () => ({
  createServerClient: jest.fn(),
}));

describe('Middleware Tests', () => {
  let mockSupabase: any;

  beforeAll(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://mock.supabase.co';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'mock-anon-key';
  });

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up mock Supabase client
    mockSupabase = {
      auth: {
        getUser: jest.fn(),
      },
    };
    (createServerClient as jest.Mock).mockReturnValue(mockSupabase);
  });

  // Helper to create a NextRequest
  function createMockRequest(path: string, cookies: Record<string, string> = {}) {
    const url = new URL(`http://localhost:3000${path}`);
    const req = new NextRequest(url);
    
    // Mock cookies
    for (const [key, value] of Object.entries(cookies)) {
      req.cookies.set(key, value);
    }
    
    return req;
  }

  it('should redirect unauthenticated users from private routes to /login', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null });

    const req = createMockRequest('/donor/listings');
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307); // NextResponse.redirect defaults to 307
    expect(res.headers.get('location')).toBe('http://localhost:3000/login');
  });

  it('should allow unauthenticated users to access public pages', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: null }, error: null });

    const req = createMockRequest('/login');
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.headers.get('location')).toBeNull();
  });

  it('should redirect authenticated users from /login to /browse', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'user123' } }, error: null });

    const req = createMockRequest('/login');
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3000/browse');
  });

  it('should allow donor to access donor routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'donor123' } }, error: null });

    const req = createMockRequest('/donor/listings', { 'user-role': 'donor' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.headers.get('location')).toBeNull();
  });

  it('should redirect donor trying to access NGO dashboard to /browse', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'donor123' } }, error: null });

    const req = createMockRequest('/ngo/dashboard', { 'user-role': 'donor' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3000/browse');
  });

  it('should allow NGO to access NGO routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'ngo123' } }, error: null });

    const req = createMockRequest('/ngo/dashboard', { 'user-role': 'ngo' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.headers.get('location')).toBeNull();
  });

  it('should redirect NGO trying to access donor routes to /browse', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'ngo123' } }, error: null });

    const req = createMockRequest('/donor/listings', { 'user-role': 'ngo' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3000/browse');
  });

  it('should allow admin to access admin routes', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'admin123' } }, error: null });

    const req = createMockRequest('/admin/analytics', { 'user-role': 'admin' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.headers.get('location')).toBeNull();
  });

  it('should redirect admin trying to access donor routes to /browse', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'admin123' } }, error: null });

    const req = createMockRequest('/donor/listings', { 'user-role': 'admin' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3000/browse');
  });

  it('should redirect authenticated users with null/missing role cookie to /onboarding', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'user123' } }, error: null });

    // 1. Missing cookie
    const req1 = createMockRequest('/browse');
    const res1 = await middleware(req1);
    expect(res1).toBeDefined();
    expect(res1.status).toBe(307);
    expect(res1.headers.get('location')).toBe('http://localhost:3000/onboarding');

    // 2. Cookie is 'null'
    const req2 = createMockRequest('/browse', { 'user-role': 'null' });
    const res2 = await middleware(req2);
    expect(res2).toBeDefined();
    expect(res2.status).toBe(307);
    expect(res2.headers.get('location')).toBe('http://localhost:3000/onboarding');
  });

  it('should allow authenticated users without role cookie to access /onboarding', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'user123' } }, error: null });

    const req = createMockRequest('/onboarding');
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.headers.get('location')).toBeNull();
  });

  it('should redirect non-admin trying to access admin routes to /browse', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'donor123' } }, error: null });

    const req = createMockRequest('/admin/analytics', { 'user-role': 'donor' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3000/browse');
  });

  it('should redirect donor trying to access requests routes to /browse', async () => {
    mockSupabase.auth.getUser.mockResolvedValue({ data: { user: { id: 'donor123' } }, error: null });

    const req = createMockRequest('/requests', { 'user-role': 'donor' });
    const res = await middleware(req);

    expect(res).toBeDefined();
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost:3000/browse');
  });
});

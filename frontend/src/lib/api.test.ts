import {
  apiRequest,
  ApiError,
  register,
  login,
  getMe,
  updateProfile,
  updatePreferences,
  createItem,
  getItems,
  getItem,
  updateItem,
  deleteItem,
  createRequest,
  getIncomingRequests,
  getOutgoingRequests,
  approveRequest,
  rejectRequest,
  confirmPickup,
  cancelRequest,
  getAnalyticsSummary,
  getCategoryBreakdown,
  getDonationTrends,
  getTopCities,
  getPlatformActivity,
  getSuggestions,
  getClientToken,
} from './api';

function clearCookies() {
  if (typeof document !== 'undefined') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i];
      const eqPos = cookie.indexOf('=');
      const name = eqPos > -1 ? cookie.substring(0, eqPos).trim() : cookie.trim();
      document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
    }
  }
}

describe('API Wrapper Tests', () => {
  let originalFetch: typeof global.fetch;
  let mockFetch: jest.Mock;

  beforeEach(() => {
    originalFetch = global.fetch;
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    clearCookies();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    clearCookies();
  });

  describe('getClientToken', () => {
    it('should return undefined if window is undefined', () => {
      const originalWindow = global.window;
      // Temporarily delete window
      // @ts-ignore
      delete global.window;

      expect(getClientToken()).toBeUndefined();

      // Restore
      global.window = originalWindow;
    });

    it('should extract access_token from supabase cookie correctly', () => {
      document.cookie = 'sb-test-auth-token=' + encodeURIComponent(
        JSON.stringify({ access_token: 'test-token-123' })
      );
      expect(getClientToken()).toBe('test-token-123');
    });

    it('should extract nested access_token from session object in supabase cookie', () => {
      document.cookie = 'sb-anotherproject-auth-token=' + encodeURIComponent(
        JSON.stringify({ session: { access_token: 'nested-token-456' } })
      );
      expect(getClientToken()).toBe('nested-token-456');
    });

    it('should return undefined if cookie does not match regex', () => {
      document.cookie = 'some-other-cookie=hello';
      expect(getClientToken()).toBeUndefined();
    });

    it('should return undefined if cookie JSON is invalid', () => {
      document.cookie = 'sb-project-auth-token=invalid-json';
      expect(getClientToken()).toBeUndefined();
    });
  });

  describe('apiRequest base functionality', () => {
    it('should perform a successful GET fetch request', async () => {
      const mockResponseData = { data: 'hello' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponseData,
      } as Response);

      const result = await apiRequest<{ data: string }>('/test-path');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [calledUrl, calledConfig] = mockFetch.mock.calls[0];
      expect(calledUrl).toBe('http://localhost:8000/test-path');
      expect(calledConfig.method).toBeUndefined();
      expect(calledConfig.headers).toBeInstanceOf(Headers);
      expect(result).toEqual(mockResponseData);
    });

    it('should inject explicit token in Authorization header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await apiRequest('/test-path', { token: 'explicit-token' });

      const calledHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(calledHeaders.get('Authorization')).toBe('Bearer explicit-token');
    });

    it('should inject cookie token if no explicit token is passed', async () => {
      document.cookie = 'sb-project-auth-token=' + encodeURIComponent(
        JSON.stringify({ access_token: 'cookie-token' })
      );
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await apiRequest('/test-path');

      const calledHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(calledHeaders.get('Authorization')).toBe('Bearer cookie-token');
    });

    it('should prioritize explicit token over cookie token', async () => {
      document.cookie = 'sb-project-auth-token=' + encodeURIComponent(
        JSON.stringify({ access_token: 'cookie-token' })
      );
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await apiRequest('/test-path', { token: 'explicit-token' });

      const calledHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(calledHeaders.get('Authorization')).toBe('Bearer explicit-token');
    });

    it('should set Content-Type header to application/json by default for bodies', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await apiRequest('/test-path', {
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      });

      const calledHeaders = mockFetch.mock.calls[0][1].headers as Headers;
      expect(calledHeaders.get('Content-Type')).toBe('application/json');
    });

    it('should return empty object on 204 No Content', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      } as Response);

      const result = await apiRequest('/test-path');
      expect(result).toEqual({});
    });

    it('should throw ApiError when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Something went wrong' }),
      } as Response);

      await expect(apiRequest('/test-path')).rejects.toThrow(ApiError);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Something went wrong' }),
      } as Response);

      try {
        await apiRequest('/test-path');
      } catch (err: any) {
        expect(err.status).toBe(400);
        expect(err.message).toBe('Something went wrong');
        expect(err.detail).toBe('Something went wrong');
      }
    });

    it('should format array FastAPI validation details', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({
          detail: [
            { msg: 'Field is required', loc: ['body', 'title'] },
            { msg: 'Must be positive', loc: ['body', 'quantity'] },
          ],
        }),
      } as Response);

      try {
        await apiRequest('/test-path');
      } catch (err: any) {
        expect(err.status).toBe(422);
        expect(err.message).toBe('Field is required, Must be positive');
      }
    });

    it('should handle custom error structures correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ message: 'Conflict occurred' }),
      } as Response);

      try {
        await apiRequest('/test-path');
      } catch (err: any) {
        expect(err).toBeInstanceOf(ApiError);
        expect(err.status).toBe(409);
        expect(err.message).toBe('Conflict occurred');
      }
    });
  });

  describe('Auth Methods', () => {
    it('register should make a POST request with correct payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({ id: 1 }),
      } as Response);

      const payload = {
        email: 'test@example.com',
        password: 'password123',
        full_name: 'John Doe',
        role: 'donor' as const,
      };

      await register(payload);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/register',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(payload),
        })
      );
    });

    it('login should use x-www-form-urlencoded params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: 'tok', token_type: 'bearer' }),
      } as Response);

      await login('myusername', 'mypassword');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(URLSearchParams),
        })
      );

      const calledBody = mockFetch.mock.calls[0][1].body as URLSearchParams;
      expect(calledBody.get('username')).toBe('myusername');
      expect(calledBody.get('password')).toBe('mypassword');
    });

    it('getMe should make GET request with token', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 1 }),
      } as Response);

      await getMe('tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/me',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('updatePreferences should make PATCH request with preferences payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      const pref = { preferred_categories: ['clothing' as const, 'kitchen' as const] };
      await updatePreferences(pref, 'tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/me/preferences',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(pref),
        })
      );
    });

    it('updateProfile should make PATCH request with user payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 1 }),
      } as Response);

      const updatePayload = { full_name: 'Jane Doe', role: 'recipient' as const };
      await updateProfile(updatePayload, 'tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/me',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(updatePayload),
        })
      );
    });
  });

  describe('Items Methods', () => {
    it('createItem should make POST request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({}),
      } as Response);

      const payload = {
        title: 'Title',
        description: 'Desc',
        category: 'clothing' as const,
        condition: 'new' as const,
        quantity: 1,
        city: 'Delhi',
        pincode: '110001',
      };

      await createItem(payload, 'tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/items/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(payload),
        })
      );
    });

    it('getItems should format query string and map radius to radius_km', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      } as Response);

      await getItems({
        page: 2,
        page_size: 10,
        radius: 25,
        category: 'furniture',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/items/?page=2&page_size=10&category=furniture&radius_km=25'),
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('getItems should append mine parameter only when it is a boolean (true or false)', async () => {
      // 1. mine is true
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      } as Response);

      await getItems({ mine: true });

      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.stringContaining('/api/items/?mine=true'),
        expect.any(Object)
      );

      // 2. mine is false
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      } as Response);

      await getItems({ mine: false });

      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.stringContaining('/api/items/?mine=false'),
        expect.any(Object)
      );

      // 3. mine is undefined (should be omitted)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      } as Response);

      await getItems({ page: 1 });

      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.not.stringContaining('mine='),
        expect.any(Object)
      );
    });

    it('getItem should make GET request with ID', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await getItem(42);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/items/42',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('updateItem should make PATCH request with ID and body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      const payload = { title: 'New title' };
      await updateItem(42, payload, 'tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/items/42',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      );
    });

    it('deleteItem should make DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await deleteItem(42, 'tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/items/42',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('Requests Methods', () => {
    it('createRequest should make POST request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({}),
      } as Response);

      const payload = { item_id: 12, message: 'Interested' };
      await createRequest(payload, 'tok');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/requests/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(payload),
        })
      );
    });

    it('getIncomingRequests and getOutgoingRequests should call correct endpoints', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [],
      } as Response);

      await getIncomingRequests('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/requests/incoming',
        expect.objectContaining({ method: 'GET' })
      );

      await getOutgoingRequests('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/requests/my',
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('approveRequest, rejectRequest, confirmPickup, cancelRequest should call correct endpoints', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await approveRequest(1, 'tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/requests/1/approve',
        expect.objectContaining({ method: 'PATCH' })
      );

      await rejectRequest(1, 'tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/requests/1/reject',
        expect.objectContaining({ method: 'PATCH' })
      );

      await confirmPickup(1, 'tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/requests/1/pickup',
        expect.objectContaining({ method: 'PATCH' })
      );

      await cancelRequest(1, 'tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/requests/1/cancel',
        expect.objectContaining({ method: 'PATCH' })
      );
    });
  });

  describe('Analytics Methods', () => {
    it('should call all analytics endpoints correctly', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response);

      await getAnalyticsSummary('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/analytics/summary',
        expect.objectContaining({ method: 'GET' })
      );

      await getCategoryBreakdown('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/analytics/category-breakdown',
        expect.objectContaining({ method: 'GET' })
      );

      await getDonationTrends('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/analytics/donation-trend',
        expect.objectContaining({ method: 'GET' })
      );

      await getTopCities('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/analytics/top-cities',
        expect.objectContaining({ method: 'GET' })
      );

      await getPlatformActivity('tok');
      expect(mockFetch).toHaveBeenLastCalledWith(
        'http://localhost:8000/api/analytics/platform-activity',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('Matching Methods', () => {
    it('getSuggestions should work with string token', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [],
      } as Response);

      await getSuggestions('mytoken');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/matching/suggestions',
        expect.objectContaining({
          method: 'GET',
        })
      );
      const headers = mockFetch.mock.calls[0][1].headers as Headers;
      expect(headers.get('Authorization')).toBe('Bearer mytoken');
    });

    it('getSuggestions should work with parameters and token', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [],
      } as Response);

      await getSuggestions({ lat: 12.34, lng: 56.78 }, 'mytoken');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/matching/suggestions?lat=12.34&lng=56.78'),
        expect.objectContaining({
          method: 'GET',
        })
      );
      const headers = mockFetch.mock.calls[0][1].headers as Headers;
      expect(headers.get('Authorization')).toBe('Bearer mytoken');
    });
  });
});

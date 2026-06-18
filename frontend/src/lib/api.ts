import {
  UserCreate,
  UserOut,
  UserUpdate,
  Token,
  PreferencesUpdate,
  ItemCreate,
  ItemOut,
  ItemCategory,
  ItemCondition,
  ItemStatus,
  PaginatedResponse,
  ItemUpdate,
  RequestCreate,
  RequestOut,
  AnalyticsSummary,
  CategoryBreakdownItem,
  DonationTrendItem,
  TopCityItem,
  PlatformActivityItem,
  SuggestionItem,
  GetItemsParams,
} from '@/types';

const isServer = typeof window === 'undefined' || process.env.NODE_ENV === 'test';
const BASE_URL = isServer
  ? (process.env.API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://api:8000')
  : '';

export class ApiError extends Error {
  status: number;
  detail: any;
  constructor(message: string, status: number, detail?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Helper to dynamically extract access_token from the client Supabase cookie
 */
export function getClientToken(): string | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }
  const match = document.cookie.match(/sb-[a-zA-Z0-9]+-auth-token=([^;]+)/);
  if (!match) return undefined;
  try {
    const decoded = decodeURIComponent(match[1]);
    const parsed = JSON.parse(decoded);
    return parsed.access_token || parsed.session?.access_token || parsed.currentSession?.access_token;
  } catch (e) {
    return undefined;
  }
}

/**
 * Generic API request function
 */
export async function apiRequest<T>(
  path: string,
  options?: RequestInit & { token?: string }
): Promise<T> {
  const { token, ...fetchOptions } = options || {};

  // Resolve token: explicit token takes precedence, then client-side cookie token.
  let resolvedToken = token;
  if (!resolvedToken && typeof window !== 'undefined') {
    resolvedToken = getClientToken();
  }

  const headers = new Headers(fetchOptions.headers);
  if (resolvedToken) {
    headers.set('Authorization', `Bearer ${resolvedToken}`);
  }

  // Set Content-Type to application/json by default if body is present and not FormData/URLSearchParams
  if (
    fetchOptions.body &&
    !headers.has('Content-Type') &&
    !(fetchOptions.body instanceof URLSearchParams) &&
    !(fetchOptions.body instanceof FormData)
  ) {
    headers.set('Content-Type', 'application/json');
  }

  let resolvedPath = path;
  if (!isServer && path.startsWith('/api/')) {
    resolvedPath = path.replace('/api/', '/api/backend/');
  }

  const url = `${BASE_URL}${resolvedPath.startsWith('/') ? resolvedPath : '/' + resolvedPath}`;

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    let detail: any = null;
    let message = `API request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      detail = errorJson.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
      } else if (errorJson.message) {
        message = errorJson.message;
      }
    } catch {
      if (response.statusText) {
        message = `${response.status} ${response.statusText}`;
      }
    }
    throw new ApiError(message, response.status, detail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  try {
    return await response.json();
  } catch {
    return {} as T;
  }
}

/**
 * Auth API Endpoints
 */
export async function register(user: UserCreate): Promise<UserOut> {
  return apiRequest<UserOut>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(user),
  });
}

export async function login(username: string, password: string): Promise<Token> {
  const body = new URLSearchParams({ username, password });
  return apiRequest<Token>('/api/auth/login', {
    method: 'POST',
    body,
  });
}

export async function getMe(token?: string): Promise<UserOut> {
  return apiRequest<UserOut>('/api/auth/me', {
    method: 'GET',
    token,
  });
}

export async function updateProfile(
  update: UserUpdate,
  token?: string
): Promise<UserOut> {
  return apiRequest<UserOut>('/api/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(update),
    token,
  });
}

export async function updatePreferences(
  pref: PreferencesUpdate,
  token?: string
): Promise<UserOut> {
  return apiRequest<UserOut>('/api/auth/me/preferences', {
    method: 'PATCH',
    body: JSON.stringify(pref),
    token,
  });
}

/**
 * Items API Endpoints
 */
export async function createItem(item: ItemCreate, token?: string): Promise<ItemOut> {
  return apiRequest<ItemOut>('/api/items/', {
    method: 'POST',
    body: JSON.stringify(item),
    token,
  });
}

export async function getItems(
  params?: GetItemsParams,
  token?: string
): Promise<PaginatedResponse<ItemOut>> {
  const queryParams = new URLSearchParams();
  if (params) {
    if (params.page !== undefined) queryParams.append('page', params.page.toString());
    if (params.page_size !== undefined) queryParams.append('page_size', params.page_size.toString());
    if (params.category !== undefined) queryParams.append('category', params.category);
    if (params.condition !== undefined) queryParams.append('condition', params.condition);
    if (params.status !== undefined) queryParams.append('status', params.status);
    if (params.city !== undefined) queryParams.append('city', params.city);
    if (params.pincode !== undefined) queryParams.append('pincode', params.pincode);
    if (params.lat !== undefined) queryParams.append('lat', params.lat.toString());
    if (params.lng !== undefined) queryParams.append('lng', params.lng.toString());
    if (params.radius !== undefined) queryParams.append('radius_km', params.radius.toString());
    if (typeof params.mine === 'boolean') queryParams.append('mine', params.mine.toString());
  }

  const queryString = queryParams.toString();
  const path = `/api/items/${queryString ? `?${queryString}` : ''}`;

  return apiRequest<PaginatedResponse<ItemOut>>(path, {
    method: 'GET',
    token,
  });
}

export async function getItem(id: number, token?: string): Promise<ItemOut> {
  return apiRequest<ItemOut>(`/api/items/${id}`, {
    method: 'GET',
    token,
  });
}

export async function updateItem(
  id: number,
  item: ItemUpdate,
  token?: string
): Promise<ItemOut> {
  return apiRequest<ItemOut>(`/api/items/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(item),
    token,
  });
}

export async function deleteItem(id: number, token?: string): Promise<ItemOut> {
  return apiRequest<ItemOut>(`/api/items/${id}`, {
    method: 'DELETE',
    token,
  });
}

/**
 * Requests API Endpoints
 */
export async function createRequest(
  request: RequestCreate,
  token?: string
): Promise<RequestOut> {
  return apiRequest<RequestOut>('/api/requests/', {
    method: 'POST',
    body: JSON.stringify(request),
    token,
  });
}

export async function getIncomingRequests(token?: string): Promise<RequestOut[]> {
  return apiRequest<RequestOut[]>('/api/requests/incoming', {
    method: 'GET',
    token,
  });
}

export async function getOutgoingRequests(token?: string): Promise<RequestOut[]> {
  return apiRequest<RequestOut[]>('/api/requests/my', {
    method: 'GET',
    token,
  });
}

export async function approveRequest(id: number, token?: string, pickupLocation?: string): Promise<RequestOut> {
  return apiRequest<RequestOut>(`/api/requests/${id}/approve`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ pickup_location: pickupLocation || null }),
  });
}

export async function rejectRequest(id: number, token?: string): Promise<RequestOut> {
  return apiRequest<RequestOut>(`/api/requests/${id}/reject`, {
    method: 'PATCH',
    token,
  });
}

export async function confirmPickup(id: number, token?: string): Promise<RequestOut> {
  return apiRequest<RequestOut>(`/api/requests/${id}/pickup`, {
    method: 'PATCH',
    token,
  });
}

export async function cancelRequest(id: number, token?: string): Promise<RequestOut> {
  return apiRequest<RequestOut>(`/api/requests/${id}/cancel`, {
    method: 'PATCH',
    token,
  });
}

/**
 * Analytics API Endpoints
 */
export async function getAnalyticsSummary(token?: string): Promise<AnalyticsSummary> {
  return apiRequest<AnalyticsSummary>('/api/analytics/summary', {
    method: 'GET',
    token,
  });
}

export async function getCategoryBreakdown(token?: string): Promise<CategoryBreakdownItem[]> {
  return apiRequest<CategoryBreakdownItem[]>('/api/analytics/category-breakdown', {
    method: 'GET',
    token,
  });
}

export async function getDonationTrends(token?: string): Promise<DonationTrendItem[]> {
  return apiRequest<DonationTrendItem[]>('/api/analytics/donation-trend', {
    method: 'GET',
    token,
  });
}

export async function getTopCities(token?: string): Promise<TopCityItem[]> {
  return apiRequest<TopCityItem[]>('/api/analytics/top-cities', {
    method: 'GET',
    token,
  });
}

export async function getPlatformActivity(token?: string): Promise<PlatformActivityItem[]> {
  return apiRequest<PlatformActivityItem[]>('/api/analytics/platform-activity', {
    method: 'GET',
    token,
  });
}

/**
 * Matching API Endpoints
 */
export async function getSuggestions(token?: string): Promise<SuggestionItem[]>;
export async function getSuggestions(
  params?: { lat?: number; lng?: number },
  token?: string
): Promise<SuggestionItem[]>;
export async function getSuggestions(
  paramsOrToken?: { lat?: number; lng?: number } | string,
  token?: string
): Promise<SuggestionItem[]> {
  let params: { lat?: number; lng?: number } | undefined;
  let resolvedToken = token;

  if (typeof paramsOrToken === 'string') {
    resolvedToken = paramsOrToken;
  } else if (paramsOrToken && typeof paramsOrToken === 'object') {
    params = paramsOrToken;
  }

  const queryParams = new URLSearchParams();
  if (params) {
    if (params.lat !== undefined) queryParams.append('lat', params.lat.toString());
    if (params.lng !== undefined) queryParams.append('lng', params.lng.toString());
  }

  const queryString = queryParams.toString();
  const path = `/api/matching/suggestions${queryString ? `?${queryString}` : ''}`;

  return apiRequest<SuggestionItem[]>(path, {
    method: 'GET',
    token: resolvedToken,
  });
}

/**
 * Upload an image file for a listing
 */
export async function uploadItemImage(file: File, token?: string): Promise<{ image_url: string }> {
  const formData = new FormData();
  formData.append('file', file);

  return apiRequest<{ image_url: string }>('/api/items/upload', {
    method: 'POST',
    body: formData,
    token,
  });
}

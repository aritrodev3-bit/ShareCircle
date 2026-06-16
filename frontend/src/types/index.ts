// User Roles
export type UserRole = 'donor' | 'recipient' | 'ngo' | 'admin';

// Item Categories
export type ItemCategory =
  | 'clothing'
  | 'furniture'
  | 'electronics'
  | 'books'
  | 'kitchen'
  | 'toys'
  | 'medical'
  | 'other';

// Item Conditions
export type ItemCondition = 'new' | 'like_new' | 'good' | 'fair';

// Item Statuses
export type ItemStatus = 'available' | 'reserved' | 'donated' | 'removed';

// Request Statuses
export type RequestStatus = 'pending' | 'approved' | 'rejected' | 'picked_up' | 'cancelled';

/**
 * Outgoing Models (Representing Server Responses)
 */

export interface UserUpdate {
  full_name?: string | null;
  role?: UserRole | null;
  phone?: string | null;
}

export interface UserOut {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  phone: string | null;
  preferred_categories: string[];
  is_active: boolean;
}

export interface ItemOut {
  id: number;
  donor_id: number;
  donor_name: string;
  title: string;
  description: string;
  category: ItemCategory;
  condition: ItemCondition;
  quantity: number;
  status: ItemStatus;
  city: string;
  pincode: string;
  image_url: string | null;
  donated_at: string | null;
  removed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RequestOut {
  id: number;
  item_id: number;
  requester_id: number;
  item_title: string;
  donor_name: string;
  donor_phone: string | null;
  requester_name: string;
  message: string | null;
  ngo_note: string | null;
  status: RequestStatus;
  pickup_scheduled_at: string | null;
  approved_at: string | null;
  picked_up_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Incoming Models (Representing Request Payloads)
 */

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  phone?: string | null;
}

export interface ItemCreate {
  title: string;
  description: string;
  category: ItemCategory;
  condition: ItemCondition;
  quantity: number;
  city: string;
  pincode: string;
  image_url?: string | null;
  lat?: number | null;
  lng?: number | null;
}

export interface ItemUpdate {
  title?: string | null;
  description?: string | null;
  category?: ItemCategory | null;
  condition?: ItemCondition | null;
  quantity?: number | null;
  city?: string | null;
  pincode?: string | null;
  image_url?: string | null;
  lat?: number | null;
  lng?: number | null;
}

export interface RequestCreate {
  item_id: number;
  message?: string | null;
  ngo_note?: string | null;
}

export interface PreferencesUpdate {
  preferred_categories: ItemCategory[];
}

/**
 * Analytics Models
 */

export interface AnalyticsSummary {
  total_donors: number;
  total_recipients: number;
  total_ngos: number;
  total_items_listed: number;
  total_items_donated: number;
  total_requests: number;
  people_helped: number;
}

export interface CategoryBreakdownItem {
  category: string;
  count: number;
}

export interface DonationTrendItem {
  date: string; // ISO date string: YYYY-MM-DD
  count: number;
}

export interface TopCityItem {
  city: string;
  count: number;
}

export interface PlatformActivityItem {
  date: string; // ISO date string: YYYY-MM-DD
  new_users: number;
  new_items: number;
  new_requests: number;
}

/**
 * Matching & Auth Models
 */

export interface SuggestionItem {
  id: number;
  title: string;
  category: ItemCategory;
  condition: ItemCondition;
  city: string;
  donor_name: string;
  image_url: string | null;
  score: number;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface GetItemsParams {
  page?: number;
  page_size?: number;
  category?: ItemCategory;
  condition?: ItemCondition;
  status?: ItemStatus;
  city?: string;
  pincode?: string;
  lat?: number;
  lng?: number;
  radius?: number;
  mine?: boolean;
}


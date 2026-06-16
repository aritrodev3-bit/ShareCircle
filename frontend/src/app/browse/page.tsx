'use client';

import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/utils/supabase/client';
import { getItems, createRequest, getMe } from '@/lib/api';
import { ItemOut, UserOut, ItemCategory, ItemCondition } from '@/types';
import ItemCard from '@/components/ItemCard';
import { Search, MapPin, Loader2, AlertCircle, X, ChevronLeft, ChevronRight, Navigation, CheckCircle2 } from 'lucide-react';

export default function BrowsePage() {
  // Authentication & User profile
  const [dbUser, setDbUser] = useState<UserOut | null>(null);

  // Listing Data
  const [items, setItems] = useState<ItemOut[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters State
  const [category, setCategory] = useState<string>('');
  const [condition, setCondition] = useState<string>('');
  const [city, setCity] = useState<string>('');

  // Location/Radius Search State
  const [useRadius, setUseRadius] = useState(false);
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [radius, setRadius] = useState('10');
  const [fetchingGps, setFetchingGps] = useState(false);

  // Request Modal State
  const [selectedItem, setSelectedItem] = useState<ItemOut | null>(null);
  const [requestMessage, setRequestMessage] = useState('');
  const [ngoNote, setNgoNote] = useState('');
  const [submittingRequest, setSubmittingRequest] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [requestSuccess, setRequestSuccess] = useState(false);

  // Load user profile on mount
  useEffect(() => {
    const loadUser = async () => {
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (session?.access_token) {
          const profile = await getMe(session.access_token);
          setDbUser(profile);
        }
      } catch (err) {
        console.error('Failed to load user profile in browse page:', err);
      }
    };
    loadUser();
  }, []);

  // Fetch Items callback
  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;

      // Build parameters
      const params: any = {
        page,
        page_size: 9,
        status: 'available', // Only browse available items
      };

      if (category) params.category = category as ItemCategory;
      if (condition) params.condition = condition as ItemCondition;
      if (city) params.city = city.trim();

      if (useRadius && lat && lng && radius) {
        const parsedLat = parseFloat(lat);
        const parsedLng = parseFloat(lng);
        const parsedRadius = parseFloat(radius);

        if (!isNaN(parsedLat) && !isNaN(parsedLng) && !isNaN(parsedRadius)) {
          params.lat = parsedLat;
          params.lng = parsedLng;
          params.radius = parsedRadius;
        }
      }

      const data = await getItems(params, token);
      setItems(data.items);
      setTotalPages(data.total_pages);
    } catch (err: any) {
      console.error('Failed to load items:', err);
      setError(err.message || 'Failed to load items from server.');
    } finally {
      setLoading(false);
    }
  }, [page, category, condition, city, useRadius, lat, lng, radius]);

  // Refetch items when filters or pages change
  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  // Trigger browser location detection
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setFetchingGps(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(position.coords.latitude.toFixed(6));
        setLng(position.coords.longitude.toFixed(6));
        setFetchingGps(false);
      },
      (err) => {
        console.error(err);
        alert('Could not retrieve your location. Please input coordinates manually.');
        setFetchingGps(false);
      }
    );
  };

  // Submit Request Action
  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    setSubmittingRequest(true);
    setRequestError(null);
    setRequestSuccess(false);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('You must be logged in to request items.');

      await createRequest(
        {
          item_id: selectedItem.id,
          message: requestMessage.trim() ? requestMessage.trim() : null,
          ngo_note: dbUser?.role === 'ngo' && ngoNote.trim() ? ngoNote.trim() : null,
        },
        token
      );

      setRequestSuccess(true);
      // Refresh items list
      fetchItems();

      // Close modal after success
      setTimeout(() => {
        setSelectedItem(null);
        setRequestMessage('');
        setNgoNote('');
        setRequestSuccess(false);
      }, 1500);
    } catch (err: any) {
      console.error('Request submission failed:', err);
      setRequestError(err.message || 'Failed to submit request.');
    } finally {
      setSubmittingRequest(false);
    }
  };

  // Categories list
  const categories: ItemCategory[] = [
    'clothing',
    'furniture',
    'electronics',
    'books',
    'kitchen',
    'toys',
    'medical',
    'other',
  ];

  // Conditions list
  const conditions: ItemCondition[] = ['new', 'like_new', 'good', 'fair'];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h1 className="font-serif text-2xl font-medium text-text-primary">Available donations</h1>
        <p className="text-sm text-text-secondary">
          Browse items offered by donors in your community.
        </p>
      </div>

      {/* Filter Section */}
      <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Category Filter */}
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
              Category
            </label>
            <select
              className="focus-ring cursor-pointer"
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Condition Filter */}
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
              Condition
            </label>
            <select
              className="focus-ring cursor-pointer"
              value={condition}
              onChange={(e) => {
                setCondition(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Conditions</option>
              {conditions.map((cond) => (
                <option key={cond} value={cond}>
                  {cond.replace('_', ' ').charAt(0).toUpperCase() + cond.replace('_', ' ').slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* City Filter */}
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
              City
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g. San Francisco"
                className="focus-ring"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
        </div>

        {/* Spatial / Location Search */}
        <div className="mt-4 pt-4 border-t border-[rgba(167,209,41,0.04)]">
          <label className="inline-flex items-center space-x-2 text-sm text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              className="rounded bg-bg-secondary border-[rgba(167,209,41,0.16)] text-lime-500 focus:ring-0 cursor-pointer"
              checked={useRadius}
              onChange={(e) => {
                setUseRadius(e.target.checked);
                setPage(1);
              }}
            />
            <span className="font-sans font-medium text-xs uppercase tracking-wider">Enable radius search (GPS)</span>
          </label>

          {useRadius && (
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mt-3 animate-fadeIn">
              <div className="sm:col-span-1">
                <label className="block text-[10px] font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                  Latitude
                </label>
                <input
                  type="number"
                  step="0.000001"
                  placeholder="37.7749"
                  className="focus-ring"
                  value={lat}
                  onChange={(e) => {
                    setLat(e.target.value);
                    setPage(1);
                  }}
                />
              </div>
              <div className="sm:col-span-1">
                <label className="block text-[10px] font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                  Longitude
                </label>
                <input
                  type="number"
                  step="0.000001"
                  placeholder="-122.4194"
                  className="focus-ring"
                  value={lng}
                  onChange={(e) => {
                    setLng(e.target.value);
                    setPage(1);
                  }}
                />
              </div>
              <div className="sm:col-span-1">
                <label className="block text-[10px] font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                  Radius (km)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  className="focus-ring"
                  value={radius}
                  onChange={(e) => {
                    setRadius(e.target.value);
                    setPage(1);
                  }}
                />
              </div>
              <div className="flex items-end sm:col-span-1">
                <button
                  type="button"
                  onClick={handleGetLocation}
                  disabled={fetchingGps}
                  className="w-full flex items-center justify-center space-x-1.5 bg-transparent border border-olive-500 hover:bg-surface-hover text-lime-400 py-2.5 px-3 rounded-lg text-xs transition-all duration-150 focus-ring cursor-pointer min-h-[44px]"
                >
                  {fetchingGps ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Navigation className="h-4 w-4" />
                      <span>Use current GPS</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {error && (
        <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-2">
          <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
          <p className="text-xs text-text-muted">Loading available donations...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-12 text-center">
          <MapPin className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h2 className="font-serif text-lg font-medium text-text-primary mb-2">No donations found</h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto">
            Try adjusting your filters or expansion coordinates to see items in other regions.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                showRequestButton={
                  dbUser !== null && (dbUser.role === 'recipient' || dbUser.role === 'ngo')
                }
                onRequestClick={(id) => setSelectedItem(item)}
              />
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center space-x-4 pt-6">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page === 1}
                className="flex items-center space-x-1.5 px-3 py-2 bg-transparent text-text-secondary border border-olive-600 hover:bg-surface-hover rounded-lg text-sm transition-all duration-150 focus-ring cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed min-h-[40px]"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Prev</span>
              </button>
              <span className="text-xs text-text-muted font-sans font-medium uppercase">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={page === totalPages}
                className="flex items-center space-x-1.5 px-3 py-2 bg-transparent text-text-secondary border border-olive-600 hover:bg-surface-hover rounded-lg text-sm transition-all duration-150 focus-ring cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed min-h-[40px]"
              >
                <span>Next</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      )}

      {/* Item Request Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-surface-1 border border-[rgba(167,209,41,0.16)] rounded-[14px] w-full max-w-md p-6 relative animate-slideIn">
            <button
              onClick={() => setSelectedItem(null)}
              className="absolute top-4 right-4 text-text-muted hover:text-text-primary focus-ring rounded-lg p-1 min-h-[36px] min-w-[36px]"
            >
              <X className="h-5 w-5" />
            </button>

            {requestSuccess ? (
              <div className="py-6 text-center space-y-3">
                <CheckCircle2 className="h-12 w-12 text-success mx-auto" />
                <h3 className="font-serif text-lg text-text-primary">Request submitted!</h3>
                <p className="text-sm text-text-secondary">
                  Your request has been successfully registered. The donor has been notified.
                </p>
              </div>
            ) : (
              <form onSubmit={handleRequestSubmit} className="space-y-4">
                <div>
                  <h3 className="font-serif text-lg text-text-primary mb-1">
                    Request &ldquo;{selectedItem.title}&rdquo;
                  </h3>
                  <p className="text-xs text-text-secondary">
                    Provided by {selectedItem.donor_name} in {selectedItem.city}
                  </p>
                </div>

                {requestError && (
                  <div className="bg-error/5 border border-error/20 text-error rounded-lg p-3 flex items-start space-x-2 text-sm">
                    <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
                    <span>{requestError}</span>
                  </div>
                )}

                {/* Message Field */}
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                    Message to donor
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Briefly describe why you are requesting this item..."
                    className="focus-ring text-xs"
                    value={requestMessage}
                    onChange={(e) => setRequestMessage(e.target.value)}
                    maxLength={1000}
                    disabled={submittingRequest}
                  />
                </div>

                {/* NGO Note Field (NGO only) */}
                {dbUser?.role === 'ngo' && (
                  <div>
                    <label className="block text-xs font-medium text-info mb-1.5 uppercase tracking-wider">
                      NGO verification note
                    </label>
                    <textarea
                      rows={2}
                      placeholder="e.g. Verified ngo shelter, tax-exempt ID..."
                      className="focus-ring text-xs border-info/30"
                      value={ngoNote}
                      onChange={(e) => setNgoNote(e.target.value)}
                      maxLength={1000}
                      disabled={submittingRequest}
                    />
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedItem(null)}
                    disabled={submittingRequest}
                    className="flex-1 bg-transparent text-text-secondary border border-olive-600 hover:bg-surface-hover py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-150 focus-ring cursor-pointer min-h-[44px]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingRequest}
                    className="flex-1 bg-lime-500 hover:bg-lime-700 text-bg-primary py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-150 flex items-center justify-center space-x-2 focus-ring cursor-pointer min-h-[44px]"
                  >
                    {submittingRequest ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Sending...</span>
                      </>
                    ) : (
                      <span>Submit request</span>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

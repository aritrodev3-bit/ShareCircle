'use client';

import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/utils/supabase/client';
import { getSuggestions, getOutgoingRequests, cancelRequest, updatePreferences, getMe } from '@/lib/api';
import { ItemOut, RequestOut, UserOut, ItemCategory, SuggestionItem } from '@/types';
import ItemCard from '@/components/ItemCard';
import RequestCard from '@/components/RequestCard';
import { Sparkles, ClipboardList, Settings, Loader2, AlertCircle, CheckCircle2, Navigation } from 'lucide-react';

export default function NgoDashboard() {
  const [dbUser, setDbUser] = useState<UserOut | null>(null);
  const [activeTab, setActiveTab] = useState<'suggestions' | 'requests' | 'preferences'>('suggestions');

  // Suggestions state
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);

  // Suggestions Coordinates
  const [useGps, setUseGps] = useState(false);
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [fetchingGps, setFetchingGps] = useState(false);

  // Requests state
  const [requests, setRequests] = useState<RequestOut[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(true);
  const [requestsError, setRequestsError] = useState<string | null>(null);

  // Preferences state
  const [selectedCategories, setSelectedCategories] = useState<ItemCategory[]>([]);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [preferenceError, setPreferenceError] = useState<string | null>(null);
  const [preferenceSuccess, setPreferenceSuccess] = useState(false);

  // General Action Alerts
  const [actionAlert, setActionAlert] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

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

  // Fetch Suggestions
  const fetchSuggestions = useCallback(async () => {
    setLoadingSuggestions(true);
    setSuggestionsError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      let data;
      if (useGps && lat && lng) {
        const parsedLat = parseFloat(lat);
        const parsedLng = parseFloat(lng);
        if (!isNaN(parsedLat) && !isNaN(parsedLng)) {
          data = await getSuggestions({ lat: parsedLat, lng: parsedLng }, token);
        } else {
          data = await getSuggestions(token);
        }
      } else {
        data = await getSuggestions(token);
      }

      setSuggestions(data);
    } catch (err: any) {
      console.error(err);
      setSuggestionsError(err.message || 'Failed to load suggestions.');
    } finally {
      setLoadingSuggestions(false);
    }
  }, [useGps, lat, lng]);

  // Fetch NGO Requests
  const fetchRequests = useCallback(async () => {
    setLoadingRequests(true);
    setRequestsError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      const data = await getOutgoingRequests(token);
      setRequests(data);
    } catch (err: any) {
      console.error(err);
      setRequestsError(err.message || 'Failed to load NGO requests.');
    } finally {
      setLoadingRequests(false);
    }
  }, []);

  // Fetch initial profile & data
  useEffect(() => {
    const init = async () => {
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (session?.access_token) {
          const profile = await getMe(session.access_token);
          setDbUser(profile);
          setSelectedCategories(profile.preferred_categories as ItemCategory[]);
        }
      } catch (err) {
        console.error(err);
      }
    };
    init();
    fetchSuggestions();
    fetchRequests();
  }, [fetchSuggestions, fetchRequests]);

  // Handle GPS coordinate retrieval
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
        alert('Could not retrieve your location.');
        setFetchingGps(false);
      }
    );
  };

  // Cancel Request Action
  const handleCancelRequest = async (reqId: number) => {
    if (!confirm('Are you sure you want to cancel this request?')) return;
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      await cancelRequest(reqId, token);
      setActionAlert({ message: 'Request cancelled.', type: 'success' });
      fetchRequests();
    } catch (err: any) {
      console.error(err);
      setActionAlert({ message: err.message || 'Failed to cancel request.', type: 'error' });
    }
  };

  // Preference checkbox toggles
  const handleCategoryToggle = (cat: ItemCategory) => {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  // Update Preferences Action
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPreferences(true);
    setPreferenceError(null);
    setPreferenceSuccess(false);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Not authenticated.');

      await updatePreferences({ preferred_categories: selectedCategories }, token);
      setPreferenceSuccess(true);
      // Refresh suggestions matching the new preferences
      fetchSuggestions();
      setTimeout(() => setPreferenceSuccess(false), 2500);
    } catch (err: any) {
      console.error(err);
      setPreferenceError(err.message || 'Failed to save preferences.');
    } finally {
      setSavingPreferences(false);
    }
  };

  // Hide general alerts
  useEffect(() => {
    if (actionAlert) {
      const timer = setTimeout(() => setActionAlert(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [actionAlert]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-serif text-2xl font-medium text-text-primary">NGO dashboard</h1>
        <p className="text-sm text-text-secondary">
          View automated matches, manage requests, and update preferred category filters.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[rgba(167,209,41,0.08)]">
        <button
          onClick={() => setActiveTab('suggestions')}
          className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-150 cursor-pointer ${
            activeTab === 'suggestions'
              ? 'text-lime-400 border-lime-500'
              : 'text-text-secondary border-transparent hover:text-text-primary hover:bg-surface-hover'
          }`}
        >
          <Sparkles className="h-4 w-4" />
          <span>Matches ({suggestions.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-150 cursor-pointer ${
            activeTab === 'requests'
              ? 'text-lime-400 border-lime-500'
              : 'text-text-secondary border-transparent hover:text-text-primary hover:bg-surface-hover'
          }`}
        >
          <ClipboardList className="h-4 w-4" />
          <span>My Requests ({requests.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('preferences')}
          className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-150 cursor-pointer ${
            activeTab === 'preferences'
              ? 'text-lime-400 border-lime-500'
              : 'text-text-secondary border-transparent hover:text-text-primary hover:bg-surface-hover'
          }`}
        >
          <Settings className="h-4 w-4" />
          <span>Matching Settings</span>
        </button>
      </div>

      {/* Action Alerts */}
      {actionAlert && (
        <div
          className={`p-3 rounded-lg flex items-start space-x-2 text-sm animate-fadeIn ${
            actionAlert.type === 'success'
              ? 'bg-success/5 border border-success/20 text-success'
              : 'bg-error/5 border border-error/20 text-error'
          }`}
        >
          {actionAlert.type === 'error' && <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />}
          <span>{actionAlert.message}</span>
        </div>
      )}

      {/* Matches Tab */}
      {activeTab === 'suggestions' && (
        <div className="space-y-6 animate-fadeIn">
          {/* Spatial query controls for suggestions */}
          <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4">
            <label className="inline-flex items-center space-x-2 text-sm text-text-secondary cursor-pointer">
              <input
                type="checkbox"
                className="rounded bg-bg-secondary border-[rgba(167,209,41,0.16)] text-lime-500 focus:ring-0 cursor-pointer"
                checked={useGps}
                onChange={(e) => {
                  setUseGps(e.target.checked);
                }}
              />
              <span className="font-sans font-medium text-xs uppercase tracking-wider">Search matches relative to location</span>
            </label>

            {useGps && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-3">
                <div>
                  <label className="block text-[10px] font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                    Latitude
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    placeholder="37.7749"
                    className="focus-ring text-xs"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                    Longitude
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    placeholder="-122.4194"
                    className="focus-ring text-xs"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                  />
                </div>
                <div className="flex items-end">
                  <button
                    type="button"
                    onClick={handleGetLocation}
                    disabled={fetchingGps}
                    className="w-full flex items-center justify-center space-x-1.5 bg-transparent border border-olive-500 hover:bg-surface-hover text-lime-400 py-2 px-3 rounded-lg text-xs transition-all duration-150 focus-ring cursor-pointer min-h-[40px]"
                  >
                    {fetchingGps ? (
                      <Loader2 className="h-4.5 w-4.5 animate-spin" />
                    ) : (
                      <>
                        <Navigation className="h-3.5 w-3.5" />
                        <span>Get GPS Coordinates</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
            {useGps && (
              <button
                onClick={fetchSuggestions}
                className="mt-3 bg-lime-500 hover:bg-lime-700 text-bg-primary py-2 px-4 rounded-lg text-xs font-medium transition-all duration-150 focus-ring border-none cursor-pointer"
              >
                Apply Location
              </button>
            )}
          </div>

          {suggestionsError && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{suggestionsError}</span>
            </div>
          )}

          {loadingSuggestions ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-2">
              <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
              <p className="text-xs text-text-muted">Calculating matched donations...</p>
            </div>
          ) : suggestions.length === 0 ? (
            <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-12 text-center">
              <Sparkles className="h-12 w-12 text-text-muted mx-auto mb-4" />
              <h2 className="font-serif text-lg font-medium text-text-primary mb-2">No matches yet</h2>
              <p className="text-sm text-text-secondary max-w-md mx-auto">
                No active listings match your preferred categories. Update your matching settings or check back later.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {suggestions.map((item) => (
                <div key={item.id} className="relative">
                  {/* Score badge top-right */}
                  <span className="absolute top-2 right-2 bg-info/15 text-info border border-info/20 text-[10px] font-medium px-2 py-0.5 rounded-full z-10">
                    Match score: {Math.round(item.score * 100)}%
                  </span>
                  <ItemCard
                    item={{
                      ...item,
                      description: '',
                      donor_id: 0,
                      quantity: 1,
                      status: 'available',
                      pincode: '',
                      donated_at: null,
                      removed_at: null,
                      updated_at: '',
                    }}
                    showRequestButton={true}
                    onRequestClick={() => alert('To request, go to the general Browse tab and select this item.')}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Requests Tab */}
      {activeTab === 'requests' && (
        <div className="animate-fadeIn">
          {requestsError && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{requestsError}</span>
            </div>
          )}

          {loadingRequests ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-2">
              <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
              <p className="text-xs text-text-muted">Loading your requests...</p>
            </div>
          ) : requests.length === 0 ? (
            <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-12 text-center">
              <ClipboardList className="h-12 w-12 text-text-muted mx-auto mb-4" />
              <h2 className="font-serif text-lg font-medium text-text-primary mb-2">No requests made</h2>
              <p className="text-sm text-text-secondary max-w-md mx-auto">
                You haven&rsquo;t submitted requests for any items yet. Browse listings to request.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {requests.map((req) => (
                <RequestCard
                  key={req.id}
                  request={req}
                  currentRole="ngo"
                  onCancel={handleCancelRequest}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Preferences Tab */}
      {activeTab === 'preferences' && (
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-6 max-w-xl animate-fadeIn">
          <h2 className="font-serif text-lg font-medium text-text-primary mb-2">Matching Preferences</h2>
          <p className="text-sm text-text-secondary mb-6">
            Choose categories your NGO focuses on. The matching algorithm scores available items higher if they fall under your preferred categories.
          </p>

          {preferenceError && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-3 flex items-start space-x-2 text-sm mb-4">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{preferenceError}</span>
            </div>
          )}

          {preferenceSuccess && (
            <div className="bg-success/5 border border-success/20 text-success rounded-lg p-3 flex items-start space-x-2 text-sm mb-4">
              <CheckCircle2 className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>Matching preferences successfully updated!</span>
            </div>
          )}

          <form onSubmit={handleSavePreferences} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              {categories.map((cat) => (
                <label
                  key={cat}
                  className={`flex items-center space-x-3 p-3 rounded-lg border transition-all duration-150 cursor-pointer ${
                    selectedCategories.includes(cat)
                      ? 'bg-[rgba(167,209,41,0.04)] border-[rgba(167,209,41,0.24)] text-lime-400 font-medium'
                      : 'bg-bg-secondary border-[rgba(167,209,41,0.08)] text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                  }`}
                >
                  <input
                    type="checkbox"
                    className="rounded bg-bg-secondary border-[rgba(167,209,41,0.16)] text-lime-500 focus:ring-0 cursor-pointer"
                    checked={selectedCategories.includes(cat)}
                    onChange={() => handleCategoryToggle(cat)}
                    disabled={savingPreferences}
                  />
                  <span className="capitalize text-sm select-none">
                    {cat.replace('_', ' ')}
                  </span>
                </label>
              ))}
            </div>

            <button
              type="submit"
              disabled={savingPreferences}
              className="w-full bg-lime-500 hover:bg-lime-700 text-bg-primary py-2.5 px-4 rounded-lg font-medium transition-all duration-150 flex items-center justify-center space-x-2 focus-ring cursor-pointer border-none min-h-[44px]"
            >
              {savingPreferences ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Saving preferences...</span>
                </>
              ) : (
                <span>Save preferences</span>
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

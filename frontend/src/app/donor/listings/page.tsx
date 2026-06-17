'use client';

import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/utils/supabase/client';
import { getItems, createItem, deleteItem, getIncomingRequests, approveRequest, rejectRequest, confirmPickup, getMe } from '@/lib/api';
import { ItemOut, RequestOut, UserOut, ItemCategory, ItemCondition } from '@/types';
import ItemCard from '@/components/ItemCard';
import RequestCard from '@/components/RequestCard';
import { Plus, X, Loader2, AlertCircle, LayoutGrid, ClipboardList, Navigation, CheckCircle2 } from 'lucide-react';

export default function DonorDashboard() {
  const [dbUser, setDbUser] = useState<UserOut | null>(null);
  const [activeTab, setActiveTab] = useState<'listings' | 'requests'>('listings');

  // Listings state
  const [listings, setListings] = useState<ItemOut[]>([]);
  const [loadingListings, setLoadingListings] = useState(true);
  const [listingsError, setListingsError] = useState<string | null>(null);

  // Incoming requests state
  const [requests, setRequests] = useState<RequestOut[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(true);
  const [requestsError, setRequestsError] = useState<string | null>(null);

  // Add Item Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<ItemCategory>('clothing');
  const [condition, setCondition] = useState<ItemCondition>('good');
  const [quantity, setQuantity] = useState(1);
  const [city, setCity] = useState('');
  const [pincode, setPincode] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [fetchingGps, setFetchingGps] = useState(false);
  const [submittingItem, setSubmittingItem] = useState(false);
  const [addItemError, setAddItemError] = useState<string | null>(null);
  const [addItemSuccess, setAddItemSuccess] = useState(false);
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // Alert message for request actions
  const [actionAlert, setActionAlert] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Categories & Conditions lists
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
  const conditions: ItemCondition[] = ['new', 'like_new', 'good', 'fair'];

  // Fetch Listings
  const fetchListings = useCallback(async () => {
    setLoadingListings(true);
    setListingsError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      const data = await getItems({ mine: true, page_size: 100 }, token);
      // Filter out 'removed' items to display active/past listings cleanly
      setListings(data.items.filter((item) => item.status !== 'removed'));
    } catch (err: any) {
      console.error(err);
      setListingsError(err.message || 'Failed to load listings.');
    } finally {
      setLoadingListings(false);
    }
  }, []);

  // Fetch Incoming Requests
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

      const data = await getIncomingRequests(token);
      setRequests(data);
    } catch (err: any) {
      console.error(err);
      setRequestsError(err.message || 'Failed to load incoming requests.');
    } finally {
      setLoadingRequests(false);
    }
  }, []);

  // Initial Load
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
        }
      } catch (err) {
        console.error(err);
      }
    };
    init();
    fetchListings();
    fetchRequests();
  }, [fetchListings, fetchRequests]);

  // GPS geolocation fetch
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

  // Add Item Action
  const handleAddItemSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingItem(true);
    setAddItemError(null);
    setAddItemSuccess(false);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Not authenticated.');

      const latVal = lat ? parseFloat(lat) : null;
      const lngVal = lng ? parseFloat(lng) : null;

      await createItem(
        {
          title: title.trim(),
          description: description.trim(),
          category,
          condition,
          quantity,
          city: city.trim(),
          pincode: pincode.trim(),
          image_url: imageUrl.trim() ? (imageUrl.trim() as any) : null,
          lat: latVal && !isNaN(latVal) ? latVal : null,
          lng: lngVal && !isNaN(lngVal) ? lngVal : null,
        },
        token
      );

      setAddItemSuccess(true);
      fetchListings();

      setTimeout(() => {
        setIsModalOpen(false);
        // Reset form
        setTitle('');
        setDescription('');
        setCategory('clothing');
        setCondition('good');
        setQuantity(1);
        setCity('');
        setPincode('');
        setImageUrl('');
        setLat('');
        setLng('');
        setAddItemSuccess(false);
      }, 1500);
    } catch (err: any) {
      console.error(err);
      setAddItemError(err.message || 'Failed to list item.');
    } finally {
      setSubmittingItem(false);
    }
  };

  // AI Description Generator Action
  const handleAiDescribe = async () => {
    if (!title.trim()) {
      setAiError('Please enter a title first.');
      return;
    }
    setGeneratingAi(true);
    setAiError(null);
    try {
      const response = await fetch('/api/ai/describe-item', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: title.trim() }),
      });

      if (!response.ok) {
        if (response.status === 429) {
          setAiError('Daily AI limit reached. You can still fill in the details manually.');
        } else {
          setAiError('AI generation failed. Please fill in the details manually.');
        }
        return;
      }

      const data = await response.json();
      setDescription(data.description);
      setCategory(data.category);
      setCondition(data.condition);
    } catch (err) {
      console.error(err);
      setAiError('AI generation failed. Please fill in the details manually.');
    } finally {
      setGeneratingAi(false);
    }
  };

  // Soft Delete Listing Action
  const handleRemoveListing = async (itemId: number) => {
    if (!confirm('Are you sure you want to remove this listing?')) return;
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      await deleteItem(itemId, token);
      setActionAlert({ message: 'Listing successfully removed.', type: 'success' });
      fetchListings();
      fetchRequests();
    } catch (err: any) {
      console.error(err);
      setActionAlert({ message: err.message || 'Failed to remove listing.', type: 'error' });
    }
  };

  // Workflow Actions
  const handleApprove = async (reqId: number) => {
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      await approveRequest(reqId, token);
      setActionAlert({ message: 'Request approved successfully.', type: 'success' });
      fetchListings();
      fetchRequests();
    } catch (err: any) {
      console.error(err);
      setActionAlert({ message: err.message || 'Failed to approve request.', type: 'error' });
    }
  };

  const handleReject = async (reqId: number) => {
    if (!confirm('Are you sure you want to reject this request?')) return;
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      await rejectRequest(reqId, token);
      setActionAlert({ message: 'Request rejected.', type: 'success' });
      fetchListings();
      fetchRequests();
    } catch (err: any) {
      console.error(err);
      setActionAlert({ message: err.message || 'Failed to reject request.', type: 'error' });
    }
  };

  const handleConfirmPickup = async (reqId: number) => {
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) return;

      await confirmPickup(reqId, token);
      setActionAlert({ message: 'Pickup confirmed! Item status set to donated.', type: 'success' });
      fetchListings();
      fetchRequests();
    } catch (err: any) {
      console.error(err);
      setActionAlert({ message: err.message || 'Failed to confirm pickup.', type: 'error' });
    }
  };

  // Auto hide action alert
  useEffect(() => {
    if (actionAlert) {
      const timer = setTimeout(() => setActionAlert(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [actionAlert]);

  // Reset AI states when modal is closed
  useEffect(() => {
    if (!isModalOpen) {
      setGeneratingAi(false);
      setAiError(null);
    }
  }, [isModalOpen]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-medium text-text-primary">Donor dashboard</h1>
          <p className="text-sm text-text-secondary">
            Manage your listed items and coordinate pickup requests.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center space-x-1.5 bg-lime-500 hover:bg-lime-700 text-bg-primary py-2 px-4 rounded-lg text-sm font-medium transition-all duration-150 focus-ring cursor-pointer min-h-[40px] self-start sm:self-center border-none"
        >
          <Plus className="h-4 w-4" />
          <span>Add donation</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[rgba(167,209,41,0.08)]">
        <button
          onClick={() => setActiveTab('listings')}
          className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-150 cursor-pointer ${
            activeTab === 'listings'
              ? 'text-lime-400 border-lime-500'
              : 'text-text-secondary border-transparent hover:text-text-primary hover:bg-surface-hover'
          }`}
        >
          <LayoutGrid className="h-4 w-4" />
          <span>My Listings ({listings.length})</span>
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
          <span>Incoming Requests ({requests.length})</span>
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

      {/* Listings Tab */}
      {activeTab === 'listings' && (
        <>
          {listingsError && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{listingsError}</span>
            </div>
          )}

          {loadingListings ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-2">
              <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
              <p className="text-xs text-text-muted">Loading your listings...</p>
            </div>
          ) : listings.length === 0 ? (
            <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-12 text-center">
              <LayoutGrid className="h-12 w-12 text-text-muted mx-auto mb-4" />
              <h2 className="font-serif text-lg font-medium text-text-primary mb-2">No items listed</h2>
              <p className="text-sm text-text-secondary max-w-md mx-auto mb-6">
                You haven&rsquo;t listed any items for donation yet. Click &ldquo;Add Donation&rdquo; to start.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fadeIn">
              {listings.map((item) => (
                <ItemCard
                  key={item.id}
                  item={item}
                  showEditActions={true}
                  onRemoveClick={handleRemoveListing}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Requests Tab */}
      {activeTab === 'requests' && (
        <>
          {requestsError && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{requestsError}</span>
            </div>
          )}

          {loadingRequests ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-2">
              <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
              <p className="text-xs text-text-muted">Loading incoming requests...</p>
            </div>
          ) : requests.length === 0 ? (
            <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-12 text-center">
              <ClipboardList className="h-12 w-12 text-text-muted mx-auto mb-4" />
              <h2 className="font-serif text-lg font-medium text-text-primary mb-2">No incoming requests</h2>
              <p className="text-sm text-text-secondary max-w-md mx-auto">
                No recipients or NGOs have requested your items yet. You will see them listed here when they do.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fadeIn">
              {requests.map((req) => (
                <RequestCard
                  key={req.id}
                  request={req}
                  currentRole={dbUser ? dbUser.role : 'donor'}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onConfirmPickup={handleConfirmPickup}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Add Item Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-surface-1 border border-[rgba(167,209,41,0.16)] rounded-[14px] w-full max-w-lg p-6 relative max-h-[90vh] overflow-y-auto animate-slideIn">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 text-text-muted hover:text-text-primary focus-ring rounded-lg p-1 min-h-[36px] min-w-[36px]"
            >
              <X className="h-5 w-5" />
            </button>

            {addItemSuccess ? (
              <div className="py-6 text-center space-y-3">
                <CheckCircle2 className="h-12 w-12 text-success mx-auto" />
                <h3 className="font-serif text-lg text-text-primary">Item listed successfully!</h3>
                <p className="text-sm text-text-secondary">
                  Your donation item is now available for browse searches.
                </p>
              </div>
            ) : (
              <form onSubmit={handleAddItemSubmit} className="space-y-4">
                <div>
                  <h3 className="font-serif text-lg text-text-primary">Add item for donation</h3>
                  <p className="text-xs text-text-secondary mt-1">
                    Describe the item accurately to help recipients and NGOs.
                  </p>
                </div>

                {addItemError && (
                  <div className="bg-error/5 border border-error/20 text-error rounded-lg p-3 flex items-start space-x-2 text-sm">
                    <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
                    <span>{addItemError}</span>
                  </div>
                )}

                {/* Title */}
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label htmlFor="itemTitle" className="block text-xs font-medium text-text-secondary uppercase tracking-wider">
                      Item Title
                    </label>
                    {title.trim().length > 0 && (
                      <button
                        type="button"
                        onClick={handleAiDescribe}
                        disabled={generatingAi || submittingItem}
                        className="inline-flex items-center space-x-1 text-xs text-lime-400 hover:opacity-80 bg-transparent border-none p-0 cursor-pointer disabled:opacity-50"
                      >
                        {generatingAi ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin text-lime-400" />
                            <span>Generating...</span>
                          </>
                        ) : (
                          <span>✨ AI Describe</span>
                        )}
                      </button>
                    )}
                  </div>
                  <input
                    id="itemTitle"
                    type="text"
                    required
                    placeholder="e.g. Wooden Dining Table with 4 Chairs"
                    className="focus-ring"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    disabled={submittingItem || generatingAi}
                  />
                  {aiError && (
                    <div className="mt-1.5 bg-error/5 border border-error/20 text-error rounded-lg p-2 flex items-start space-x-2 text-xs">
                      <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <span>{aiError}</span>
                    </div>
                  )}
                </div>

                {/* Description */}
                <div>
                  <label htmlFor="itemDesc" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                    Description
                  </label>
                  <textarea
                    id="itemDesc"
                    required
                    rows={3}
                    placeholder="Provide details about size, condition, and any pickup restrictions..."
                    className="focus-ring text-xs"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    disabled={submittingItem}
                  />
                </div>

                {/* Category & Condition */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="itemCat" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                      Category
                    </label>
                    <select
                      id="itemCat"
                      className="focus-ring cursor-pointer"
                      value={category}
                      onChange={(e) => setCategory(e.target.value as ItemCategory)}
                      disabled={submittingItem}
                    >
                      {categories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat.charAt(0).toUpperCase() + cat.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="itemCond" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                      Condition
                    </label>
                    <select
                      id="itemCond"
                      className="focus-ring cursor-pointer"
                      value={condition}
                      onChange={(e) => setCondition(e.target.value as ItemCondition)}
                      disabled={submittingItem}
                    >
                      {conditions.map((cond) => (
                        <option key={cond} value={cond}>
                          {cond.replace('_', ' ').charAt(0).toUpperCase() + cond.replace('_', ' ').slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Quantity */}
                <div>
                  <label htmlFor="itemQty" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                    Quantity (Display only)
                  </label>
                  <input
                    id="itemQty"
                    type="number"
                    min="1"
                    required
                    className="focus-ring"
                    value={quantity}
                    onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                    disabled={submittingItem}
                  />
                </div>

                {/* City & Pincode */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="itemCity" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                      City
                    </label>
                    <input
                      id="itemCity"
                      type="text"
                      required
                      placeholder="San Francisco"
                      className="focus-ring"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      disabled={submittingItem}
                    />
                  </div>
                  <div>
                    <label htmlFor="itemPin" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                      Pincode
                    </label>
                    <input
                      id="itemPin"
                      type="text"
                      required
                      placeholder="94101"
                      className="focus-ring"
                      value={pincode}
                      onChange={(e) => setPincode(e.target.value)}
                      disabled={submittingItem}
                    />
                  </div>
                </div>

                {/* Image URL */}
                <div>
                  <label htmlFor="itemImage" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                    Image URL (Optional)
                  </label>
                  <input
                    id="itemImage"
                    type="url"
                    placeholder="https://example.com/image.jpg"
                    className="focus-ring"
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    disabled={submittingItem}
                  />
                </div>

                {/* Lat & Lng Geolocation */}
                <div className="bg-bg-secondary p-3.5 rounded-lg border border-[rgba(167,209,41,0.08)]">
                  <span className="block text-xs font-medium text-text-primary mb-2">Coordinates (Optional - used for GPS searches)</span>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <input
                        type="number"
                        step="0.000001"
                        placeholder="Latitude"
                        className="focus-ring text-xs py-2"
                        value={lat}
                        onChange={(e) => setLat(e.target.value)}
                        disabled={submittingItem}
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        step="0.000001"
                        placeholder="Longitude"
                        className="focus-ring text-xs py-2"
                        value={lng}
                        onChange={(e) => setLng(e.target.value)}
                        disabled={submittingItem}
                      />
                    </div>
                    <div>
                      <button
                        type="button"
                        onClick={handleGetLocation}
                        disabled={fetchingGps || submittingItem}
                        className="w-full flex items-center justify-center space-x-1.5 bg-transparent border border-olive-500 hover:bg-surface-hover text-lime-400 py-2.5 px-3 rounded-lg text-xs transition-all duration-150 focus-ring cursor-pointer min-h-[36px]"
                      >
                        {fetchingGps ? (
                          <Loader2 className="h-4.5 w-4.5 animate-spin" />
                        ) : (
                          <>
                            <Navigation className="h-3.5 w-3.5" />
                            <span>Get GPS</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Footer Buttons */}
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    disabled={submittingItem}
                    className="flex-1 bg-transparent text-text-secondary border border-olive-600 hover:bg-surface-hover py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-150 focus-ring cursor-pointer min-h-[44px]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingItem}
                    className="flex-1 bg-lime-500 hover:bg-lime-700 text-bg-primary py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-150 flex items-center justify-center space-x-2 focus-ring cursor-pointer min-h-[44px]"
                  >
                    {submittingItem ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Submitting...</span>
                      </>
                    ) : (
                      <span>List Item</span>
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

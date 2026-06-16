'use client';

import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@/utils/supabase/client';
import { getOutgoingRequests, cancelRequest, getMe } from '@/lib/api';
import { RequestOut, UserOut } from '@/types';
import RequestCard from '@/components/RequestCard';
import { FileText, Loader2, AlertCircle, ShoppingBag } from 'lucide-react';
import Link from 'next/link';

export default function MyRequestsPage() {
  const [dbUser, setDbUser] = useState<UserOut | null>(null);
  const [requests, setRequests] = useState<RequestOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Alert message for request action feedback
  const [actionAlert, setActionAlert] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
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
      setError(err.message || 'Failed to load requests.');
    } finally {
      setLoading(false);
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
    fetchRequests();
  }, [fetchRequests]);

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
      setActionAlert({ message: 'Request cancelled successfully.', type: 'success' });
      fetchRequests();
    } catch (err: any) {
      console.error(err);
      setActionAlert({ message: err.message || 'Failed to cancel request.', type: 'error' });
    }
  };

  // Auto hide action alert
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
        <h1 className="font-serif text-2xl font-medium text-text-primary">My requests</h1>
        <p className="text-sm text-text-secondary">
          Track the status of items you have requested from the community.
        </p>
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

      {error && (
        <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-2">
          <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
          <p className="text-xs text-text-muted">Loading your requests...</p>
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-12 text-center">
          <FileText className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h2 className="font-serif text-lg font-medium text-text-primary mb-2">No requests made</h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto mb-6">
            You haven&rsquo;t requested any donation items yet. Go to Browse to find available listings.
          </p>
          <Link
            href="/browse"
            className="inline-flex items-center space-x-1.5 bg-lime-500 hover:bg-lime-700 text-bg-primary py-2 px-4 rounded-lg text-sm font-medium transition-all duration-150 focus-ring cursor-pointer border-none"
          >
            <ShoppingBag className="h-4 w-4" />
            <span>Browse items</span>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fadeIn">
          {requests.map((req) => (
            <RequestCard
              key={req.id}
              request={req}
              currentRole={dbUser ? dbUser.role : 'recipient'}
              onCancel={handleCancelRequest}
            />
          ))}
        </div>
      )}
    </div>
  );
}

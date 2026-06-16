'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useSession } from '@/hooks/useSession';
import {
  getAnalyticsSummary,
  getCategoryBreakdown,
  getDonationTrends,
  getTopCities,
  getPlatformActivity,
} from '@/lib/api';
import {
  AnalyticsSummary,
  CategoryBreakdownItem,
  DonationTrendItem,
  TopCityItem,
  PlatformActivityItem,
} from '@/types';
import { Loader2, AlertCircle, BarChart3, ShieldAlert } from 'lucide-react';

// Dynamically import charts with SSR disabled
const AnalyticsCharts = dynamic(() => import('@/components/AnalyticsCharts'), {
  ssr: false,
  loading: () => (
    <div className="flex flex-col items-center justify-center py-20 space-y-2">
      <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
      <p className="text-xs text-text-muted">Loading charts...</p>
    </div>
  ),
});

export default function AdminAnalyticsPage() {
  const { profile: dbUser, session, loading: checkingAuth } = useSession();

  // Data states
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdownItem[]>([]);
  const [trends, setTrends] = useState<DonationTrendItem[]>([]);
  const [cities, setCities] = useState<TopCityItem[]>([]);
  const [activity, setActivity] = useState<PlatformActivityItem[]>([]);

  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAnalytics = async () => {
      if (checkingAuth || !session?.access_token || !dbUser) return;
      if (dbUser.role !== 'admin') {
        setLoadingData(false);
        return;
      }

      setLoadingData(true);
      setError(null);
      try {
        const [
          summaryData,
          categoriesData,
          trendsData,
          citiesData,
          activityData,
        ] = await Promise.all([
          getAnalyticsSummary(session.access_token),
          getCategoryBreakdown(session.access_token),
          getDonationTrends(session.access_token),
          getTopCities(session.access_token),
          getPlatformActivity(session.access_token),
        ]);

        setSummary(summaryData);
        setCategories(categoriesData);
        setTrends(trendsData);
        setCities(citiesData);
        setActivity(activityData);
      } catch (err: any) {
        console.error('Failed to load admin analytics:', err);
        setError(err.message || 'Failed to load analytics.');
      } finally {
        setLoadingData(false);
      }
    };

    loadAnalytics();
  }, [checkingAuth, session, dbUser]);

  if (checkingAuth) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-2">
        <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
        <p className="text-xs text-text-muted">Verifying administrator credentials...</p>
      </div>
    );
  }

  if (dbUser && dbUser.role !== 'admin') {
    return (
      <div className="bg-surface-1 border border-error/20 rounded-[14px] p-8 text-center max-w-md mx-auto my-12 space-y-4">
        <ShieldAlert className="h-12 w-12 text-error mx-auto" />
        <h2 className="font-serif text-lg font-medium text-text-primary">Access Restricted</h2>
        <p className="text-sm text-text-secondary">
          Only users with the administrator role are permitted to view platform analytics.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-[rgba(167,209,41,0.06)] rounded-lg text-lime-400 border border-[rgba(167,209,41,0.16)]">
          <BarChart3 className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-serif text-2xl font-medium text-text-primary">Platform analytics</h1>
          <p className="text-sm text-text-secondary">
            System performance, listings activity, and donations trends.
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-error/5 border border-error/20 text-error rounded-lg p-4 flex items-start space-x-2">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loadingData ? (
        <div className="flex flex-col items-center justify-center py-24 space-y-2">
          <Loader2 className="h-8 w-8 text-lime-400 animate-spin" />
          <p className="text-xs text-text-muted">Fetching platform database metrics...</p>
        </div>
      ) : (
        summary && (
          <AnalyticsCharts
            summary={summary}
            categories={categories}
            trends={trends}
            cities={cities}
            activity={activity}
          />
        )
      )}
    </div>
  );
}

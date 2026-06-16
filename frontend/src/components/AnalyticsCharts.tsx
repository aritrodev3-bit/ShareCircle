'use client';

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  AnalyticsSummary,
  CategoryBreakdownItem,
  DonationTrendItem,
  TopCityItem,
  PlatformActivityItem,
} from '@/types';
import { CHART_COLORS, CHART_THEME } from '@/lib/chart-theme';

interface AnalyticsChartsProps {
  summary: AnalyticsSummary;
  categories: CategoryBreakdownItem[];
  trends: DonationTrendItem[];
  cities: TopCityItem[];
  activity: PlatformActivityItem[];
}

export default function AnalyticsCharts({
  summary,
  categories,
  trends,
  cities,
  activity,
}: AnalyticsChartsProps) {
  // Format dates for display
  const formattedTrends = trends.map((item) => ({
    ...item,
    formattedDate: new Date(item.date).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    }),
  }));

  const formattedActivity = activity.map((item) => ({
    ...item,
    formattedDate: new Date(item.date).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    }),
  }));

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Metrics Summary Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            Total Donors
          </span>
          <span className="block font-serif text-2xl font-medium text-lime-400">
            {summary.total_donors}
          </span>
        </div>
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            Total Recipients
          </span>
          <span className="block font-serif text-2xl font-medium text-lime-400">
            {summary.total_recipients}
          </span>
        </div>
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            Total NGOs
          </span>
          <span className="block font-serif text-2xl font-medium text-lime-400">
            {summary.total_ngos}
          </span>
        </div>
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            People Helped
          </span>
          <span className="block font-serif text-2xl font-medium text-info">
            {summary.people_helped}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            Listed Items
          </span>
          <span className="block font-serif text-xl font-medium text-text-primary">
            {summary.total_items_listed}
          </span>
        </div>
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            Donated Items
          </span>
          <span className="block font-serif text-xl font-medium text-text-primary">
            {summary.total_items_donated}
          </span>
        </div>
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 text-center">
          <span className="block text-xs text-text-secondary uppercase tracking-wider mb-1">
            Total Requests
          </span>
          <span className="block font-serif text-xl font-medium text-text-primary">
            {summary.total_requests}
          </span>
        </div>
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donation Area Chart */}
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-5">
          <h3 className="font-serif text-base font-medium text-text-primary mb-4">
            Donation Trends (Last 30 Days)
          </h3>
          <div className="h-64">
            {trends.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-text-muted">No trend data yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={formattedTrends}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={CHART_THEME.gridColor} strokeDasharray="3 3" />
                  <XAxis dataKey="formattedDate" stroke={CHART_THEME.textColor} fontSize={10} />
                  <YAxis stroke={CHART_THEME.textColor} fontSize={10} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: CHART_THEME.backgroundColor,
                      borderColor: CHART_THEME.borderColor,
                      color: CHART_THEME.textColor,
                      borderRadius: '8px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    name="Donations"
                    stroke={CHART_COLORS.primary}
                    fillOpacity={1}
                    fill="url(#colorCount)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Category Breakdown Bar Chart */}
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-5">
          <h3 className="font-serif text-base font-medium text-text-primary mb-4">
            Donations by Category
          </h3>
          <div className="h-64">
            {categories.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-text-muted">No category data yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories}>
                  <CartesianGrid stroke={CHART_THEME.gridColor} strokeDasharray="3 3" />
                  <XAxis
                    dataKey="category"
                    stroke={CHART_THEME.textColor}
                    fontSize={10}
                    tickFormatter={(val) => val.charAt(0).toUpperCase() + val.slice(1)}
                  />
                  <YAxis stroke={CHART_THEME.textColor} fontSize={10} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: CHART_THEME.backgroundColor,
                      borderColor: CHART_THEME.borderColor,
                      color: CHART_THEME.textColor,
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="count" name="Items" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Cities Bar Chart */}
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-5">
          <h3 className="font-serif text-base font-medium text-text-primary mb-4">
            Donation Listings by City
          </h3>
          <div className="h-64">
            {cities.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-text-muted">No city data yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cities} layout="vertical">
                  <CartesianGrid stroke={CHART_THEME.gridColor} strokeDasharray="3 3" />
                  <XAxis type="number" stroke={CHART_THEME.textColor} fontSize={10} allowDecimals={false} />
                  <YAxis dataKey="city" type="category" stroke={CHART_THEME.textColor} fontSize={10} width={80} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: CHART_THEME.backgroundColor,
                      borderColor: CHART_THEME.borderColor,
                      color: CHART_THEME.textColor,
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="count" name="Listings" fill={CHART_COLORS.info} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Platform Daily Activity Multi Line Chart */}
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-5">
          <h3 className="font-serif text-base font-medium text-text-primary mb-4">
            Daily Platform Activity (Last 30 Days)
          </h3>
          <div className="h-64">
            {activity.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-text-muted">No activity data yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={formattedActivity}>
                  <CartesianGrid stroke={CHART_THEME.gridColor} strokeDasharray="3 3" />
                  <XAxis dataKey="formattedDate" stroke={CHART_THEME.textColor} fontSize={10} />
                  <YAxis stroke={CHART_THEME.textColor} fontSize={10} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: CHART_THEME.backgroundColor,
                      borderColor: CHART_THEME.borderColor,
                      color: CHART_THEME.textColor,
                      borderRadius: '8px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                  <Line
                    type="monotone"
                    dataKey="new_users"
                    name="New Users"
                    stroke={CHART_COLORS.info}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="new_items"
                    name="New Items"
                    stroke={CHART_COLORS.primary}
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="new_requests"
                    name="New Requests"
                    stroke={CHART_COLORS.warning}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/hooks/useSession';
import { updateProfile } from '@/lib/api';
import { UserRole } from '@/types';
import { Heart, Users, Building2, Gift, Loader2, AlertCircle, ChevronRight } from 'lucide-react';

interface RoleCard {
  role: UserRole;
  label: string;
  description: string;
  icon: React.ElementType;
  accent: string;
  bg: string;
  border: string;
  borderSelected: string;
}

const ROLE_CARDS: RoleCard[] = [
  {
    role: 'donor',
    label: 'Donor',
    description: 'I have items to share with people in need. I want to list donations and connect with recipients.',
    icon: Gift,
    accent: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-[rgba(52,211,153,0.10)]',
    borderSelected: 'border-emerald-400/60',
  },
  {
    role: 'recipient',
    label: 'Recipient',
    description: 'I am looking for donated items to support my household or personal needs.',
    icon: Users,
    accent: 'text-slate-300',
    bg: 'bg-slate-500/10',
    border: 'border-[rgba(148,163,184,0.10)]',
    borderSelected: 'border-slate-400/60',
  },
  {
    role: 'ngo',
    label: 'NGO / Organisation',
    description: 'We are a non-profit or community organisation distributing donations to many people at scale.',
    icon: Building2,
    accent: 'text-emerald-300',
    bg: 'bg-emerald-500/5',
    border: 'border-[rgba(52,211,153,0.08)]',
    borderSelected: 'border-emerald-300/60',
  },
];

export default function OnboardingPage() {
  const [selected, setSelected] = useState<UserRole | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();
  const { session, refreshSession } = useSession();

  const handleContinue = async () => {
    if (!selected) return;
    if (!session?.access_token) {
      setError('Session expired. Please log in again.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Patch role on backend
      await updateProfile({ role: selected }, session.access_token);

      // 2. Update cookie so middleware picks up the new role immediately
      document.cookie = `user-role=${selected}; path=/; max-age=86400; SameSite=Lax`;

      // 3. Refresh session so context picks up new profile
      await refreshSession();

      // 3. Redirect based on role
      if (selected === 'ngo') {
        router.push('/ngo/dashboard');
      } else {
        router.push('/browse');
      }
    } catch (err: any) {
      console.error('Onboarding failed:', err);
      setError(err.message || 'Could not save your role. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 bg-bg-primary">
      <div className="w-full max-w-2xl space-y-8">

        {/* Brand Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-3 bg-surface-1 border border-[rgba(52,211,153,0.10)] rounded-2xl mb-2">
            <Heart className="h-10 w-10 text-emerald-400 fill-emerald-400" />
          </div>
          <div>
            <h1 className="font-serif text-3xl font-medium text-text-primary tracking-tight">
              Welcome to GiveCircle
            </h1>
            <p className="text-sm text-text-secondary mt-3 max-w-md mx-auto leading-relaxed">
              To get started, tell us how you&apos;d like to participate in our community.
              You can always explore the platform after selecting your role.
            </p>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-rose-500/5 border border-rose-500/20 text-rose-400 rounded-xl p-4 flex items-start space-x-3 text-sm">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Role Cards */}
        <div className="space-y-3">
          {ROLE_CARDS.map((card) => {
            const Icon = card.icon;
            const isSelected = selected === card.role;
            return (
              <button
                key={card.role}
                type="button"
                disabled={loading}
                onClick={() => setSelected(card.role)}
                className={`w-full text-left rounded-2xl border p-5 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/60 cursor-pointer ${
                  isSelected
                    ? `bg-surface-1 ${card.borderSelected} ring-1 ring-inset ${card.borderSelected}`
                    : `bg-bg-secondary ${card.border} hover:bg-surface-1 hover:${card.borderSelected}`
                }`}
                aria-pressed={isSelected}
                id={`role-${card.role}`}
              >
                <div className="flex items-start space-x-4">
                  <div className={`flex-shrink-0 p-2.5 rounded-xl ${card.bg}`}>
                    <Icon className={`h-6 w-6 ${card.accent}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className={`font-medium text-base ${isSelected ? 'text-text-primary' : 'text-text-secondary'} transition-colors`}>
                        {card.label}
                      </span>
                      {isSelected && (
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${card.bg} ${card.accent} border ${card.borderSelected}`}>
                          Selected
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-text-muted mt-1 leading-relaxed">
                      {card.description}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Continue Button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={handleContinue}
            disabled={!selected || loading}
            className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:bg-surface-1 disabled:text-text-muted disabled:cursor-not-allowed text-slate-900 py-3 px-6 rounded-xl font-medium transition-all duration-200 flex items-center justify-center space-x-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/60 min-h-[48px]"
            id="onboarding-continue"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Saving your role...</span>
              </>
            ) : (
              <>
                <span>Continue to GiveCircle</span>
                <ChevronRight className="h-5 w-5" />
              </>
            )}
          </button>
          <p className="text-center text-xs text-text-muted mt-3">
            This sets your account type. Contact support to change roles later.
          </p>
        </div>

      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/utils/supabase/client';
import { getMe } from '@/lib/api';
import { Heart, Mail, Lock, Loader2, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();
  const supabase = createClient();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // 1. Sign in with Supabase Auth
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) {
        throw new Error(authError.message);
      }

      if (!data.session) {
        throw new Error('Could not establish an active session.');
      }

      // 2. Fetch profile from FastAPI backend
      const profile = await getMe(data.session.access_token);

      // 3. Set the user-role cookie for middleware routing (null if not yet assigned)
      document.cookie = `user-role=${profile.role ?? 'null'}; path=/; max-age=86400; SameSite=Lax`;

      // 4. Force router refresh and redirect
      router.refresh();
      if (!profile.role) {
        // New user without a role — send to onboarding
        router.push('/onboarding');
      } else {
        router.push('/browse');
      }
    } catch (err: any) {
      console.error('Login failed:', err);
      setError(err.message || 'Invalid email or password.');
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 bg-bg-primary">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center p-3 bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-2xl mb-4">
            <Heart className="h-10 w-10 text-lime-400 fill-lime-400" />
          </div>
          <h1 className="font-serif text-2xl font-medium text-text-primary tracking-tight">
            Welcome back to GiveCircle
          </h1>
          <p className="text-sm text-text-secondary mt-2">
            Share resources and support your local community
          </p>
        </div>

        {/* Card Form container */}
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-6 sm:p-8">
          {error && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-3 flex items-start space-x-2 text-sm mb-4">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-text-muted">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  required
                  placeholder="name@example.com"
                  className="pl-10 focus-ring"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-text-muted">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  placeholder="••••••••"
                  className="pl-10 focus-ring"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-lime-500 hover:bg-lime-700 text-bg-primary py-2.5 px-4 rounded-lg font-medium transition-all duration-150 flex items-center justify-center space-x-2 focus-ring mt-6 cursor-pointer min-h-[44px]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Logging in...</span>
                </>
              ) : (
                <span>Log in</span>
              )}
            </button>
          </form>
        </div>

        {/* Footer Link */}
        <p className="text-center text-sm text-text-secondary">
          Don&rsquo;t have an account?{' '}
          <Link href="/register" className="text-lime-400 hover:text-lime-500 font-medium focus-ring rounded p-0.5">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}

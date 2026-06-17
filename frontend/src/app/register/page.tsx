'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/utils/supabase/client';
import { register, getMe } from '@/lib/api';
import { UserRole } from '@/types';
import { Heart, Mail, Lock, User, Phone, Loader2, AlertCircle } from 'lucide-react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<UserRole>('recipient');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();
  const supabase = createClient();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // 1. Submit registration to our FastAPI backend API (which integrates with Supabase)
      await register({
        email,
        password,
        full_name: fullName,
        role,
        phone: phone ? phone : null,
      });

      // 2. Perform automatic login to fetch session cookies
      const { data, error: loginError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (loginError) {
        throw new Error(loginError.message);
      }

      if (!data.session) {
        throw new Error('Establish active session failed.');
      }

      // 3. Fetch profile from backend to verify role
      const profile = await getMe(data.session.access_token);

      // 4. Set the user-role cookie (null if not yet assigned)
      document.cookie = `user-role=${profile.role ?? 'null'}; path=/; max-age=86400; SameSite=Lax`;

      // 5. Force refresh and redirect
      router.refresh();
      if (!profile.role) {
        router.push('/onboarding');
      } else {
        router.push('/browse');
      }
    } catch (err: any) {
      console.error('Registration failed:', err);
      setError(err.message || 'Registration failed. Please try again.');
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
            Create your account
          </h1>
          <p className="text-sm text-text-secondary mt-2">
            Join GiveCircle to start sharing and receiving resources
          </p>
        </div>

        {/* Card container */}
        <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-6 sm:p-8">
          {error && (
            <div className="bg-error/5 border border-error/20 text-error rounded-lg p-3 flex items-start space-x-2 text-sm mb-4">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            {/* Full Name */}
            <div>
              <label htmlFor="fullName" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-text-muted">
                  <User className="h-4 w-4" />
                </div>
                <input
                  id="fullName"
                  type="text"
                  required
                  placeholder="John Doe"
                  className="pl-10 focus-ring"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Email Address */}
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
                  placeholder="john@example.com"
                  className="pl-10 focus-ring"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* Password */}
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
                  placeholder="•••••••• (Min. 8 characters)"
                  className="pl-10 focus-ring"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  minLength={8}
                />
              </div>
            </div>

            {/* Role selection - Admin excluded */}
            <div>
              <label htmlFor="role" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">
                Account Type
              </label>
              <select
                id="role"
                className="focus-ring cursor-pointer"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                disabled={loading}
              >
                <option value="recipient">Recipient (Individual seeking help)</option>
                <option value="donor">Donor (Individual offering help)</option>
                <option value="ngo">NGO (Non-profit organization)</option>
              </select>
            </div>

            {/* Phone (optional) */}
            <div>
              <label htmlFor="phone" className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider font-sans">
                Phone Number (Optional)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-text-muted">
                  <Phone className="h-4 w-4" />
                </div>
                <input
                  id="phone"
                  type="tel"
                  placeholder="555-0199"
                  className="pl-10 focus-ring"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  disabled={loading}
                />
              </div>
              <p className="text-[10px] text-text-muted mt-1 font-sans">
                Donor phone numbers are only visible to approved requesters.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-lime-500 hover:bg-lime-700 text-bg-primary py-2.5 px-4 rounded-lg font-medium transition-all duration-150 flex items-center justify-center space-x-2 focus-ring mt-6 cursor-pointer min-h-[44px]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Creating account...</span>
                </>
              ) : (
                <span>Register</span>
              )}
            </button>

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[rgba(167,209,41,0.08)]"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-surface-1 px-2 text-text-secondary">Or continue with</span>
              </div>
            </div>

            <a
              href="/api/backend/auth/login/google"
              className="w-full bg-surface-2 hover:bg-surface-3 text-text-primary border border-[rgba(167,209,41,0.15)] py-2.5 px-4 rounded-lg font-medium transition-all duration-150 flex items-center justify-center space-x-2 focus-ring cursor-pointer min-h-[44px]"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
              </svg>
              <span>Sign up with Google</span>
            </a>
          </form>
        </div>

        {/* Footer Link */}
        <p className="text-center text-sm text-text-secondary">
          Already have an account?{' '}
          <Link href="/login" className="text-lime-400 hover:text-lime-500 font-medium focus-ring rounded p-0.5">
            Log in here
          </Link>
        </p>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/utils/supabase/client';
import { getMe } from '@/lib/api';
import { Loader2 } from 'lucide-react';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function handleCallback() {
      try {
        const hash = window.location.hash;
        if (!hash) {
          throw new Error('No authentication details found in the response.');
        }

        const params = new URLSearchParams(hash.substring(1));
        const accessToken = params.get('access_token');
        const isNewUser = params.get('is_new_user') === 'true';

        if (!accessToken) {
          throw new Error('Access token not found in the response.');
        }

        const supabase = createClient();
        const { error: sessionError } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: params.get('refresh_token') || '',
        });

        if (sessionError) {
          throw new Error(sessionError.message);
        }

        const profile = await getMe(accessToken);

        document.cookie = `user-role=${profile.role ?? 'null'}; path=/; max-age=86400; SameSite=Lax`;

        router.refresh();
        if (!profile.role || isNewUser) {
          router.push('/onboarding');
        } else {
          router.push('/browse');
        }
      } catch (err: any) {
        console.error('Callback error:', err);
        setError(err.message || 'Authentication failed.');
      }
    }

    handleCallback();
  }, [router]);

  if (error) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 bg-bg-primary">
        <div className="w-full max-w-md p-6 bg-surface-1 border border-error/20 rounded-[14px] text-center space-y-4">
          <h2 className="text-xl font-serif text-error">Authentication Failed</h2>
          <p className="text-sm text-text-secondary">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="px-4 py-2 bg-lime-500 hover:bg-lime-600 text-bg-primary font-medium rounded-lg cursor-pointer"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 bg-bg-primary">
      <div className="text-center space-y-4">
        <Loader2 className="h-10 w-10 animate-spin text-lime-400 mx-auto" />
        <h2 className="text-lg font-serif text-text-primary">Completing sign in...</h2>
        <p className="text-sm text-text-secondary">Please wait while we set up your session.</p>
      </div>
    </div>
  );
}

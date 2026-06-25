'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { createClient } from '@/utils/supabase/client';
import { getMe } from '@/lib/api';
import { UserOut } from '@/types';
import { Session, User } from '@supabase/supabase-js';

interface SessionContextType {
  session: Session | null;
  user: User | null;
  profile: UserOut | null;
  loading: boolean;
  refreshSession: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({
  children,
  initialProfile,
}: {
  children: React.ReactNode;
  initialProfile?: UserOut | null;
}) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserOut | null>(initialProfile || null);
  const [loading, setLoading] = useState(true);

  const supabase = createClient();

  const fetchProfile = async (accessToken: string) => {
    try {
      const p = await getMe(accessToken);
      setProfile(p);
      if (p) {
        document.cookie = `user-role=${p.role ?? 'null'}; path=/; max-age=86400; SameSite=Lax`;
      }
    } catch (err) {
      console.error('Failed to fetch user profile:', err);
      setProfile(null);
    }
  };

  const refreshSession = async () => {
    setLoading(true);
    try {
      const { data: { session: newSession }, error } = await supabase.auth.refreshSession();
      if (error) throw error;
      if (newSession) {
        setSession(newSession);
        setUser(newSession.user);
        await fetchProfile(newSession.access_token);
      } else {
        setSession(null);
        setUser(null);
        setProfile(null);
      }
    } catch (err) {
      console.error('Error refreshing session:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;

    // Get initial session
    supabase.auth.getSession().then(({ data: { session: initialSession } }) => {
      if (!mounted) return;
      if (initialSession) {
        setSession(initialSession);
        setUser(initialSession.user);
        // Only fetch if we don't already have an initial profile from SSR
        if (!initialProfile) {
          fetchProfile(initialSession.access_token).finally(() => {
            if (mounted) setLoading(false);
          });
        } else {
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    });

    // Subscribe to auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, currentSession) => {
        if (!mounted) return;
        setSession(currentSession);
        setUser(currentSession?.user ?? null);

        if (currentSession) {
          await fetchProfile(currentSession.access_token);
        } else {
          setProfile(null);
        }
        setLoading(false);
      }
    );

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [initialProfile]);

  useEffect(() => {
    if (profile) {
      document.cookie = `user-role=${profile.role ?? 'null'}; path=/; max-age=86400; SameSite=Lax`;
    }
  }, [profile]);

  return (
    <SessionContext.Provider value={{ session, user, profile, loading, refreshSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSessionContext must be used within a SessionProvider');
  }
  return context;
}

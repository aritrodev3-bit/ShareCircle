'use client';

import { useSessionContext } from '@/providers/SessionProvider';

export function useSession() {
  return useSessionContext();
}

import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';
import { createClient } from '@/utils/supabase/server';
import { getMe } from '@/lib/api';
import { UserOut } from '@/types';

import { SessionProvider } from '@/providers/SessionProvider';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'GiveCircle - Community Donation Platform',
  description: 'Connecting donors, recipients, and NGOs to share resources in local communities.',
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  let dbUser: UserOut | null = null;

  try {
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      dbUser = await getMe(session.access_token);
    }
  } catch (error) {
    console.error('Error loading user profile in layout:', error);
    // Silent fail so layout still renders (middleware will redirect if route is protected)
  }

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg-primary text-text-secondary">
        <SessionProvider initialProfile={dbUser}>
          <Navbar dbUser={dbUser} />
          <main className="flex-1 w-full max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col">
            {children}
          </main>
          <footer className="w-full max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 py-6 border-t border-[rgba(167,209,41,0.08)] text-center text-xs text-text-muted">
            <p>© {new Date().getFullYear()} GiveCircle. All rights reserved.</p>
          </footer>
        </SessionProvider>
      </body>
    </html>
  );
}

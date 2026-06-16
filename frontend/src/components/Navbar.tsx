'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createClient } from '@/utils/supabase/client';
import { UserOut } from '@/types';
import { Menu, X, LogOut, Heart, LayoutDashboard, Search, FileText, BarChart2 } from 'lucide-react';

import { useSession } from '@/hooks/useSession';

interface NavbarProps {
  dbUser: UserOut | null;
}

export default function Navbar({ dbUser: propDbUser }: NavbarProps) {
  const { profile: contextProfile } = useSession();
  const dbUser = contextProfile || propDbUser;

  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    // Clear user-role cookie
    document.cookie = 'user-role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    router.refresh();
    router.push('/login');
  };

  const isActive = (path: string) => pathname === path;

  // Navigation Links based on role
  const getNavLinks = () => {
    if (!dbUser) return [];

    const links = [{ label: 'Browse', path: '/browse', icon: Search }];

    if (dbUser.role === 'donor') {
      links.push(
        { label: 'My Listings', path: '/donor/listings', icon: LayoutDashboard },
        { label: 'Outgoing Requests', path: '/requests', icon: FileText }
      );
    } else if (dbUser.role === 'recipient') {
      links.push({ label: 'My Requests', path: '/requests', icon: FileText });
    } else if (dbUser.role === 'ngo') {
      links.push(
        { label: 'NGO Dashboard', path: '/ngo/dashboard', icon: LayoutDashboard },
        { label: 'My Requests', path: '/requests', icon: FileText }
      );
    } else if (dbUser.role === 'admin') {
      links.push({ label: 'Analytics', path: '/admin/analytics', icon: BarChart2 });
    }

    return links;
  };

  const navLinks = getNavLinks();

  return (
    <nav className="bg-bg-secondary border-b border-[rgba(167,209,41,0.08)] sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href={dbUser ? '/browse' : '/login'} className="flex items-center space-x-2 focus-ring rounded-lg p-1">
              <Heart className="h-6 w-6 text-lime-400 fill-lime-400" />
              <span className="font-serif text-xl tracking-tight text-text-primary">
                GiveCircle
              </span>
            </Link>
          </div>

          {/* Desktop Nav */}
          {dbUser && (
            <div className="hidden md:flex items-center space-x-4">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const active = isActive(link.path);
                return (
                  <Link
                    key={link.path}
                    href={link.path}
                    className={`flex items-center space-x-1 px-3 py-2 rounded-lg text-sm transition-all duration-150 focus-ring ${
                      active
                        ? 'text-lime-400 bg-surface-1 border border-[rgba(167,209,41,0.16)]'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </div>
          )}

          {/* User profile & Logout */}
          {dbUser ? (
            <div className="hidden md:flex items-center space-x-4">
              <div className="flex flex-col text-right">
                <span className="text-sm font-medium text-text-primary">{dbUser.full_name}</span>
                <span className="text-[10px] text-text-muted uppercase tracking-wider">{dbUser.role}</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-1 px-3 py-2 bg-transparent text-error border border-transparent hover:border-error/20 hover:bg-error/5 rounded-lg text-sm transition-all duration-150 focus-ring cursor-pointer min-h-[40px]"
                title="Log out"
              >
                <LogOut className="h-4 w-4" />
                <span>Log out</span>
              </button>
            </div>
          ) : (
            <div className="hidden md:flex items-center space-x-4">
              <Link
                href="/login"
                className="text-text-secondary hover:text-text-primary px-3 py-2 text-sm focus-ring rounded-lg"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="bg-lime-500 text-bg-primary hover:bg-lime-700 px-4 py-2 rounded-lg text-sm transition-all duration-150 focus-ring border-none"
              >
                Register
              </Link>
            </div>
          )}

          {/* Mobile menu button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex items-center justify-center p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-hover focus-ring min-h-[44px] min-w-[44px]"
              aria-expanded="false"
            >
              <span className="sr-only">Open main menu</span>
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden bg-bg-tertiary border-b border-[rgba(167,209,41,0.08)]">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            {dbUser ? (
              <>
                <div className="px-3 py-2 border-b border-[rgba(167,209,41,0.08)] mb-2">
                  <p className="text-sm font-medium text-text-primary">{dbUser.full_name}</p>
                  <p className="text-xs text-text-muted capitalize">{dbUser.role}</p>
                </div>
                {navLinks.map((link) => {
                  const Icon = link.icon;
                  const active = isActive(link.path);
                  return (
                    <Link
                      key={link.path}
                      href={link.path}
                      onClick={() => setIsOpen(false)}
                      className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-base transition-all duration-150 focus-ring min-h-[44px] ${
                        active
                          ? 'text-lime-400 bg-surface-1 border border-[rgba(167,209,41,0.16)]'
                          : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{link.label}</span>
                    </Link>
                  );
                })}
                <button
                  onClick={() => {
                    setIsOpen(false);
                    handleLogout();
                  }}
                  className="flex w-full items-center space-x-2 px-3 py-3 text-left text-error hover:bg-error/5 rounded-lg text-base transition-all duration-150 focus-ring min-h-[44px] mt-2 cursor-pointer"
                >
                  <LogOut className="h-5 w-5" />
                  <span>Log out</span>
                </button>
              </>
            ) : (
              <div className="space-y-2 p-2">
                <Link
                  href="/login"
                  onClick={() => setIsOpen(false)}
                  className="block text-center text-text-secondary hover:text-text-primary px-3 py-2.5 rounded-lg text-base border border-[rgba(167,209,41,0.16)] min-h-[44px]"
                >
                  Log in
                </Link>
                <Link
                  href="/register"
                  onClick={() => setIsOpen(false)}
                  className="block text-center bg-lime-500 text-bg-primary hover:bg-lime-700 px-3 py-2.5 rounded-lg text-base transition-all duration-150 min-h-[44px]"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}

import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({
            request,
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const url = request.nextUrl.clone();
  const path = url.pathname;

  // 1. Authentication Redirects
  const isAuthPage = path === '/login' || path === '/register';
  const isOnboardingPage = path === '/onboarding';
  const isPublicPage =
    isAuthPage ||
    isOnboardingPage ||
    path === '/' ||
    path.startsWith('/_next') ||
    path.startsWith('/api/') ||
    path === '/favicon.ico';

  if (!user && !isPublicPage) {
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  if (user && isAuthPage) {
    url.pathname = '/browse';
    return NextResponse.redirect(url);
  }

  // 2. Role null-guard: redirect authenticated users without a role to onboarding
  if (user && !isOnboardingPage && !isPublicPage) {
    const roleCookie = request.cookies.get('user-role')?.value;

    // Cookie value 'null' or missing cookie signals no role assigned yet.
    // The login/register pages set this cookie after fetching the profile.
    if (!roleCookie || roleCookie === 'null') {
      url.pathname = '/onboarding';
      return NextResponse.redirect(url);
    }

    // 3. Role Guards — protect role-scoped routes
    if (path.startsWith('/donor') && roleCookie !== 'donor') {
      url.pathname = '/browse';
      return NextResponse.redirect(url);
    }
    if (path.startsWith('/ngo') && roleCookie !== 'ngo') {
      url.pathname = '/browse';
      return NextResponse.redirect(url);
    }
    if (path.startsWith('/admin') && roleCookie !== 'admin') {
      url.pathname = '/browse';
      return NextResponse.redirect(url);
    }
    if (path.startsWith('/requests') && roleCookie !== 'recipient' && roleCookie !== 'ngo') {
      url.pathname = '/browse';
      return NextResponse.redirect(url);
    }
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const currentEnv = process.env.NODE_ENV;
  
  // Force HTTPS in production
  if (currentEnv === 'production' && request.headers.get('x-forwarded-proto') !== 'https' && !request.url.startsWith('https://')) {
    const httpsUrl = request.url.replace(/^http:/, 'https:');
    return NextResponse.redirect(httpsUrl, 301);
  }
  
  return NextResponse.next();
}

export const config = {
  // Apply to all routes except static assets and API routes (if any are handled by Next)
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};

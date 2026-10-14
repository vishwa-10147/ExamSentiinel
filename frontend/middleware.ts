import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Force HTTPS in production — but only when a proxy (ALB / CloudFront)
  // explicitly says the client used plain HTTP. Load-balancer health checks
  // reach the container directly without that header and must get a 200,
  // not a redirect loop.
  if (process.env.NODE_ENV === 'production' && request.headers.get('x-forwarded-proto') === 'http') {
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

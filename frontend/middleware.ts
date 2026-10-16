import { NextResponse } from "next/server";

// HTTP-to-HTTPS redirection is done by the front door that terminates TLS (nginx in
// deploy/campus and deploy/rehearsal, the load balancer listener on AWS), which knows the public
// address. Redirecting here was wrong: Next's own server marks plain requests as
// x-forwarded-proto=http and builds request.url from its bind address, so every page redirected
// to https://0.0.0.0:3000 when the app was served directly (e.g. docker-compose.yml).
export function middleware() {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

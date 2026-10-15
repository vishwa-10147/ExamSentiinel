/** @type {import('next').NextConfig} */

const isProduction = process.env.NODE_ENV === "production";

// The API (and its WebSockets) may live on another origin, e.g. https://api.exam.example.edu.
function apiOrigins() {
  const raw = process.env.NEXT_PUBLIC_API_URL || (isProduction ? "" : "http://localhost:8000");
  if (!raw) return [];
  try {
    const url = new URL(raw);
    const ws = `${url.protocol === "https:" ? "wss:" : "ws:"}//${url.host}`;
    return [url.origin, ws];
  } catch {
    return [];
  }
}

// Everything the app loads is served by itself (Monaco and the face model included), so the
// policy only names this origin and the API. 'unsafe-inline' scripts are needed by Next.js'
// inline bootstrap; 'unsafe-eval' only by the development server's hot reload.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isProduction ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  `connect-src 'self' ${apiOrigins().join(" ")}${isProduction ? "" : " ws://localhost:3000"}`,
  "media-src 'self' blob:",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // Exams and interviews need the camera and microphone of this site only.
  { key: "Permissions-Policy", value: "camera=(self), microphone=(self), fullscreen=(self), geolocation=(), payment=(), usb=()" },
  ...(isProduction ? [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }] : []),
];

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  images: {
    unoptimized: true,
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

// NEXT_PUBLIC_API_URL is compiled into the bundle: a production build without it would talk to
// localhost from every student's browser. Fail the build instead.
module.exports = (phase) => {
  if (phase === "phase-production-build" && !process.env.NEXT_PUBLIC_API_URL) {
    throw new Error("NEXT_PUBLIC_API_URL must be set for a production build (the public API origin).");
  }
  return nextConfig;
};

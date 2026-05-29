/** @type {import('next').NextConfig} */

// Server-side proxy target. The browser makes relative /api/* + /health/*
// calls; Next.js (running inside the frontend container) rewrites them to
// the in-cluster backend service. Override with BACKEND_URL /
// BACKEND_INTERNAL_URL; defaults to the k8s service.
const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.BACKEND_INTERNAL_URL ||
  "http://dclaw-marketing-backend:8102";

const nextConfig = {
  output: "standalone",
  skipTrailingSlashRedirect: true,
  async redirects() {
    return [
      { source: "/agent", destination: "/conductor", permanent: true },
    ];
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/health/:path*", destination: `${BACKEND_URL}/health/:path*` },
    ];
  },
};

export default nextConfig;

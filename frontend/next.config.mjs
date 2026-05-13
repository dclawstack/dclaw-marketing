/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // For the server-side proxy (Next.js running inside the frontend
    // container), we need a hostname reachable from THAT container —
    // typically the docker service name `backend`. The browser-facing
    // NEXT_PUBLIC_API_URL is the host's externally-published address
    // (`http://127.0.0.1:8102`), which would point at the frontend
    // container's own loopback if used here. Prefer BACKEND_INTERNAL_URL
    // when set; fall back to NEXT_PUBLIC_API_URL otherwise.
    const apiUrl =
      process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      console.warn(
        "Neither BACKEND_INTERNAL_URL nor NEXT_PUBLIC_API_URL set — API proxy disabled",
      );
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: "/health/:path*",
        destination: `${apiUrl}/health/:path*`,
      },
    ];
  },
};

export default nextConfig;

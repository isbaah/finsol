import type { NextConfig } from "next";

// Server-only (no NEXT_PUBLIC_ prefix — never sent to the browser). Proxying
// through our own domain keeps Django's Set-Cookie (session/CSRF) scoped to
// this frontend's host instead of the backend's, since frontend and backend
// sit on unrelated *.up.railway.app hostnames with no shared parent domain
// to set a cross-site cookie on.
const backendOrigin = (process.env.BACKEND_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Enables the minimal `.next/standalone` server the production Dockerfile
  // copies into its final stage — see frontend/Dockerfile's `runner` stage.
  output: "standalone",
  async rewrites() {
    return [
      { source: "/accounts/:path*", destination: `${backendOrigin}/accounts/:path*` },
      { source: "/_allauth/:path*", destination: `${backendOrigin}/_allauth/:path*` },
      { source: "/api/v1/:path*", destination: `${backendOrigin}/api/v1/:path*` },
    ];
  },
};

export default nextConfig;

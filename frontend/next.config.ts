import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enables the minimal `.next/standalone` server the production Dockerfile
  // copies into its final stage — see frontend/Dockerfile's `runner` stage.
  output: "standalone",
};

export default nextConfig;

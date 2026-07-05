import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const apiBaseUrl = process.env.BLACKOUT_API_BASE_URL || "http://127.0.0.1:5000";
const projectRoot = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: projectRoot,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`
      }
    ];
  }
};

export default nextConfig;

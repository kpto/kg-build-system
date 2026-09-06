import type { NextConfig } from "next";

/**
 * The studio backend owns REST and WebSocket on its own origin, so the UI talks
 * to it directly rather than through a proxy that would have to special-case
 * sockets. `STUDIO_BACKEND_ORIGIN` is baked in at build time.
 */
const backend = process.env.STUDIO_BACKEND_ORIGIN ?? "http://127.0.0.1:8700";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Dev requests arrive as http://127.0.0.1:3000 as well as localhost, and Next
  // refuses a cross-origin dev build rather than serving it.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  env: {
    STUDIO_BACKEND_ORIGIN: backend,
    STUDIO_WS_ORIGIN: backend.replace(/^http/, "ws") + "/ws",
  },
};

export default nextConfig;

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /** Satisfies Next 16 when a `webpack` hook exists; production build may still use Turbopack. */
  turbopack: {},
  /**
   * USB / network drives often miss or duplicate native FS events, which makes
   * dev watchers think files changed over and over → Fast Refresh loops.
   * Set NEXT_WEBPACK_POLL=1 before `npm run dev` to use polling (more CPU, steadier on USB).
   */
  webpack: (config, { dev }) => {
    if (dev && process.env.NEXT_WEBPACK_POLL === "1") {
      config.watchOptions = {
        ...config.watchOptions,
        poll: 1000,
        aggregateTimeout: 400,
      };
    }
    return config;
  },
};

export default nextConfig;

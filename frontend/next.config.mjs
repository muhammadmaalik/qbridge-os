/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  turbopack: {},
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

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Remove serverActions as it's now default
  },
  webpack: (config) => {
    config.externals = [...(config.externals || []), 'canvas', 'jsdom'];
    return config;
  }
}

module.exports = nextConfig 
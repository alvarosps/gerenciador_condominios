/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Use Node.js server mode instead of static export
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
  eslint: {
    // Only run ESLint on these directories during production builds
    dirs: ['app', 'components', 'lib', 'hooks', 'store'],
  },
  // Skip build errors for pages that can't be statically generated
  typescript: {
    ignoreBuildErrors: false,
  },
  // Continue build even if some pages fail during static generation
  staticPageGenerationTimeout: 1000,
  // Disable static page generation for error pages
  onDemandEntries: {
    maxInactiveAge: 60 * 1000,
    pagesBufferLength: 5,
  },
};

module.exports = nextConfig;

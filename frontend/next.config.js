/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Use Node.js server mode instead of static export
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
  skipTrailingSlashRedirect: true,
  async rewrites() {
    // Determine the destination URL: use BACKEND_URL or NEXT_PUBLIC_API_URL (without /api at the end if it has it, or handle it carefully)
    // To be safe, if we just use an env var like BACKEND_API_URL
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8008/api';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
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
  staticPageGenerationTimeout: 120,
  // Disable static page generation for error pages
  onDemandEntries: {
    maxInactiveAge: 60 * 1000,
    pagesBufferLength: 5,
  },
};

module.exports = nextConfig;

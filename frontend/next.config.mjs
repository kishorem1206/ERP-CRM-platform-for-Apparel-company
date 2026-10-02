/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  async headers() {
    // This is an authenticated admin dashboard — every page shows live
    // business data, so navigations must never be served stale from a
    // browser/CDN disk cache. Next.js otherwise statically optimizes
    // client-rendered pages with a 1-year s-maxage, which silently hides
    // every future deploy behind the user's cached copy until they clear
    // it. Hashed build assets under /_next/static are excluded — those are
    // content-addressed and safe to cache forever.
    return [
      {
        source: "/((?!_next/static|_next/image|favicon.ico).*)",
        headers: [{ key: "Cache-Control", value: "no-store, must-revalidate" }],
      },
    ];
  },
};

export default nextConfig;

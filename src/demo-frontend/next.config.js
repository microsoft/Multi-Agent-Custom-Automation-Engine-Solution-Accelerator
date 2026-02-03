/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React Strict Mode for better development experience
  reactStrictMode: true,

  // Optimize images from external sources
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_TWILIO_NUMBER: process.env.NEXT_PUBLIC_TWILIO_NUMBER,
    NEXT_PUBLIC_VOICE_WEBSOCKET_URL: process.env.NEXT_PUBLIC_VOICE_WEBSOCKET_URL,
  },

  // Experimental features for Next.js 15
  experimental: {
    // Enable server actions (default in Next.js 15)
  },
};

export default nextConfig;

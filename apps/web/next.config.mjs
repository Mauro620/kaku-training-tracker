/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@training-tracker/contracts"],
  // Las variables públicas del cliente viven acá. NEXT_PUBLIC_API_URL la usa
  // lib/api/client.ts para apuntar al backend.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1",
  },
};

export default nextConfig;

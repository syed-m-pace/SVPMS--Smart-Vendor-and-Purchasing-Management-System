/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    reactStrictMode: false,
    eslint: {
        ignoreDuringBuilds: true,
    },
};

export default nextConfig;

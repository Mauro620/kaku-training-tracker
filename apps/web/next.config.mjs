import withSerwistInit from "@serwist/next";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@training-tracker/contracts"],
  // Las variables públicas del cliente viven acá. NEXT_PUBLIC_API_URL la usa
  // lib/api/client.ts para apuntar al backend. El fallback es el puerto por
  // defecto de .env.example (8000), no el de una máquina en particular.
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  },
};

// El service worker precachea el shell estático (JS/CSS/fuentes/páginas) para
// que la PWA sea instalable y arranque rápido en visitas repetidas. NO
// cachea llamadas al API (viven en otro origen, http://localhost:8001, y
// ningún matcher de defaultCache las toca): la sincronización offline de
// datos sigue siendo trabajo de la Fase 5 (Dexie + cola de salida), esto
// no se adelanta a esa fase.
const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development",
});

export default withSerwist(nextConfig);

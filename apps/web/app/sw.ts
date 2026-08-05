import { defaultCache } from "@serwist/next/worker";
import { installSerwist } from "@serwist/sw";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

// Precachea el shell estático (JS/CSS/fuentes/páginas) para que la PWA sea
// instalable y arranque rápido. `defaultCache` no matchea nada fuera del
// origen de Next.js: las llamadas al API (otro puerto, otro origen) pasan
// directo a la red, sin caché. La sincronización de datos offline sigue
// siendo trabajo de la Fase 5, no de este service worker.
installSerwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache,
});

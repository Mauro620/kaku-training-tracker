# Web (Next.js)

PWA de la app de rendimiento. App Router, TS estricto, Tailwind v3.

## Comandos

```bash
pnpm dev          # http://localhost:3000
pnpm build
pnpm typecheck
pnpm lint
pnpm generate:api # regenera packages/contracts/src/api.ts desde el OpenAPI
```

## Variables de entorno

- `NEXT_PUBLIC_API_URL`: URL del backend. Default `http://localhost:8001/api/v1`.

## Estructura

- `app/(auth)/login/` — formulario de login.
- `app/(tabs)/hoy/` — pantalla Hoy: sueño + bienestar + hábitos (Fase 3).
- `app/(tabs)/{entreno,cocina,progreso}/` — placeholders de fases 4/6/8.
- `components/ui/` — primitivos del DESIGN.md (BentoCard, MetricDisplay,
  CircularProgressRing, PillSelectorGroup, CheckTile).
- `components/hoy/` — composición específica de la pantalla.
- `components/nav/` — BottomNav + TabPlaceholder.
- `lib/api/client.ts` — fetch wrapper con JWT, refresh una vez.
- `lib/api/hooks.ts` — TanStack Query hooks de Fase 3.
- `lib/auth.ts` — localStorage del JWT.
- `lib/query-provider.tsx` — QueryClient con staleTime alto.

## Pendiente

- Service worker + offline (fase 5). El manifest está pero sin íconos.
- Refresh automático proactivo del token (hoy solo reintenta una vez al 401).
- Las pestañas Entreno/Cocina/Progreso son placeholders.
- El Estado del día muestra `—` hasta fase 8.
- Recharts para gráficas (fase 8).

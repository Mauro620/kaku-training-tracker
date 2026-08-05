// El JWT vive en localStorage. Sin Dexie todavía (fase 5). Esto es lo
// suficientemente bueno para Fase 3: si el usuario cierra la pestaña, tiene
// que volver a loguearse. Eso es preferible a meter cookies + CSRF para
// una app monousuario que solo corre en su celular.

const CLAVE_ACCESS = "tt.access_token";
const CLAVE_REFRESH = "tt.refresh_token";

export function guardarTokens(access: string, refresh: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CLAVE_ACCESS, access);
  window.localStorage.setItem(CLAVE_REFRESH, refresh);
}

export function leerAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CLAVE_ACCESS);
}

export function leerRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CLAVE_REFRESH);
}

export function limpiarTokens() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(CLAVE_ACCESS);
  window.localStorage.removeItem(CLAVE_REFRESH);
}

export function haySesion(): boolean {
  return leerAccessToken() !== null;
}

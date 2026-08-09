import { limpiarTokens, leerAccessToken, leerRefreshToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    mensaje: string,
  ) {
    super(mensaje);
  }
}

type Opciones = {
  metodo?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  cuerpo?: unknown;
  parametros?: Record<string, string | number | undefined>;
  // Si false, no adjunta el access token (usado para /auth/login).
  conAuth?: boolean;
};

async function parsear<R>(respuesta: Response): Promise<R> {
  if (respuesta.status === 204) return undefined as R;
  const texto = await respuesta.text();
  if (!texto) return undefined as R;
  if (!respuesta.ok) {
    let detalle: string;
    try {
      detalle = (JSON.parse(texto) as { detail?: string }).detail ?? texto;
    } catch {
      detalle = texto;
    }
    throw new ApiError(respuesta.status, detalle);
  }
  return JSON.parse(texto) as R;
}

// El refresh ROTA el token en el backend (una sola vez es valido, ver
// auth.py::refresh): si dos requests pegan 401 casi juntas (TanStack Query
// dispara varias en paralelo, ej. la pantalla Hoy), cada una llamaba a esto
// por separado. La primera rotaba el token y guardaba el nuevo; la segunda
// todavia tenia el viejo en memoria, el backend ya no lo reconocia (401),
// y limpiarTokens() borraba TODO -- incluido el token bueno que la primera
// acababa de guardar. Un solo refresh en vuelo, todas las llamadas
// concurrentes esperan la MISMA promesa en vez de disparar una cada una.
let refrescoEnCurso: Promise<boolean> | null = null;

async function intentarRefresh(): Promise<boolean> {
  if (refrescoEnCurso) return refrescoEnCurso;
  refrescoEnCurso = ejecutarRefresh().finally(() => {
    refrescoEnCurso = null;
  });
  return refrescoEnCurso;
}

async function ejecutarRefresh(): Promise<boolean> {
  const refresh = leerRefreshToken();
  if (!refresh) return false;
  try {
    const respuesta = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!respuesta.ok) return false;
    const data = (await respuesta.json()) as {
      access_token: string;
      refresh_token: string;
    };
    if (typeof window !== "undefined") {
      window.localStorage.setItem("tt.access_token", data.access_token);
      window.localStorage.setItem("tt.refresh_token", data.refresh_token);
    }
    return true;
  } catch {
    return false;
  }
}

async function llamar<R>(
  path: string,
  opciones: Opciones = {},
): Promise<R> {
  const { metodo = "GET", cuerpo, parametros, conAuth = true } = opciones;

  // new URL(path, API) descartaría el /api/v1 de la base (path empieza con "/").
  const url = new URL(`${API}${path}`);
  if (parametros) {
    for (const [clave, valor] of Object.entries(parametros)) {
      if (valor !== undefined) url.searchParams.set(clave, String(valor));
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (conAuth) {
    const access = leerAccessToken();
    if (access) headers.Authorization = `Bearer ${access}`;
  }

  const fetchOpts: RequestInit = {
    method: metodo,
    headers,
  };
  if (cuerpo !== undefined) fetchOpts.body = JSON.stringify(cuerpo);

  let respuesta = await fetch(url.toString(), fetchOpts);

  // Token expirado: intentar refresh una vez y reintentar.
  if (respuesta.status === 401 && conAuth) {
    const refrescado = await intentarRefresh();
    if (refrescado) {
      headers.Authorization = `Bearer ${leerAccessToken()}`;
      respuesta = await fetch(url.toString(), { ...fetchOpts, headers });
    } else {
      limpiarTokens();
    }
  }

  return parsear<R>(respuesta);
}

export const api = {
  get: <T>(path: string, opciones?: Omit<Opciones, "metodo" | "cuerpo">) =>
    llamar<T>(path, { ...opciones, metodo: "GET" }),
  post: <T>(path: string, cuerpo: unknown, opciones?: Omit<Opciones, "metodo" | "cuerpo">) =>
    llamar<T>(path, { ...opciones, metodo: "POST", cuerpo }),
  put: <T>(path: string, cuerpo: unknown, opciones?: Omit<Opciones, "metodo" | "cuerpo">) =>
    llamar<T>(path, { ...opciones, metodo: "PUT", cuerpo }),
  patch: <T>(path: string, cuerpo: unknown, opciones?: Omit<Opciones, "metodo" | "cuerpo">) =>
    llamar<T>(path, { ...opciones, metodo: "PATCH", cuerpo }),
  delete: <T>(path: string, opciones?: Omit<Opciones, "metodo" | "cuerpo">) =>
    llamar<T>(path, { ...opciones, metodo: "DELETE" }),
};

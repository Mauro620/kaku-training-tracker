import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";

// ---------- Tipos espejo del backend ----------
// Mantengo los tipos cerca del hook en vez de importarlos del OpenAPI
// generado: el cliente los valida en runtime con Pydantic y el contrato es
// chico. Si crece, los muevo a un archivo aparte.

export type RegistroSueno = {
  id: number;
  fecha: string;
  inicio: string;
  fin: string;
  celular_fuera: boolean | null;
  origen: "manual" | "health_kit" | "notion_backfill";
  horas_sueno: string;
};

export type RegistroBienestar = {
  id: number;
  fecha: string;
  sueno_pobre: number;
  fatiga: number;
  dolor_muscular: number;
  estres: number;
  hooper: number;
};

export type Habito = {
  id: number;
  nombre: string;
  activo: boolean;
  orden: number;
};

export type HabitoRegistro = {
  habito_id: number;
  fecha: string;
  valor: boolean;
};

export type Parametro = {
  clave: string;
  valor: string;
  unidad: string | null;
  descripcion: string;
};

export type RegistroHidratacion = {
  id: number;
  fecha: string;
  ml_totales: number;
};

export type UsuarioPerfil = {
  id: string;
  nombre: string;
  peso_objetivo_kg: string | null;
  agua_objetivo_ml_min: number | null;
  agua_objetivo_ml_max: number | null;
};

// ---------- Fase 4: sesion, serie, molestia, catalogos ----------

export type TipoSesion = {
  id: number;
  codigo: string;
  nombre: string;
  demanda: "alta" | "media" | "baja";
};

export type Ejercicio = {
  id: number;
  nombre: string;
  patron: string | null;
  carga_lumbar: "alta" | "media" | "baja";
};

export type ZonaCorporal = {
  id: number;
  nombre: string;
};

export type Serie = {
  id: number;
  sesion_id: string;
  ejercicio_id: number;
  orden: number;
  series: number;
  reps: number;
  peso_kg: string | null;
  rpe: number | null;
  dolor_lumbar: boolean;
};

export type Sesion = {
  id: string;
  usuario_id: string;
  sesion_plan_id: number | null;
  fecha: string;
  tipo_sesion_id: number;
  duracion_min: number;
  rpe: number;
  nota: string | null;
  carga_srpe: number;
  registrado_en: string;
  series: Serie[];
};

export type Molestia = {
  id: number;
  usuario_id: string;
  fecha: string;
  zona_id: number;
  intensidad: number;
  nota: string | null;
};

// ---------- Queries ----------

export const QUERY_HOY = ["cierre-del-dia", "hoy"] as const;

export function useSuenoDeHoy(fecha: string) {
  return useQuery({
    queryKey: ["sueno", fecha],
    queryFn: () => api.get<RegistroSueno>(`/sueno/${fecha}`),
    // 404 = no hay registro todavía, no es un error de carga.
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });
}

export function useBienestarDeHoy(fecha: string) {
  return useQuery({
    queryKey: ["bienestar", fecha],
    queryFn: () => api.get<RegistroBienestar>(`/bienestar/${fecha}`),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });
}

export function useParametro(clave: string) {
  return useQuery({
    queryKey: ["parametro", clave],
    queryFn: () => api.get<Parametro>(`/parametros/${clave}`),
    staleTime: Infinity, // un umbral de negocio no cambia en medio de una sesión
  });
}

export function useHabitos() {
  return useQuery({
    queryKey: ["habitos"],
    queryFn: () => api.get<Habito[]>("/habitos"),
  });
}

export function useHabitosDeHoy(fecha: string) {
  return useQuery({
    queryKey: ["habitos", "registro", fecha],
    queryFn: () => api.get<HabitoRegistro[]>(`/habitos/registro/${fecha}`),
  });
}

export function useUsuarioActual() {
  return useQuery({
    queryKey: ["usuario", "me"],
    queryFn: () => api.get<UsuarioPerfil>("/auth/me"),
    staleTime: Infinity,
  });
}

export function useHidratacionDeHoy(fecha: string) {
  return useQuery({
    queryKey: ["hidratacion", fecha],
    queryFn: () => api.get<RegistroHidratacion>(`/hidratacion/${fecha}`),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });
}

// ---------- Mutations ----------

export function useUpsertSueno(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { inicio: string; fin: string; celular_fuera: boolean | null }) =>
      api.post<RegistroSueno>("/sueno", { fecha, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sueno", fecha] });
    },
  });
}

export function useUpsertBienestar(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      sueno_pobre: number;
      fatiga: number;
      dolor_muscular: number;
      estres: number;
    }) => api.post<RegistroBienestar>("/bienestar", { fecha, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bienestar", fecha] });
    },
  });
}

export function useMarcarHabito(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { habito_id: number; valor: boolean }) =>
      api.post<HabitoRegistro>("/habitos/registro", { fecha, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["habitos", "registro", fecha] });
    },
  });
}

export function useSumarHidratacion(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { cantidad_ml: number }) =>
      api.post<RegistroHidratacion>("/hidratacion", { fecha, ...cuerpo }),
    // El endpoint ya devuelve el total nuevo: no hace falta invalidar y
    // esperar un segundo round-trip para ver el número actualizado.
    onSuccess: (data) => {
      qc.setQueryData(["hidratacion", fecha], data);
    },
  });
}

// ---------- Fase 4: catalogos ----------

export function useTiposSesion() {
  return useQuery({
    queryKey: ["catalogos", "tipos-sesion"],
    queryFn: () => api.get<TipoSesion[]>("/catalogos/tipos-sesion"),
    staleTime: Infinity, // un catalogo sembrado no cambia en una sesion
  });
}

export function useEjercicios() {
  return useQuery({
    queryKey: ["catalogos", "ejercicios"],
    queryFn: () => api.get<Ejercicio[]>("/catalogos/ejercicios"),
    staleTime: Infinity,
  });
}

export function useZonasCorporales() {
  return useQuery({
    queryKey: ["catalogos", "zonas-corporales"],
    queryFn: () => api.get<ZonaCorporal[]>("/catalogos/zonas-corporales"),
    staleTime: Infinity,
  });
}

// ---------- Fase 4: sesiones ----------

export function useSesionesDeFecha(fecha: string) {
  return useQuery({
    queryKey: ["sesiones", fecha],
    queryFn: () => api.get<Sesion[]>(`/sesiones?fecha=${fecha}`),
  });
}

export function useCrearSesion(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      id?: string;
      idempotency_key: string;
      tipo_sesion_id: number;
      duracion_min: number;
      rpe: number;
      nota?: string | null;
      series: Array<{
        ejercicio_id: number;
        orden: number;
        series: number;
        reps: number;
        peso_kg: number | null;
        rpe: number | null;
        dolor_lumbar?: boolean;
      }>;
    }) =>
      api.post<Sesion>("/sesiones", { fecha, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sesiones", fecha] });
    },
  });
}

// ---------- Fase 4: molestias ----------

export function useMolestiasDeFecha(fecha: string) {
  return useQuery({
    queryKey: ["molestias", fecha],
    queryFn: () => api.get<Molestia[]>(`/molestias?fecha=${fecha}`),
  });
}

export function useCrearMolestia(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { zona_id: number; intensidad: number; nota?: string | null }) =>
      api.post<Molestia>("/molestias", { fecha, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["molestias", fecha] });
    },
  });
}

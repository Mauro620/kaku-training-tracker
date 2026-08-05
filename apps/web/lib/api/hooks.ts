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

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";
import { encolar, endpointDesdeApi, procesarCola } from "@/lib/sync/outbox";
import type { EventoOutbox } from "@/lib/sync/outbox";

// ---------- Fase 5: captura offline-first ----------
// Las 6 mutaciones de captura (sueno, bienestar, hidratacion, habito,
// molestia, sesion) escriben primero a la cola local (Dexie, siempre
// instantaneo, nunca falla sin red) y recien devuelven exito: el dato ya
// esta a salvo aunque no haya conexion. El envio real pasa en background;
// cuando termina (typicamente <1s si hay red), recien ahi se invalidan
// las queries para traer el valor autoritativo del server (ej. el total
// de hidratacion, que es una suma que solo el server puede calcular).
function sincronizarYRefrescar(qc: QueryClient, keys: (string | number | null)[][]): void {
  void procesarCola(endpointDesdeApi(api)).then(() => {
    for (const key of keys) void qc.invalidateQueries({ queryKey: key });
  });
}

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

export type TipoMedicion = "carga" | "distancia" | "tiempo" | "tecnica";

export type Ejercicio = {
  id: number;
  nombre: string;
  patron: string | null;
  carga_lumbar: "alta" | "media" | "baja";
  tipo_sesion_id: number | null;
  tipo_medicion: TipoMedicion;
};

export type ZonaCorporal = {
  id: number;
  nombre: string;
};

export type Bloque = {
  id: number;
  sesion_id: string;
  ejercicio_id: number;
  orden: number;
  series: number | null;
  reps: number | null;
  distancia_m: string | null;
  duracion_s: number | null;
  calidad: number | null;
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
  bloques: Bloque[];
};

export type Molestia = {
  id: number;
  usuario_id: string;
  fecha: string;
  zona_id: number;
  intensidad: number;
  nota: string | null;
};

export type BloquePlan = {
  id: number;
  sesion_plan_id: number;
  ejercicio_id: number;
  orden: number;
  series: number | null;
  reps_min: number | null;
  reps_max: number | null;
  peso_objetivo_kg: string | null;
  distancia_objetivo_m: string | null;
  duracion_objetivo_s: number | null;
};

export type SesionPlan = {
  id: number;
  usuario_id: string;
  ciclo_semana_id: number | null;
  fecha_prevista: string | null;
  dia_sugerido: number | null;
  tipo_sesion_id: number;
  objetivo: string | null;
  duracion_min_est: number | null;
  rpe_objetivo: number | null;
  bloques_planeados: BloquePlan[];
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
    mutationFn: async (cuerpo: {
      inicio: string;
      fin: string;
      celular_fuera: boolean | null;
    }) => {
      const evento: EventoOutbox = {
        tipo: "sueno",
        cuerpo: { fecha, ...cuerpo, origen: "manual", idempotency_key: crypto.randomUUID() },
      };
      await encolar(evento);
      sincronizarYRefrescar(qc, [["sueno", fecha]]);
    },
  });
}

export function useUpsertBienestar(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (cuerpo: {
      sueno_pobre: number;
      fatiga: number;
      dolor_muscular: number;
      estres: number;
    }) => {
      const evento: EventoOutbox = {
        tipo: "bienestar",
        cuerpo: { fecha, ...cuerpo, idempotency_key: crypto.randomUUID() },
      };
      await encolar(evento);
      sincronizarYRefrescar(qc, [["bienestar", fecha]]);
    },
  });
}

export function useMarcarHabito(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (cuerpo: { habito_id: number; valor: boolean }) => {
      const evento: EventoOutbox = {
        tipo: "habito_registro",
        cuerpo: { fecha, ...cuerpo, idempotency_key: crypto.randomUUID() },
      };
      await encolar(evento);
      sincronizarYRefrescar(qc, [["habitos", "registro", fecha]]);
    },
  });
}

export function useSumarHidratacion(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (cuerpo: { cantidad_ml: number }) => {
      const evento: EventoOutbox = {
        tipo: "hidratacion",
        cuerpo: { fecha, ...cuerpo, idempotency_key: crypto.randomUUID() },
      };
      await encolar(evento);
      // El total es una suma que solo el server calcula bien: hay que
      // esperar el sync (no hay valor optimista correcto sin red).
      sincronizarYRefrescar(qc, [["hidratacion", fecha]]);
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

// Unico catalogo que el usuario amplia (REGLAS_NEGOCIO §15): el universo
// de ejercicios de una rutina real es abierto.
export function useCrearEjercicio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { nombre: string; tipo_medicion: TipoMedicion }) =>
      api.post<Ejercicio>("/catalogos/ejercicios", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["catalogos", "ejercicios"] });
    },
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

export type BloqueBorradorPayload = {
  ejercicio_id: number;
  orden: number;
  series?: number | null;
  reps?: number | null;
  distancia_m?: number | null;
  duracion_s?: number | null;
  calidad?: number | null;
  peso_kg?: number | null;
  rpe?: number | null;
  dolor_lumbar?: boolean;
};

export function useCrearSesion(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (cuerpo: {
      id?: string;
      idempotency_key: string;
      sesion_plan_id?: number | null;
      tipo_sesion_id: number;
      duracion_min: number;
      rpe: number;
      nota?: string | null;
      bloques: BloqueBorradorPayload[];
    }) => {
      const { bloques, ...cabecera } = cuerpo;
      const evento: EventoOutbox = {
        tipo: "sesion",
        cuerpo: {
          sesion: {
            id: cabecera.id ?? crypto.randomUUID(),
            idempotency_key: cabecera.idempotency_key,
            sesion_plan_id: cabecera.sesion_plan_id ?? null,
            fecha,
            tipo_sesion_id: cabecera.tipo_sesion_id,
            duracion_min: cabecera.duracion_min,
            rpe: cabecera.rpe,
            nota: cabecera.nota ?? null,
          },
          bloques: bloques.map((b) => ({
            ejercicio_id: b.ejercicio_id,
            orden: b.orden,
            series: b.series ?? null,
            reps: b.reps ?? null,
            distancia_m: b.distancia_m ?? null,
            duracion_s: b.duracion_s ?? null,
            calidad: b.calidad ?? null,
            peso_kg: b.peso_kg ?? null,
            rpe: b.rpe ?? null,
            dolor_lumbar: b.dolor_lumbar ?? false,
          })),
        },
      };
      await encolar(evento);
      // Una sesion vinculada a un plan lo saca de "pendiente".
      sincronizarYRefrescar(qc, [["sesiones", fecha], ["planes", fecha]]);
    },
  });
}

export function useSesion(id: string | null) {
  return useQuery({
    queryKey: ["sesion", id],
    queryFn: () => api.get<Sesion>(`/sesiones/${id}`),
    enabled: id !== null,
  });
}

export type SesionActualizarPayload = {
  fecha: string;
  tipo_sesion_id: number;
  duracion_min: number;
  rpe: number;
  nota?: string | null;
  bloques: BloqueBorradorPayload[];
};

export function useActualizarSesion(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: SesionActualizarPayload) =>
      api.put<Sesion>(`/sesiones/${id}`, cuerpo),
    onSuccess: (data) => {
      qc.setQueryData(["sesion", id], data);
      // La fecha pudo cambiar: invalido cualquier lista de sesiones por
      // fecha, no solo la de hoy.
      void qc.invalidateQueries({ queryKey: ["sesiones"] });
      void qc.invalidateQueries({ queryKey: ["planes"] });
    },
  });
}

export function useEliminarSesion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/sesiones/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sesiones"] });
      void qc.invalidateQueries({ queryKey: ["planes"] });
    },
  });
}

// Duplicar: crea una sesion nueva (id/idempotency_key propios) copiando
// bloques a otra fecha. Sin hook de "fecha fija" como useCrearSesion
// porque el destino puede ser cualquier dia, no el de la pantalla actual.
export function useDuplicarSesion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      id: string;
      idempotency_key: string;
      fecha: string;
      tipo_sesion_id: number;
      duracion_min: number;
      rpe: number;
      nota?: string | null;
      bloques: BloqueBorradorPayload[];
    }) => api.post<Sesion>("/sesiones", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sesiones"] });
      void qc.invalidateQueries({ queryKey: ["planes"] });
    },
  });
}

// ---------- Fase 4 R2: planes ----------

export function usePlanesDeFecha(fecha: string) {
  return useQuery({
    queryKey: ["planes", fecha],
    queryFn: () => api.get<SesionPlan[]>(`/planes?fecha=${fecha}`),
  });
}

// ---------- Fase 4 R3a: ciclo, semana, composicion, cumplimiento ----------

export type Ciclo = {
  id: number;
  usuario_id: string;
  numero: number;
  objetivo: string;
  fecha_inicio: string;
  semanas: number;
  estado: "planificado" | "activo" | "cerrado";
  fecha_fin_prevista: string;
  fecha_cierre_real: string | null;
};

export type CicloSemana = {
  id: number;
  ciclo_id: number;
  numero: number;
  fase: "readaptacion" | "carga" | "descarga";
  rpe_objetivo_min: number | null;
  rpe_objetivo_max: number | null;
  volumen_pct: number;
};

export type ComposicionItem = {
  tipo_sesion_id: number;
  cantidad_objetivo: number;
};

export type CumplimientoItem = {
  tipo_sesion_id: number;
  tipo_sesion_codigo: string;
  tipo_sesion_nombre: string;
  objetivo: number;
  hecho: number;
  cumplido: boolean;
};

export function useCiclos() {
  return useQuery({
    queryKey: ["ciclos"],
    queryFn: () => api.get<Ciclo[]>("/ciclos"),
  });
}

export function useCiclo(id: number | null) {
  return useQuery({
    queryKey: ["ciclo", id],
    queryFn: () => api.get<Ciclo>(`/ciclos/${id}`),
    enabled: id !== null,
  });
}

export function useCrearCiclo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      numero: number;
      objetivo: string;
      fecha_inicio: string;
      semanas: number;
    }) => api.post<Ciclo>("/ciclos", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ciclos"] });
    },
  });
}

export function useCerrarCiclo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, fecha_cierre_real }: { id: number; fecha_cierre_real?: string }) =>
      api.post<Ciclo>(`/ciclos/${id}/cerrar`, { fecha_cierre_real }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ciclos"] });
      void qc.invalidateQueries({ queryKey: ["ciclo"] });
    },
  });
}

export function useSemanas(cicloId: number | null) {
  return useQuery({
    queryKey: ["ciclo", cicloId, "semanas"],
    queryFn: () => api.get<CicloSemana[]>(`/ciclos/${cicloId}/semanas`),
    enabled: cicloId !== null,
  });
}

export function useCrearSemana(cicloId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      numero: number;
      fase: "readaptacion" | "carga" | "descarga";
      rpe_objetivo_min: number | null;
      rpe_objetivo_max: number | null;
      volumen_pct: number;
    }) => api.post<CicloSemana>(`/ciclos/${cicloId}/semanas`, cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ciclo", cicloId, "semanas"] });
    },
  });
}

export function useActualizarSemana(cicloId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...cuerpo
    }: {
      id: number;
      fase: "readaptacion" | "carga" | "descarga";
      rpe_objetivo_min: number | null;
      rpe_objetivo_max: number | null;
      volumen_pct: number;
    }) => api.put<CicloSemana>(`/ciclos/semanas/${id}`, cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ciclo", cicloId, "semanas"] });
    },
  });
}

export function useEliminarSemana(cicloId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/ciclos/semanas/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["ciclo", cicloId, "semanas"] });
    },
  });
}

export function useComposicion(semanaId: number | null) {
  return useQuery({
    queryKey: ["semana", semanaId, "composicion"],
    queryFn: () => api.get<ComposicionItem[]>(`/ciclos/semanas/${semanaId}/composicion`),
    enabled: semanaId !== null,
  });
}

export function useReemplazarComposicion(semanaId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: ComposicionItem[]) =>
      api.put<ComposicionItem[]>(`/ciclos/semanas/${semanaId}/composicion`, { items }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["semana", semanaId, "composicion"] });
    },
  });
}

export function useCumplimiento(semanaId: number | null) {
  return useQuery({
    queryKey: ["semana", semanaId, "cumplimiento"],
    queryFn: () => api.get<CumplimientoItem[]>(`/ciclos/semanas/${semanaId}/cumplimiento`),
    enabled: semanaId !== null,
  });
}

export function usePlanesDeSemana(semanaId: number | null) {
  return useQuery({
    queryKey: ["semana", semanaId, "planes"],
    queryFn: () => api.get<SesionPlan[]>(`/ciclos/semanas/${semanaId}/planes`),
    enabled: semanaId !== null,
  });
}

export type BloquePlanCreatePayload = {
  ejercicio_id: number;
  orden: number;
  series: number | null;
  reps_min: number | null;
  reps_max: number | null;
  peso_objetivo_kg: number | null;
  distancia_objetivo_m: number | null;
  duracion_objetivo_s: number | null;
};

export function useCrearPlan(semanaId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      dia_sugerido: number | null;
      tipo_sesion_id: number;
      objetivo: string | null;
      duracion_min_est: number | null;
      rpe_objetivo: number | null;
      bloques: BloquePlanCreatePayload[];
    }) =>
      api.post<SesionPlan>("/planes", { ciclo_semana_id: semanaId, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["semana", semanaId, "planes"] });
      void qc.invalidateQueries({ queryKey: ["planes"] });
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
    mutationFn: async (cuerpo: {
      zona_id: number;
      intensidad: number;
      nota?: string | null;
    }) => {
      const evento: EventoOutbox = {
        tipo: "molestia",
        cuerpo: {
          fecha,
          zona_id: cuerpo.zona_id,
          intensidad: cuerpo.intensidad,
          nota: cuerpo.nota ?? null,
          idempotency_key: crypto.randomUUID(),
        },
      };
      await encolar(evento);
      sincronizarYRefrescar(qc, [["molestias", fecha]]);
    },
  });
}

export function useEliminarMolestia(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/molestias/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["molestias", fecha] });
    },
  });
}

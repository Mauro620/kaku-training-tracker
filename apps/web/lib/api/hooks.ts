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
    // C: la grilla de cumplimiento semanal depende de todas las
    // dimensiones; refresca cuando cualquier captura cambie.
    void qc.invalidateQueries({ queryKey: ["cierre-semana"] });
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

// ---------- C: cumplimiento semanal (cerrar semana) ----------

export type CierreSuenoDia = {
  horas: string | null;
  objetivo_h: string;
};

export type CierreSesionDia = {
  registrada: boolean;
};

export type CierreHidratacionDia = {
  ml_totales: number | null;
  objetivo_ml: number;
};

export type CierreHabitosDia = {
  marcados: number;
  activos: number;
};

export type CierreBienestarDia = {
  registrado: boolean;
};

export type CierreDia = {
  fecha: string;
  sueno: CierreSuenoDia;
  sesion: CierreSesionDia;
  hidratacion: CierreHidratacionDia;
  habitos: CierreHabitosDia;
  bienestar: CierreBienestarDia;
};

export type CierreSemana = {
  dias: CierreDia[];
};

/** Devuelve la data cruda por dia de las 5 dimensiones. La UI
 * calcula los flags cumplidos/incumplidos con los thresholds que
 * prefiera (>= objetivo, >= 80% del objetivo, etc.). Por ahora la
 * regla es >= objetivo. */
export function useCierreSemana(desde: string, hasta: string) {
  return useQuery({
    queryKey: ["cierre-semana", desde, hasta],
    queryFn: () =>
      api.get<CierreSemana>(
        `/semana?desde=${desde}&hasta=${hasta}`,
      ),
    staleTime: 60 * 1000,
  });
}

// H3 de la revision de UI: historial de 14 dias para la grilla y la
// deuda 7d. staleTime corto: la UI lo invalida al guardar un sueno nuevo
// (ver useUpsertSueno.onSuccess abajo), no recachea en cada navegacion.
export function useSuenoUltimosNDias(dias: number) {
  return useQuery({
    queryKey: ["sueno", "ultimos", dias],
    queryFn: () => api.get<RegistroSueno[]>(`/sueno/ultimos?dias=${dias}`),
    staleTime: 5 * 60 * 1000,
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

// ---------- D4: CRUD de habitos en Ajustes ----------
// QueryKey distinta de ["habitos"] (que devuelve solo los activos).
// Ajustes necesita ver archivados para permitir "desarchivar" y
// mostrar el historial.

export function useHabitosAjustes() {
  const qc = useQueryClient();
  const listar = useQuery({
    queryKey: ["habitos", "all"],
    queryFn: () => api.get<Habito[]>("/habitos/all"),
  });

  const crear = useMutation({
    mutationFn: (cuerpo: { nombre: string }) =>
      api.post<Habito>("/habitos", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["habitos"] });
      void qc.invalidateQueries({ queryKey: ["habitos", "all"] });
    },
  });

  const actualizar = useMutation({
    mutationFn: (args: { id: number; cuerpo: { nombre?: string; activo?: boolean; orden?: number } }) =>
      api.patch<Habito>(`/habitos/${args.id}`, args.cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["habitos"] });
      void qc.invalidateQueries({ queryKey: ["habitos", "all"] });
    },
  });

  const reordenar = useMutation({
    mutationFn: (ids: number[]) =>
      api.put<void>("/habitos/reordenar", { ids }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["habitos"] });
      void qc.invalidateQueries({ queryKey: ["habitos", "all"] });
    },
  });

  function obtenerError(err: unknown): string | null {
    if (!err) return null;
    if (err instanceof ApiError) return err.message;
    if (err instanceof Error) return err.message;
    return "Error desconocido";
  }

  return {
    habitos: listar.data ?? [],
    cargando: listar.isLoading,
    error: obtenerError(listar.error),
    crear: (nombre: string) => crear.mutateAsync({ nombre }),
    actualizar: (id: number, cuerpo: { nombre?: string; activo?: boolean; orden?: number }) =>
      actualizar.mutateAsync({ id, cuerpo }),
    archivar: (id: number) => actualizar.mutateAsync({ id, cuerpo: { activo: false } }),
    reordenar: (id: number, dir: "arriba" | "abajo", lista: Habito[]) => {
      const idx = lista.findIndex((h) => h.id === id);
      if (idx === -1) return Promise.resolve();
      const objetivo = dir === "arriba" ? idx - 1 : idx + 1;
      if (objetivo < 0 || objetivo >= lista.length) return Promise.resolve();
      // Swap y persistir el orden completo.
      const nueva = [...lista];
      const a = nueva[idx];
      const b = nueva[objetivo];
      if (!a || !b) return Promise.resolve();
      nueva[idx] = b;
      nueva[objetivo] = a;
      return reordenar.mutateAsync(nueva.map((h) => h.id));
    },
  };
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
      // Tambien invalida la lista de N dias: la grilla del historial y la
      // deuda 7d dependen de este row.
      void qc.invalidateQueries({ queryKey: ["sueno", "ultimos"] });
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

// ---------- Fase 6: nutricion ----------

export type GrupoAlimento =
  | "proteina_animal"
  | "lacteo"
  | "cereal"
  | "leguminosa"
  | "tuberculo"
  | "verdura"
  | "fruta"
  | "grasa"
  | "procesado";

export type EstadoPesaje = "crudo" | "cocido";

export type Alimento = {
  id: number;
  nombre: string;
  grupo: GrupoAlimento;
  estado_pesaje: EstadoPesaje;
  kcal_100g: string;
  proteina_100g: string;
  carbo_100g: string;
  grasa_100g: string;
  fibra_100g: string | null;
  fuente: string | null;
};

export type MomentoComida =
  | "desayuno"
  | "media_manana"
  | "almuerzo"
  | "merienda"
  | "cena";

export type RecetaItem = {
  id: number;
  alimento_id: number;
  cantidad_g: string;
};

export type Receta = {
  id: number;
  nombre: string;
  momento_default: MomentoComida | null;
  activa: boolean;
  items: RecetaItem[];
};

export type MacroTotal = {
  kcal: string;
  proteina: string;
  carbo: string;
  grasa: string;
  fibra: string;
};

export type ComidaItem = {
  id: number;
  alimento_id: number;
  cantidad_g: string;
};

export type Comida = {
  id: string;
  fecha: string;
  momento: MomentoComida;
  receta_id: number | null;
  nota: string | null;
  idempotency_key: string;
  items: ComidaItem[];
};

export type ComidaConMacros = Comida & { macros: MacroTotal };

export type ComidasDelDia = {
  comidas: Comida[];
  macros_del_dia: MacroTotal;
};

export type DespensaItem = {
  alimento_id: number;
  alimento_nombre: string;
  imprescindible: boolean;
  en_stock: boolean;
};

// Catalogo sembrado: staleTime infinito.
export function useAlimentos() {
  return useQuery({
    queryKey: ["alimentos"],
    queryFn: () => api.get<Alimento[]>("/alimentos"),
    staleTime: Infinity,
  });
}

// Recetas del usuario. staleTime corto (5 min): cuando agrega/edita una,
// invalida la query; mientras tanto, no refetchea en cada navegacion.
export function useRecetas() {
  return useQuery({
    queryKey: ["recetas"],
    queryFn: () => api.get<Receta[]>("/recetas"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useReceta(id: number | null) {
  return useQuery({
    queryKey: ["receta", id],
    queryFn: () => api.get<Receta>(`/recetas/${id}`),
    enabled: id !== null,
  });
}

export function useMacrosDeReceta(id: number | null) {
  return useQuery({
    queryKey: ["receta", id, "macros"],
    queryFn: () => api.get<MacroTotal>(`/recetas/${id}/macros`),
    enabled: id !== null,
  });
}

// El POST de comida SI va a la cola (es el registro diario del usuario,
// offline-first). El resto de mutaciones de nutricion (CRUD receta,
// upsert despensa, eliminar) NO: son setup con red.
export function useRegistrarComida(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (cuerpo: {
      momento: MomentoComida;
      receta_id: number | null;
      nota?: string | null;
      items?: { alimento_id: number; cantidad_g: number }[];
    }) => {
      const evento: EventoOutbox = {
        tipo: "comida",
        cuerpo: {
          fecha,
          momento: cuerpo.momento,
          receta_id: cuerpo.receta_id,
          nota: cuerpo.nota ?? null,
          items: cuerpo.items ?? [],
          idempotency_key: crypto.randomUUID(),
        },
      };
      await encolar(evento);
      sincronizarYRefrescar(qc, [["comidas", fecha]]);
    },
  });
}

export function useEliminarComida(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/comidas/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["comidas", fecha] });
    },
  });
}

export function useCrearReceta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      nombre: string;
      momento_default: MomentoComida | null;
      items: { alimento_id: number; cantidad_g: number }[];
    }) => api.post<Receta>("/recetas", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["recetas"] });
    },
  });
}

export function useActualizarReceta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...cuerpo
    }: {
      id: number;
      nombre: string;
      momento_default: MomentoComida | null;
      items: { alimento_id: number; cantidad_g: number }[];
    }) => api.put<Receta>(`/recetas/${id}`, cuerpo),
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["recetas"] });
      void qc.invalidateQueries({ queryKey: ["receta", variables.id] });
    },
  });
}

export function useEliminarReceta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/recetas/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["recetas"] });
    },
  });
}

export function useComidasDelDia(fecha: string) {
  return useQuery({
    queryKey: ["comidas", fecha],
    queryFn: () => api.get<ComidasDelDia>(`/comidas?fecha=${fecha}`),
  });
}

export function useComida(id: string | null) {
  return useQuery({
    queryKey: ["comida", id],
    queryFn: () => api.get<ComidaConMacros>(`/comidas/${id}`),
    enabled: id !== null,
  });
}

export function useDespensa() {
  return useQuery({
    queryKey: ["despensa"],
    queryFn: () => api.get<DespensaItem[]>("/despensa"),
  });
}

export function useListaDeMercado() {
  return useQuery({
    queryKey: ["despensa", "lista-de-mercado"],
    queryFn: () =>
      api.get<{ items: DespensaItem[] }>("/despensa/lista-de-mercado"),
  });
}

export function useUpsertDespensa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      alimento_id,
      ...cuerpo
    }: {
      alimento_id: number;
      imprescindible: boolean;
      en_stock: boolean;
    }) =>
      api.put<void>(`/despensa/${alimento_id}`, cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["despensa"] });
    },
  });
}

export function useEliminarDeDespensa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alimento_id: number) =>
      api.delete<void>(`/despensa/${alimento_id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["despensa"] });
    },
  });
}

// ---------- Fase 7: tests fisicos, medida corporal, partidos ----------

export type TipoTest = {
  id: number;
  codigo: string;
  nombre: string;
  unidad: string;
  mejor_es_mayor: boolean;
};

export type TestIntento = {
  numero: number;
  valor: string;
};

export type TestFisico = {
  id: string;
  usuario_id: string;
  fecha: string;
  tipo_test_id: number;
  superficie: string | null;
  condiciones: string | null;
  intentos: TestIntento[];
};

export type ResultadoTest = {
  mejor: string;
  media: string;
  pct_decremento: string | null;
  pct_cambio: string | null;
};

export type MedidaCorporal = {
  id: number;
  usuario_id: string;
  fecha: string;
  peso_kg: string;
  fc_reposo: number | null;
  origen: "manual" | "health_kit" | "notion_backfill";
};

export type Partido = {
  id: string;
  sesion_id: string;
  rival: string | null;
  formato: string | null;
  minutos_jugados: number;
  goles: number;
  asistencias: number;
  recuperaciones: number | null;
  salio_bien: string | null;
  a_ajustar: string | null;
};

export function useTiposTest() {
  return useQuery({
    queryKey: ["catalogos", "tipos-test"],
    queryFn: () => api.get<TipoTest[]>("/catalogos/tipos-test"),
    staleTime: Infinity, // un catalogo sembrado no cambia en una sesion
  });
}

export function useTestsDeFecha(fecha: string) {
  return useQuery({
    queryKey: ["tests", fecha],
    queryFn: () => api.get<TestFisico[]>(`/tests?fecha=${fecha}`),
  });
}

export function useTest(id: string | null) {
  return useQuery({
    queryKey: ["test", id],
    queryFn: () => api.get<TestFisico>(`/tests/${id}`),
    enabled: id !== null,
  });
}

export function useResultadoTest(id: string | null) {
  return useQuery({
    queryKey: ["test", id, "resultado"],
    queryFn: () => api.get<ResultadoTest>(`/tests/${id}/resultado`),
    enabled: id !== null,
  });
}

export function useRegistrarTest(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      idempotency_key: string;
      tipo_test_id: number;
      superficie?: string | null;
      condiciones?: string | null;
      valores: string[];
    }) => api.post<TestFisico>("/tests", { fecha, ...cuerpo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["tests", fecha] });
    },
  });
}

export function useEliminarTest(fecha: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/tests/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["tests", fecha] });
    },
  });
}

export function useMedidas() {
  return useQuery({
    queryKey: ["medidas"],
    queryFn: () => api.get<MedidaCorporal[]>("/medidas"),
  });
}

export function useRegistrarMedida() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { fecha: string; peso_kg: string; fc_reposo?: number | null }) =>
      api.post<MedidaCorporal>("/medidas", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["medidas"] });
    },
  });
}

export function usePartidos() {
  return useQuery({
    queryKey: ["partidos"],
    queryFn: () => api.get<Partido[]>("/partidos"),
  });
}

export function usePartido(id: string | null) {
  return useQuery({
    queryKey: ["partido", id],
    queryFn: () => api.get<Partido>(`/partidos/${id}`),
    enabled: id !== null,
  });
}

export function useRegistrarPartido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: {
      sesion_id: string;
      rival?: string | null;
      formato?: string | null;
      minutos_jugados: number;
      goles?: number;
      asistencias?: number;
      recuperaciones?: number | null;
      salio_bien?: string | null;
      a_ajustar?: string | null;
    }) => api.post<Partido>("/partidos", cuerpo),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["partidos"] });
    },
  });
}

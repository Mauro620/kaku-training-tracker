"use client";

import { useState } from "react";
import { ChevronDown, Copy, Minus, Plus, Search, Trash2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useCrearEjercicio,
  useCrearSesion,
  useEjercicios,
  useSesionesDeFecha,
  useTiposSesion,
  type BloqueBorradorPayload,
  type Ejercicio,
  type SesionPlan,
  type TipoMedicion,
  type TipoSesion,
} from "@/lib/api/hooks";

type Props = { fecha: string; planes: SesionPlan[] };

type BloqueBorrador = {
  // Identificador local para key de React. No se manda al backend.
  localId: number;
  ejercicio_id: number | null;
  series: number | null;
  reps: number | null;
  distancia_m: number | null;
  duracion_s: number | null;
  calidad: number | null;
  peso_kg: number | null;
  rpe: number | null;
  dolor_lumbar: boolean;
};

const BLOQUE_VACIO: Omit<BloqueBorrador, "localId"> = {
  ejercicio_id: null,
  series: null,
  reps: null,
  distancia_m: null,
  duracion_s: null,
  calidad: null,
  peso_kg: null,
  rpe: null,
  dolor_lumbar: false,
};

function uid(): number {
  return Math.floor(Math.random() * 1e9);
}

const NOMBRE_MEDICION: Record<TipoMedicion, string> = {
  carga: "Carga (series/reps/kg)",
  distancia: "Distancia (reps/metros)",
  tiempo: "Tiempo (segundos)",
  tecnica: "Tecnica (reps o segundos + calidad)",
};

function bloqueInvalido(b: BloqueBorrador): boolean {
  if (b.ejercicio_id === null) return true;
  const numValido = (v: number | null, min: number) =>
    v === null || (Number.isFinite(v) && v > min);
  if (!numValido(b.series, 0)) return true;
  if (!numValido(b.reps, 0)) return true;
  if (!numValido(b.distancia_m, 0)) return true;
  if (!numValido(b.duracion_s, 0)) return true;
  if (b.calidad !== null && (!Number.isFinite(b.calidad) || b.calidad < 1 || b.calidad > 5)) {
    return true;
  }
  if (b.peso_kg !== null && (!Number.isFinite(b.peso_kg) || b.peso_kg < 0)) return true;
  if (b.rpe !== null && (!Number.isFinite(b.rpe) || b.rpe < 1 || b.rpe > 10)) return true;
  return false;
}

/**
 * Form de sesion (Fase 4, ROADMAP §4).
 * Un unico paso visible: tipo, duracion, RPE, nota, y N bloques editables.
 * Que campos acepta cada bloque lo decide el tipo_medicion del ejercicio
 * elegido (REGLAS_NEGOCIO §15), no el tipo de sesion: tecnica/distancia/
 * tiempo tienen bloques igual que fuerza, solo que miden otra cosa.
 * El cliente genera `id` y `idempotency_key` (uuid v4) para que el backend
 * pueda detectar reintentos idempotentes (Fase 5 offline-first).
 */
export function SesionForm({ fecha, planes }: Props) {
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const sesionesDeHoy = useSesionesDeFecha(fecha);
  const crear = useCrearSesion(fecha);

  const [tipoSesionId, setTipoSesionId] = useState<number | null>(null);
  const [tipoExpandido, setTipoExpandido] = useState(false);
  const [duracionMin, setDuracionMin] = useState<number>(60);
  const [rpe, setRpe] = useState<number>(7);
  const [nota, setNota] = useState("");
  const [bloques, setBloques] = useState<BloqueBorrador[]>([]);

  const tipoSeleccionado = tipos.data?.find((t) => t.id === tipoSesionId) ?? null;

  // Un plan ya cumplido (tiene una sesion real que lo referencia) no se
  // vuelve a ofrecer: linkearlo dos veces confundiria el delta.
  const idsPlanesCumplidos = new Set(
    (sesionesDeHoy.data ?? [])
      .map((s) => s.sesion_plan_id)
      .filter((id): id is number => id !== null),
  );
  const planesPendientes = planes.filter((p) => !idsPlanesCumplidos.has(p.id));
  const planVinculado =
    planesPendientes.find((p) => p.tipo_sesion_id === tipoSesionId) ?? null;

  const cargaEstimada = rpe * duracionMin;

  function agregarBloque() {
    setBloques((s) => [...s, { localId: uid(), ...BLOQUE_VACIO }]);
  }

  function duplicarBloque(localId: number) {
    setBloques((s) => {
      const original = s.find((b) => b.localId === localId);
      if (!original) return s;
      return [...s, { ...original, localId: uid() }];
    });
  }

  function eliminarBloque(localId: number) {
    setBloques((s) => s.filter((x) => x.localId !== localId));
  }

  function actualizarBloque(localId: number, cambio: Partial<BloqueBorrador>) {
    setBloques((s) => s.map((x) => (x.localId === localId ? { ...x, ...cambio } : x)));
  }

  function elegirTipo(id: number) {
    setTipoSesionId(id);
    setTipoExpandido(false);
  }

  const puedeGuardar = tipoSesionId !== null && !bloques.some(bloqueInvalido);

  return (
    <BentoCard>
      <header className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Nueva sesion
        </p>
        {bloques.length > 0 && (
          <span className="text-[11px] text-text-secondary">
            {bloques.length} bloque{bloques.length === 1 ? "" : "s"}
          </span>
        )}
      </header>

      {/* Plan de hoy: solo antes de elegir tipo, para no competir con el
          selector una vez que ya se sabe que se esta registrando. */}
      {!tipoSesionId && planesPendientes.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          <p className="text-[11px] uppercase tracking-widest text-text-secondary">
            Plan de hoy
          </p>
          {planesPendientes.map((p) => {
            const nombre = tipos.data?.find((t) => t.id === p.tipo_sesion_id)?.nombre;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => elegirTipo(p.tipo_sesion_id)}
                className="flex items-center justify-between rounded-bento border border-border-subtle bg-surface-secondary px-4 py-2.5 text-left"
              >
                <span className="text-[14px] font-medium text-text-primary">
                  {nombre ?? "Sesion"}
                </span>
                <span className="text-[12px] text-text-secondary">
                  {[
                    p.rpe_objetivo && `RPE ${p.rpe_objetivo}`,
                    p.duracion_min_est && `${p.duracion_min_est} min`,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Tipo de sesion: colapsado muestra solo el elegido, se expande al tocar. */}
      <p className="mb-2 text-[13px] text-text-secondary">Tipo</p>
      {tipoExpandido ? (
        <div className="flex flex-wrap gap-2">
          {tipos.data?.map((t: TipoSesion) => (
            <BotonTipo
              key={t.id}
              tipo={t}
              activo={tipoSesionId === t.id}
              onClick={() => elegirTipo(t.id)}
            />
          ))}
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setTipoExpandido(true)}
          className="flex min-h-[40px] w-full items-center justify-between rounded-pill bg-surface-secondary px-4 text-[13px] text-text-primary"
        >
          {tipoSeleccionado?.nombre ?? "Elegir tipo…"}
          <ChevronDown size={16} className="text-text-secondary" />
        </button>
      )}
      {planVinculado && (
        <p className="mt-1.5 text-[11px] text-text-secondary">
          Vinculada al plan de hoy
          {planVinculado.rpe_objetivo ? ` · RPE objetivo ${planVinculado.rpe_objetivo}` : ""}
          {planVinculado.duracion_min_est ? ` · ${planVinculado.duracion_min_est} min` : ""}
        </p>
      )}

      {/* Duracion, RPE, nota */}
      <div className="mt-5 grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">
            Duracion
          </span>
          <div className="flex items-center bg-surface-secondary rounded-pill">
            <button
              type="button"
              onClick={() => setDuracionMin((d) => Math.max(1, d - 5))}
              className="p-2 text-text-secondary"
              aria-label="Restar 5 minutos"
            >
              <Minus size={16} />
            </button>
            <input
              type="number"
              min={1}
              value={duracionMin}
              // Sin clamp en el onChange: clamp en el onChange pisa el valor
              // mientras el usuario esta editando. El min/max del HTML ya
              // limita el browser, y el backend valida si pasa.
              onChange={(e) =>
                setDuracionMin(e.target.value === "" ? 0 : Number(e.target.value))
              }
              className="w-full bg-transparent text-center text-[16px] font-bold tabular text-text-primary outline-none"
            />
            <span className="px-2 text-[11px] text-text-secondary">min</span>
            <button
              type="button"
              onClick={() => setDuracionMin((d) => d + 5)}
              className="p-2 text-text-secondary"
              aria-label="Sumar 5 minutos"
            >
              <Plus size={16} />
            </button>
          </div>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">RPE</span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpe}
            onChange={(e) => setRpe(Number(e.target.value))}
            className="bg-surface-secondary rounded-pill px-4 py-2 text-center text-[16px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>

      <p className="mt-3 text-center text-[36px] font-bold leading-none tabular text-text-primary">
        {cargaEstimada}
        <span className="ml-2 text-base font-medium text-text-secondary">carga sRPE</span>
      </p>

      <label className="mt-4 flex flex-col gap-1">
        <span className="text-[11px] uppercase tracking-widest text-text-secondary">Nota</span>
        <input
          type="text"
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="opcional"
          className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
        />
      </label>

      {/* Bloques: cualquier tipo de sesion puede tenerlos. Que campos pide
          cada uno lo decide el tipo_medicion del ejercicio elegido. */}
      <div className="mt-6 flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">Bloques</p>
        <button
          type="button"
          onClick={agregarBloque}
          className="flex items-center gap-1 rounded-pill bg-surface-secondary px-4 py-1.5 text-[13px] font-medium text-text-primary"
        >
          <Plus size={14} /> Agregar
        </button>
      </div>

      <div className="mt-3 flex flex-col gap-2">
        {bloques.map((b, idx) => (
          <BloqueBorradorCard
            key={b.localId}
            bloque={b}
            orden={idx + 1}
            ejercicios={ejercicios.data ?? []}
            onChange={(c) => actualizarBloque(b.localId, c)}
            onEliminar={() => eliminarBloque(b.localId)}
            onDuplicar={() => duplicarBloque(b.localId)}
          />
        ))}
      </div>

      <button
        type="button"
        disabled={!puedeGuardar || crear.isPending}
        onClick={async () => {
          if (!tipoSesionId) return;
          const bloquesPayload: BloqueBorradorPayload[] = bloques.map((b, idx) => ({
            ejercicio_id: b.ejercicio_id!,
            orden: idx,
            series: b.series,
            reps: b.reps,
            distancia_m: b.distancia_m,
            duracion_s: b.duracion_s,
            calidad: b.calidad,
            peso_kg: b.peso_kg,
            rpe: b.rpe,
            dolor_lumbar: b.dolor_lumbar,
          }));
          await crear.mutateAsync({
            // crypto.randomUUID requiere contexto seguro (https o localhost).
            // El dev server corre en localhost asi que funciona.
            id: crypto.randomUUID(),
            idempotency_key: crypto.randomUUID(),
            sesion_plan_id: planVinculado?.id ?? null,
            tipo_sesion_id: tipoSesionId,
            duracion_min: duracionMin,
            rpe,
            nota: nota || null,
            bloques: bloquesPayload,
          });
          // Reset del form
          setBloques([]);
          setNota("");
        }}
        className="mt-6 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
      >
        {crear.isPending ? "Guardando..." : "Guardar sesion"}
      </button>
    </BentoCard>
  );
}

// ---------- Sub-componentes ----------

function BotonTipo({
  tipo,
  activo,
  onClick,
}: {
  tipo: TipoSesion;
  activo: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={activo}
      className={`min-h-[40px] px-4 rounded-pill text-[13px] ${
        activo
          ? "bg-text-primary text-canvas"
          : "bg-surface-secondary text-text-secondary"
      }`}
    >
      {tipo.nombre}
    </button>
  );
}

function BloqueBorradorCard({
  bloque,
  orden,
  ejercicios,
  onChange,
  onEliminar,
  onDuplicar,
}: {
  bloque: BloqueBorrador;
  orden: number;
  ejercicios: Ejercicio[];
  onChange: (c: Partial<BloqueBorrador>) => void;
  onEliminar: () => void;
  onDuplicar: () => void;
}) {
  const ejercicio = ejercicios.find((e) => e.id === bloque.ejercicio_id) ?? null;

  return (
    <div className="rounded-bento border border-border-subtle bg-surface-secondary p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Bloque {orden}
        </p>
        <div className="flex items-center gap-1">
          {bloque.ejercicio_id !== null && (
            <button
              type="button"
              onClick={onDuplicar}
              aria-label="Duplicar bloque"
              className="p-1 text-text-secondary"
            >
              <Copy size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={onEliminar}
            aria-label="Eliminar bloque"
            className="p-1 text-text-secondary"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="mt-2">
        <EjercicioPicker
          ejercicioId={bloque.ejercicio_id}
          ejercicios={ejercicios}
          onElegir={(id) => onChange({ ejercicio_id: id })}
        />
      </div>

      {ejercicio && (
        <>
          <CamposBloque bloque={bloque} tipoMedicion={ejercicio.tipo_medicion} onChange={onChange} />

          <label className="mt-2 flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={bloque.dolor_lumbar}
              onChange={(e) => onChange({ dolor_lumbar: e.target.checked })}
              className="h-4 w-4 accent-text-primary"
            />
            <span className="text-[12px] text-text-secondary">Dolor lumbar</span>
          </label>
        </>
      )}
    </div>
  );
}

function CampoNumero({
  etiqueta,
  valor,
  min,
  max,
  step,
  onChange,
}: {
  etiqueta: string;
  valor: number | null;
  min?: number;
  max?: number;
  step?: number;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-widest text-text-secondary">
        {etiqueta}
      </span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
      />
    </label>
  );
}

// Que campos se muestran lo decide el tipo_medicion del ejercicio elegido
// (REGLAS_NEGOCIO §15), no el tipo de sesion. rpe siempre esta disponible.
function CamposBloque({
  bloque,
  tipoMedicion,
  onChange,
}: {
  bloque: BloqueBorrador;
  tipoMedicion: TipoMedicion;
  onChange: (c: Partial<BloqueBorrador>) => void;
}) {
  return (
    <div className="mt-2 grid grid-cols-4 gap-2">
      {tipoMedicion === "carga" && (
        <>
          <CampoNumero
            etiqueta="Sets"
            valor={bloque.series}
            min={1}
            onChange={(v) => onChange({ series: v })}
          />
          <CampoNumero
            etiqueta="Reps"
            valor={bloque.reps}
            min={1}
            onChange={(v) => onChange({ reps: v })}
          />
          <CampoNumero
            etiqueta="Kg"
            valor={bloque.peso_kg}
            min={0}
            step={0.5}
            onChange={(v) => onChange({ peso_kg: v })}
          />
        </>
      )}
      {tipoMedicion === "distancia" && (
        <>
          <CampoNumero
            etiqueta="Reps"
            valor={bloque.reps}
            min={1}
            onChange={(v) => onChange({ reps: v })}
          />
          <CampoNumero
            etiqueta="Metros"
            valor={bloque.distancia_m}
            min={0}
            step={0.5}
            onChange={(v) => onChange({ distancia_m: v })}
          />
        </>
      )}
      {tipoMedicion === "tiempo" && (
        <CampoNumero
          etiqueta="Segundos"
          valor={bloque.duracion_s}
          min={1}
          onChange={(v) => onChange({ duracion_s: v })}
        />
      )}
      {tipoMedicion === "tecnica" && (
        <>
          <CampoNumero
            etiqueta="Reps"
            valor={bloque.reps}
            min={1}
            onChange={(v) => onChange({ reps: v })}
          />
          <CampoNumero
            etiqueta="Segundos"
            valor={bloque.duracion_s}
            min={1}
            onChange={(v) => onChange({ duracion_s: v })}
          />
          <CampoNumero
            etiqueta="Calidad"
            valor={bloque.calidad}
            min={1}
            max={5}
            onChange={(v) => onChange({ calidad: v })}
          />
        </>
      )}
      <CampoNumero
        etiqueta="RPE"
        valor={bloque.rpe}
        min={1}
        max={10}
        onChange={(v) => onChange({ rpe: v })}
      />
    </div>
  );
}

// Buscador de ejercicio con creacion inline: escribir filtra el catalogo,
// y si no matchea nada ofrece crear uno nuevo ahi mismo (nombre + tipo de
// medicion), sin salir del form de la sesion.
function EjercicioPicker({
  ejercicioId,
  ejercicios,
  onElegir,
}: {
  ejercicioId: number | null;
  ejercicios: Ejercicio[];
  onElegir: (id: number) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [tipoNuevo, setTipoNuevo] = useState<TipoMedicion>("carga");
  const crear = useCrearEjercicio();

  const elegido = ejercicios.find((e) => e.id === ejercicioId) ?? null;
  const termino = busqueda.trim().toLowerCase();
  const coincidencias = (
    termino ? ejercicios.filter((e) => e.nombre.toLowerCase().includes(termino)) : ejercicios
  ).slice(0, 8);
  const sinMatchExacto =
    termino.length > 1 && !ejercicios.some((e) => e.nombre.toLowerCase() === termino);

  if (!abierto) {
    return (
      <button
        type="button"
        onClick={() => {
          setAbierto(true);
          setBusqueda("");
        }}
        className="flex min-h-[40px] w-full items-center justify-between rounded-pill bg-canvas px-4 text-[14px] text-text-primary"
      >
        {elegido?.nombre ?? "Elegir ejercicio…"}
        <Search size={14} className="text-text-secondary" />
      </button>
    );
  }

  return (
    <div className="rounded-bento border border-border-subtle bg-canvas p-2">
      <input
        autoFocus
        type="text"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        placeholder="Buscar ejercicio…"
        className="w-full bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
      />

      <ul className="mt-2 flex max-h-48 flex-col gap-0.5 overflow-y-auto">
        {coincidencias.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => {
                onElegir(e.id);
                setAbierto(false);
              }}
              className="flex w-full items-center justify-between rounded-pill px-3 py-2 text-left text-[13px] text-text-primary hover:bg-surface-secondary"
            >
              {e.nombre}
              <span className="text-[10px] uppercase tracking-widest text-text-secondary">
                {e.tipo_medicion}
              </span>
            </button>
          </li>
        ))}
        {coincidencias.length === 0 && (
          <li className="px-3 py-2 text-[13px] text-text-secondary">Sin resultados.</li>
        )}
      </ul>

      {sinMatchExacto && (
        <div className="mt-2 flex flex-col gap-2 border-t border-border-subtle pt-2">
          <select
            value={tipoNuevo}
            onChange={(e) => setTipoNuevo(e.target.value as TipoMedicion)}
            className="w-full bg-surface-secondary rounded-pill px-4 py-2 text-[13px] text-text-primary outline-none"
          >
            {(Object.keys(NOMBRE_MEDICION) as TipoMedicion[]).map((tm) => (
              <option key={tm} value={tm}>
                {NOMBRE_MEDICION[tm]}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={crear.isPending}
            onClick={async () => {
              const nuevo = await crear.mutateAsync({
                nombre: busqueda.trim(),
                tipo_medicion: tipoNuevo,
              });
              onElegir(nuevo.id);
              setAbierto(false);
            }}
            className="flex items-center justify-center gap-1 rounded-pill bg-text-primary px-4 py-2 text-[13px] font-semibold text-canvas disabled:opacity-50"
          >
            <Plus size={14} />
            {crear.isPending ? "Creando…" : `Crear "${busqueda.trim()}"`}
          </button>
        </div>
      )}
    </div>
  );
}

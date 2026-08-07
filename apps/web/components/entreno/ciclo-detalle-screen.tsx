"use client";

import { useState } from "react";
import { Minus, Pencil, Plus, Trash2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { EjercicioPicker } from "@/components/entreno/bloque-editor";
import { ApiError } from "@/lib/api/client";
import {
  useActualizarSemana,
  useCiclo,
  useComposicion,
  useCrearPlan,
  useCrearSemana,
  useCumplimiento,
  useEjercicios,
  useEliminarSemana,
  usePlanesDeSemana,
  useReemplazarComposicion,
  useSemanas,
  useTiposSesion,
  type BloquePlanCreatePayload,
  type CicloSemana,
  type ComposicionItem,
  type Ejercicio,
  type SesionPlan,
  type TipoMedicion,
} from "@/lib/api/hooks";
import { useFechaDeRegistro } from "@/lib/fecha";

const DIAS_SEMANA = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

type Props = { cicloId: number };

/**
 * Pantalla de detalle de un ciclo (Fase 4 R3a).
 * Tres bloques: header del ciclo, lista de semanas con su composicion
 * objetivo y cumplimiento real, y un form para declarar la composicion
 * de la semana que elijas.
 *
 * Por defecto la semana activa es la que corresponde a la fecha de
 * registro (con corte a las 4am).
 */
export function CicloDetalleScreen({ cicloId }: Props) {
  const ciclo = useCiclo(cicloId);
  const semanas = useSemanas(cicloId);
  const fechaHoy = useFechaDeRegistro();

  const numeroPorFecha = ciclo.data
    ? calcularNumeroSemana(ciclo.data.fecha_inicio, fechaHoy, ciclo.data.semanas)
    : 1;
  const [semanaElegida, setSemanaElegida] = useState<number | null>(null);

  const semanasData = semanas.data ?? [];
  const semanaActiva =
    semanasData.find((s) => s.numero === (semanaElegida ?? numeroPorFecha)) ??
    semanasData[0] ??
    null;

  return (
    <div className="flex flex-col gap-4 pb-32">
      <BentoCard>
        <header>
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Ciclo #{ciclo.data?.numero ?? "..."}
          </p>
          <h2 className="mt-1 text-[24px] font-bold text-text-primary">
            {ciclo.data?.objetivo ?? "..."}
          </h2>
          <p className="mt-1 text-[13px] text-text-secondary">
            {ciclo.data
              ? `${ciclo.data.semanas} semanas · ${ciclo.data.estado}`
              : ""}
            {" · "}
            {ciclo.data?.fecha_inicio}
            {" → "}
            {ciclo.data?.fecha_fin_prevista}
          </p>
        </header>
      </BentoCard>

      <BentoCard>
        <header className="mb-4">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Semanas
          </p>
        </header>

        {semanas.isLoading ? (
          <div className="h-20" />
        ) : semanasData.length === 0 ? (
          <CrearSemanaForm cicloId={cicloId} />
        ) : (
          <div className="flex flex-col gap-4">
            <SelectorSemana
              semanas={semanasData}
              activa={semanaActiva?.numero ?? 1}
              onElegir={setSemanaElegida}
            />
            {semanaActiva && (
              <SemanaBloque
                key={semanaActiva.id}
                cicloId={cicloId}
                semana={semanaActiva}
              />
            )}
            <CrearSemanaForm cicloId={cicloId} />
          </div>
        )}
      </BentoCard>
    </div>
  );
}

function SelectorSemana({
  semanas,
  activa,
  onElegir,
}: {
  semanas: CicloSemana[];
  activa: number;
  onElegir: (n: number) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {semanas.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onElegir(s.numero)}
          aria-pressed={s.numero === activa}
          className={`min-h-[40px] px-4 rounded-pill text-[13px] ${
            s.numero === activa
              ? "bg-text-primary text-canvas"
              : "bg-surface-secondary text-text-secondary"
          }`}
        >
          S{s.numero} · {s.fase}
        </button>
      ))}
    </div>
  );
}

function SemanaBloque({
  cicloId,
  semana,
}: {
  cicloId: number;
  semana: CicloSemana;
}) {
  const composicion = useComposicion(semana.id);
  const cumplimiento = useCumplimiento(semana.id);
  const eliminar = useEliminarSemana(cicloId);

  const [editando, setEditando] = useState(false);
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false);

  return (
    <div className="flex flex-col gap-4 rounded-bento border border-border-subtle bg-surface-secondary p-4">
      {editando ? (
        <EditarSemanaForm
          cicloId={cicloId}
          semana={semana}
          onListo={() => setEditando(false)}
        />
      ) : (
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-[16px] font-semibold text-text-primary">
              Semana {semana.numero} · {semana.fase}
            </p>
            <p className="text-[11px] uppercase tracking-widest text-text-secondary">
              {semana.rpe_objetivo_min !== null && semana.rpe_objetivo_max !== null
                ? `RPE ${semana.rpe_objetivo_min}-${semana.rpe_objetivo_max}`
                : "RPE libre"}
              {semana.volumen_pct !== 100 && ` · volumen ${semana.volumen_pct}%`}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Editar semana"
              onClick={() => setEditando(true)}
              className="p-2 text-text-secondary"
            >
              <Pencil size={16} />
            </button>
            <button
              type="button"
              aria-label="Eliminar semana"
              onClick={() => setConfirmandoEliminar(true)}
              className="p-2 text-state-danger"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>
      )}

      {confirmandoEliminar && (
        <div className="flex flex-col gap-3 rounded-bento bg-canvas p-3">
          <p className="text-[13px] text-text-secondary">
            Eliminar esta semana, su composicion y sus planes? Las sesiones
            reales ya registradas no se borran. No se puede deshacer.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setConfirmandoEliminar(false)}
              className="flex-1 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary"
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={eliminar.isPending}
              onClick={async () => {
                await eliminar.mutateAsync(semana.id);
                setConfirmandoEliminar(false);
              }}
              className="flex-1 rounded-pill bg-state-danger py-2.5 text-[13px] font-semibold text-canvas disabled:opacity-50"
            >
              {eliminar.isPending ? "Eliminando..." : "Eliminar"}
            </button>
          </div>
        </div>
      )}

      <CumplimientoBloque
        items={cumplimiento.data ?? []}
        cargando={cumplimiento.isLoading}
      />

      <ComposicionForm semanaId={semana.id} actuales={composicion.data ?? []} />

      <PlanesBloque semanaId={semana.id} />
    </div>
  );
}

function PlanesBloque({ semanaId }: { semanaId: number }) {
  const planes = usePlanesDeSemana(semanaId);
  const tipos = useTiposSesion();
  const [planeando, setPlaneando] = useState(false);

  const planesData = planes.data ?? [];

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Sesiones planeadas
        </p>
        {!planeando && (
          <button
            type="button"
            onClick={() => setPlaneando(true)}
            className="flex items-center gap-1 rounded-pill bg-canvas px-4 py-1.5 text-[13px] font-medium text-text-primary"
          >
            <Plus size={14} /> Planear sesion
          </button>
        )}
      </div>

      {!planes.isLoading && planesData.length === 0 && !planeando && (
        <p className="text-[13px] text-text-secondary">
          Todavia no hay sesiones planeadas para esta semana.
        </p>
      )}

      {planesData.length > 0 && (
        <ul className="flex flex-col gap-2">
          {planesData.map((p) => (
            <PlanCard key={p.id} plan={p} tipoNombre={
              tipos.data?.find((t) => t.id === p.tipo_sesion_id)?.nombre ?? "sesion"
            } />
          ))}
        </ul>
      )}

      {planeando && (
        <CrearPlanForm semanaId={semanaId} onListo={() => setPlaneando(false)} />
      )}
    </div>
  );
}

function PlanCard({ plan, tipoNombre }: { plan: SesionPlan; tipoNombre: string }) {
  return (
    <li className="rounded-bento bg-canvas px-4 py-2 text-[13px]">
      <div className="flex items-center justify-between">
        <span className="font-medium capitalize text-text-primary">{tipoNombre}</span>
        <span className="tabular text-text-secondary">
          {plan.dia_sugerido !== null ? DIAS_SEMANA[plan.dia_sugerido] : "Sin dia"}
        </span>
      </div>
      <p className="mt-0.5 text-[11px] text-text-secondary">
        {[
          plan.rpe_objetivo !== null && `RPE ${plan.rpe_objetivo}`,
          plan.duracion_min_est !== null && `${plan.duracion_min_est} min`,
          plan.bloques_planeados.length > 0 &&
            `${plan.bloques_planeados.length} bloque${plan.bloques_planeados.length === 1 ? "" : "s"}`,
        ]
          .filter(Boolean)
          .join(" · ") || "Sin detalle"}
      </p>
    </li>
  );
}

type BloquePlanBorrador = {
  localId: number;
  ejercicio_id: number | null;
  series: number | null;
  reps_min: number | null;
  reps_max: number | null;
  peso_objetivo_kg: number | null;
  distancia_objetivo_m: number | null;
  duracion_objetivo_s: number | null;
};

function bloquePlanVacio(): BloquePlanBorrador {
  return {
    localId: Math.floor(Math.random() * 1e9),
    ejercicio_id: null,
    series: null,
    reps_min: null,
    reps_max: null,
    peso_objetivo_kg: null,
    distancia_objetivo_m: null,
    duracion_objetivo_s: null,
  };
}

function bloquePlanInvalido(b: BloquePlanBorrador): boolean {
  if (b.ejercicio_id === null) return true;
  if (b.reps_min !== null && b.reps_max !== null && b.reps_min > b.reps_max) return true;
  return false;
}

function CrearPlanForm({
  semanaId,
  onListo,
}: {
  semanaId: number;
  onListo: () => void;
}) {
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const crear = useCrearPlan(semanaId);

  const [tipoSesionId, setTipoSesionId] = useState<number | null>(null);
  const [diaSugerido, setDiaSugerido] = useState<number | null>(null);
  const [objetivo, setObjetivo] = useState("");
  const [duracionMinEst, setDuracionMinEst] = useState<number | null>(null);
  const [rpeObjetivo, setRpeObjetivo] = useState<number | null>(null);
  const [bloques, setBloques] = useState<BloquePlanBorrador[]>([]);

  // Sincroniza el select cuando el catalogo termina de cargar.
  const primerTipo = tipos.data?.[0];
  if (primerTipo && tipoSesionId === null) {
    setTipoSesionId(primerTipo.id);
  }

  const puedeGuardar =
    tipoSesionId !== null && bloques.every((b) => !bloquePlanInvalido(b));

  return (
    <div className="mt-3 flex flex-col gap-3 rounded-bento border border-border-subtle bg-canvas p-3">
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Tipo de sesion
          </span>
          <select
            value={tipoSesionId ?? ""}
            onChange={(e) => setTipoSesionId(Number(e.target.value))}
            className="bg-surface-secondary rounded-pill px-3 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          >
            {tipos.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Dia sugerido
          </span>
          <select
            value={diaSugerido ?? ""}
            onChange={(e) =>
              setDiaSugerido(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-surface-secondary rounded-pill px-3 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          >
            <option value="">Sin dia</option>
            {DIAS_SEMANA.map((d, i) => (
              <option key={d} value={i}>
                {d}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE objetivo
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeObjetivo ?? ""}
            onChange={(e) =>
              setRpeObjetivo(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Duracion est. (min)
          </span>
          <input
            type="number"
            min={1}
            value={duracionMinEst ?? ""}
            onChange={(e) =>
              setDuracionMinEst(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-[10px] uppercase tracking-widest text-text-secondary">
          Objetivo (opcional)
        </span>
        <input
          type="text"
          value={objetivo}
          onChange={(e) => setObjetivo(e.target.value)}
          placeholder="ej. base aerobica"
          className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
        />
      </label>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-[10px] uppercase tracking-widest text-text-secondary">
            Bloques objetivo
          </p>
          <button
            type="button"
            onClick={() => setBloques((arr) => [...arr, bloquePlanVacio()])}
            className="flex items-center gap-1 rounded-pill bg-surface-secondary px-3 py-1 text-[12px] font-medium text-text-primary"
          >
            <Plus size={12} /> Agregar
          </button>
        </div>
        <div className="flex flex-col gap-2">
          {bloques.map((b, idx) => (
            <BloquePlanCard
              key={b.localId}
              bloque={b}
              orden={idx}
              ejercicios={ejercicios.data ?? []}
              onChange={(cambio) =>
                setBloques((arr) =>
                  arr.map((it, i) => (i === idx ? { ...it, ...cambio } : it)),
                )
              }
              onEliminar={() =>
                setBloques((arr) => arr.filter((_, i) => i !== idx))
              }
            />
          ))}
        </div>
      </div>

      {crear.error && (
        <p className="text-[12px] text-state-danger">
          {crear.error instanceof ApiError
            ? crear.error.message
            : "No se pudo crear el plan."}
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onListo}
          className="flex-1 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary"
        >
          Cancelar
        </button>
        <button
          type="button"
          disabled={!puedeGuardar || crear.isPending}
          onClick={async () => {
            if (tipoSesionId === null) return;
            await crear.mutateAsync({
              dia_sugerido: diaSugerido,
              tipo_sesion_id: tipoSesionId,
              objetivo: objetivo.trim() || null,
              duracion_min_est: duracionMinEst,
              rpe_objetivo: rpeObjetivo,
              bloques: bloques
                .filter((b): b is BloquePlanBorrador & { ejercicio_id: number } =>
                  b.ejercicio_id !== null,
                )
                .map((b, i): BloquePlanCreatePayload => ({
                  ejercicio_id: b.ejercicio_id,
                  orden: i,
                  series: b.series,
                  reps_min: b.reps_min,
                  reps_max: b.reps_max,
                  peso_objetivo_kg: b.peso_objetivo_kg,
                  distancia_objetivo_m: b.distancia_objetivo_m,
                  duracion_objetivo_s: b.duracion_objetivo_s,
                })),
            });
            onListo();
          }}
          className="flex-1 rounded-pill bg-text-primary py-2.5 text-[13px] font-semibold text-canvas disabled:opacity-50"
        >
          {crear.isPending ? "Guardando..." : "Guardar plan"}
        </button>
      </div>
    </div>
  );
}

function BloquePlanCard({
  bloque,
  orden,
  ejercicios,
  onChange,
  onEliminar,
}: {
  bloque: BloquePlanBorrador;
  orden: number;
  ejercicios: Ejercicio[];
  onChange: (c: Partial<BloquePlanBorrador>) => void;
  onEliminar: () => void;
}) {
  const ejercicio = ejercicios.find((e) => e.id === bloque.ejercicio_id) ?? null;

  return (
    <div className="rounded-bento border border-border-subtle bg-surface-secondary p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Bloque {orden + 1}
        </p>
        <button
          type="button"
          onClick={onEliminar}
          aria-label="Eliminar bloque"
          className="p-1 text-text-secondary"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <div className="mt-2">
        <EjercicioPicker
          ejercicioId={bloque.ejercicio_id}
          ejercicios={ejercicios}
          onElegir={(id) => onChange({ ejercicio_id: id })}
        />
      </div>

      {ejercicio && (
        <CamposBloquePlan
          bloque={bloque}
          tipoMedicion={ejercicio.tipo_medicion}
          onChange={onChange}
        />
      )}
    </div>
  );
}

function CampoNumeroPlan({
  etiqueta,
  valor,
  min,
  step,
  onChange,
}: {
  etiqueta: string;
  valor: number | null;
  min?: number;
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
        step={step}
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
      />
    </label>
  );
}

function CamposBloquePlan({
  bloque,
  tipoMedicion,
  onChange,
}: {
  bloque: BloquePlanBorrador;
  tipoMedicion: TipoMedicion;
  onChange: (c: Partial<BloquePlanBorrador>) => void;
}) {
  return (
    <div className="mt-2 grid grid-cols-4 gap-2">
      {tipoMedicion === "carga" && (
        <>
          <CampoNumeroPlan
            etiqueta="Sets"
            valor={bloque.series}
            min={1}
            onChange={(v) => onChange({ series: v })}
          />
          <CampoNumeroPlan
            etiqueta="Reps min"
            valor={bloque.reps_min}
            min={1}
            onChange={(v) => onChange({ reps_min: v })}
          />
          <CampoNumeroPlan
            etiqueta="Reps max"
            valor={bloque.reps_max}
            min={1}
            onChange={(v) => onChange({ reps_max: v })}
          />
          <CampoNumeroPlan
            etiqueta="Kg"
            valor={bloque.peso_objetivo_kg}
            min={0}
            step={0.5}
            onChange={(v) => onChange({ peso_objetivo_kg: v })}
          />
        </>
      )}
      {tipoMedicion === "distancia" && (
        <>
          <CampoNumeroPlan
            etiqueta="Reps min"
            valor={bloque.reps_min}
            min={1}
            onChange={(v) => onChange({ reps_min: v })}
          />
          <CampoNumeroPlan
            etiqueta="Reps max"
            valor={bloque.reps_max}
            min={1}
            onChange={(v) => onChange({ reps_max: v })}
          />
          <CampoNumeroPlan
            etiqueta="Metros"
            valor={bloque.distancia_objetivo_m}
            min={0}
            step={0.5}
            onChange={(v) => onChange({ distancia_objetivo_m: v })}
          />
        </>
      )}
      {(tipoMedicion === "tiempo" || tipoMedicion === "tecnica") && (
        <>
          {tipoMedicion === "tecnica" && (
            <>
              <CampoNumeroPlan
                etiqueta="Reps min"
                valor={bloque.reps_min}
                min={1}
                onChange={(v) => onChange({ reps_min: v })}
              />
              <CampoNumeroPlan
                etiqueta="Reps max"
                valor={bloque.reps_max}
                min={1}
                onChange={(v) => onChange({ reps_max: v })}
              />
            </>
          )}
          <CampoNumeroPlan
            etiqueta="Segundos"
            valor={bloque.duracion_objetivo_s}
            min={1}
            onChange={(v) => onChange({ duracion_objetivo_s: v })}
          />
        </>
      )}
    </div>
  );
}

function EditarSemanaForm({
  cicloId,
  semana,
  onListo,
}: {
  cicloId: number;
  semana: CicloSemana;
  onListo: () => void;
}) {
  const actualizar = useActualizarSemana(cicloId);
  const [fase, setFase] = useState(semana.fase);
  const [rpeMin, setRpeMin] = useState(semana.rpe_objetivo_min);
  const [rpeMax, setRpeMax] = useState(semana.rpe_objetivo_max);
  const [volumen, setVolumen] = useState(semana.volumen_pct);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await actualizar.mutateAsync({
          id: semana.id,
          fase,
          rpe_objetivo_min: rpeMin,
          rpe_objetivo_max: rpeMax,
          volumen_pct: volumen,
        });
        onListo();
      }}
      className="flex flex-col gap-3"
    >
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">
        Editar semana {semana.numero}
      </p>
      <label className="flex flex-col gap-1">
        <span className="text-[10px] uppercase tracking-widest text-text-secondary">
          Fase
        </span>
        <select
          value={fase}
          onChange={(e) =>
            setFase(e.target.value as "readaptacion" | "carga" | "descarga")
          }
          className="bg-canvas rounded-pill px-3 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
        >
          <option value="readaptacion">Readaptacion</option>
          <option value="carga">Carga</option>
          <option value="descarga">Descarga</option>
        </select>
      </label>
      <div className="grid grid-cols-3 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE min
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeMin ?? ""}
            onChange={(e) =>
              setRpeMin(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE max
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeMax ?? ""}
            onChange={(e) =>
              setRpeMax(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Volumen %
          </span>
          <input
            type="number"
            min={1}
            value={volumen}
            onChange={(e) =>
              setVolumen(e.target.value === "" ? 0 : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onListo}
          className="flex-1 rounded-pill bg-canvas py-2.5 text-[13px] font-medium text-text-primary"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={volumen < 1 || actualizar.isPending}
          className="flex-1 rounded-pill bg-text-primary py-2.5 text-[13px] font-semibold text-canvas disabled:opacity-50"
        >
          {actualizar.isPending ? "Guardando..." : "Guardar"}
        </button>
      </div>
    </form>
  );
}

function CumplimientoBloque({
  items,
  cargando,
}: {
  items: import("@/lib/api/hooks").CumplimientoItem[];
  cargando: boolean;
}) {
  if (cargando) {
    return <div className="h-12" />;
  }
  if (items.length === 0) {
    return (
      <p className="text-[13px] text-text-secondary">
        Aun no hay composicion declarada para esta semana.
      </p>
    );
  }
  return (
    <div>
      <p className="mb-2 text-[11px] uppercase tracking-widest text-text-secondary">
        Cumplimiento
      </p>
      <ul className="flex flex-col gap-1">
        {items.map((it) => (
          <li
            key={it.tipo_sesion_id}
            className="flex items-center justify-between text-[13px]"
          >
            <span className="text-text-primary">{it.tipo_sesion_nombre}</span>
            <span
              className={`tabular ${
                it.cumplido ? "text-state-positive" : "text-text-secondary"
              }`}
            >
              {it.hecho} / {it.objetivo}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ComposicionForm({
  semanaId,
  actuales,
}: {
  semanaId: number;
  actuales: ComposicionItem[];
}) {
  const tipos = useTiposSesion();
  const reemplazar = useReemplazarComposicion(semanaId);

  const [items, setItems] = useState<ComposicionItem[]>(actuales);

  // Sincroniza cuando el server trae composicion y el form esta vacio.
  // OJO: setState durante render es un anti-patron, pero aca es seguro
  // porque la condicion es estable (actuales.length > 0 && items.length === 0)
  // y no produce renders en loop. Si los items del server vienen en otro
  // orden la proxima vez, el form los va a tomar igual.
  if (
    actuales.length > 0 &&
    items.length === 0 &&
    !reemplazar.isPending
  ) {
    setItems(actuales);
  }

  function agregar() {
    const primero = tipos.data?.[0];
    if (!primero) return;
    setItems((arr) => [
      ...arr,
      { tipo_sesion_id: primero.id, cantidad_objetivo: 1 },
    ]);
  }

  function eliminar(idx: number) {
    setItems((arr) => arr.filter((_, i) => i !== idx));
  }

  function actualizar(idx: number, cambio: Partial<ComposicionItem>) {
    setItems((arr) =>
      arr.map((it, i) => (i === idx ? { ...it, ...cambio } : it)),
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Composicion objetivo
        </p>
        <button
          type="button"
          onClick={agregar}
          disabled={!tipos.data || tipos.data.length === 0}
          className="flex items-center gap-1 rounded-pill bg-canvas px-4 py-1.5 text-[13px] font-medium text-text-primary disabled:opacity-50"
        >
          <Plus size={14} /> Agregar
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {items.map((it, idx) => (
          <div
            key={`${it.tipo_sesion_id}-${idx}`}
            className="flex items-center gap-2"
          >
            <select
              value={it.tipo_sesion_id}
              onChange={(e) =>
                actualizar(idx, { tipo_sesion_id: Number(e.target.value) })
              }
              className="flex-1 bg-canvas rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            >
              {tipos.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={1}
              value={it.cantidad_objetivo}
              onChange={(e) =>
                actualizar(idx, {
                  cantidad_objetivo: e.target.value === "" ? 0 : Number(e.target.value),
                })
              }
              className="w-16 bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
            <button
              type="button"
              onClick={() => eliminar(idx)}
              aria-label="Eliminar"
              className="p-2 text-text-secondary"
            >
              <Minus size={14} />
            </button>
          </div>
        ))}
      </div>

      <button
        type="button"
        disabled={
          items.length === 0 ||
          items.some((it) => it.cantidad_objetivo < 1) ||
          reemplazar.isPending
        }
        onClick={async () => {
          await reemplazar.mutateAsync(items);
        }}
        className="mt-4 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
      >
        {reemplazar.isPending ? "Guardando..." : "Guardar composicion"}
      </button>
    </div>
  );
}

function CrearSemanaForm({ cicloId }: { cicloId: number }) {
  const crear = useCrearSemana(cicloId);
  const [numero, setNumero] = useState(1);
  const [fase, setFase] = useState<"readaptacion" | "carga" | "descarga">("carga");
  const [rpeMin, setRpeMin] = useState<number | null>(null);
  const [rpeMax, setRpeMax] = useState<number | null>(null);
  const [volumen, setVolumen] = useState(100);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await crear.mutateAsync({
          numero,
          fase,
          rpe_objetivo_min: rpeMin,
          rpe_objetivo_max: rpeMax,
          volumen_pct: volumen,
        });
      }}
      className="flex flex-col gap-3"
    >
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">
        Nueva semana
      </p>
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Numero
          </span>
          <input
            type="number"
            min={1}
            value={numero}
            onChange={(e) =>
              setNumero(e.target.value === "" ? 0 : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Fase
          </span>
          <select
            value={fase}
            onChange={(e) =>
              setFase(e.target.value as "readaptacion" | "carga" | "descarga")
            }
            className="bg-canvas rounded-pill px-3 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          >
            <option value="readaptacion">Readaptacion</option>
            <option value="carga">Carga</option>
            <option value="descarga">Descarga</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE min
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeMin ?? ""}
            onChange={(e) =>
              setRpeMin(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE max
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeMax ?? ""}
            onChange={(e) =>
              setRpeMax(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Volumen %
          </span>
          <input
            type="number"
            min={1}
            value={volumen}
            onChange={(e) =>
              setVolumen(e.target.value === "" ? 0 : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>
      <button
        type="submit"
        disabled={numero < 1 || volumen < 1 || crear.isPending}
        className="rounded-pill bg-canvas py-2 text-[14px] font-semibold text-text-primary disabled:opacity-50"
      >
        {crear.isPending ? "Creando..." : "Crear semana"}
      </button>
    </form>
  );
}

// ---------- Helpers ----------

function calcularNumeroSemana(
  fechaInicio: string,
  fechaActual: string,
  totalSemanas: number,
): number {
  const inicio = new Date(fechaInicio).getTime();
  const actual = new Date(fechaActual).getTime();
  const diffDias = Math.floor((actual - inicio) / (1000 * 60 * 60 * 24));
  if (diffDias < 0) return 1;
  const n = Math.floor(diffDias / 7) + 1;
  return Math.min(n, totalSemanas);
}

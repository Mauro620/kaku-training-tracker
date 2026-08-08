"use client";

import { useEffect, useMemo, useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useParametro,
  useSuenoDeHoy,
  useSuenoUltimosNDias,
  useUpsertSueno,
  type RegistroSueno,
} from "@/lib/api/hooks";

type Props = { fecha: string };

const DEBOUNCE_MS = 800;
const OBJETIVO_DEFAULT_H = 7;
const HISTORIAL_DIAS = 14;
const DEUDA_DIAS = 7;

/**
 * Sueno del dia (H3 de la revision de UI).
 *
 * Cuatro elementos que nunca faltan a la regla "ningun numero solo":
 *
 *   1. Horas grandes + delta contra el objetivo leido de `parametro`
 *      (`sueno_objetivo_horas`, default 7). Texto: "5.9 h · 1.1 bajo objetivo".
 *   2. Barra de progreso hacia el objetivo (proporcion horas/objetivo).
 *      Banda verde si >= objetivo, amarilla si >= objetivo - 1h, gris si <.
 *   3. Linea de contexto con la hora de acostarse vs media de los ultimos
 *      14 dias. No se mide contra un patron externo, contra la propia
 *      tendencia del usuario.
 *   4. Barras de los ultimos 14 dias (altura = horas, color por banda).
 *      Huecos (dias sin registro) explicitos como "Sin registro" abajo.
 *   5. Deuda acumulada 7d (REGLAS_NEGOCIO §6): suma de max(0, objetivo - horas).
 *      Solo cuenta lo que falta, no lo que sobra.
 */
export function SuenoCard({ fecha }: Props) {
  const { data: hoy, isLoading } = useSuenoDeHoy(fecha);
  const { data: paramObjetivo } = useParametro("sueno_objetivo_horas");
  const { data: ultimosDias } = useSuenoUltimosNDias(HISTORIAL_DIAS);
  const { mutate, isPending, isSuccess } = useUpsertSueno(fecha);

  const objetivo = useMemo(() => {
    if (!paramObjetivo) return OBJETIVO_DEFAULT_H;
    const n = Number(paramObjetivo.valor);
    return Number.isFinite(n) && n > 0 ? n : OBJETIVO_DEFAULT_H;
  }, [paramObjetivo]);

  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const [celular, setCelular] = useState<boolean | null>(null);
  const [tocado, setTocado] = useState(false);

  useEffect(() => {
    if (hoy && !tocado) {
      setInicio(toLocalTime(hoy.inicio));
      setFin(toLocalTime(hoy.fin));
      setCelular(hoy.celular_fuera);
    }
  }, [hoy, tocado]);

  useEffect(() => {
    if (!tocado || !inicio || !fin) return;
    const id = setTimeout(() => {
      mutate({
        inicio: toIsoDeInicio(fecha, inicio, fin),
        fin: toIsoLocal(fecha, fin),
        celular_fuera: celular,
      });
    }, DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [inicio, fin, celular, tocado, fecha, mutate]);

  const horas =
    inicio && fin ? formatHorasSueno(inicio, fin) : (hoy?.horas_sueno ?? null);

  const horasNum = horas === null ? null : Number(horas);

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Sueno
        </p>
        <span className="text-[11px] text-text-secondary">
          {isPending ? "Guardando…" : isSuccess || hoy ? "Guardado" : ""}
        </span>
      </header>

      {isLoading ? (
        <div className="h-32" />
      ) : (
        <>
          <HorasConContexto horasNum={horasNum} objetivo={objetivo} />

          <div className="mt-5 grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-widest text-text-secondary">
                Acostarse
              </span>
              <input
                type="time"
                value={inicio}
                onChange={(e) => {
                  setInicio(e.target.value);
                  setTocado(true);
                }}
                className="bg-surface-secondary rounded-pill px-4 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-widest text-text-secondary">
                Despertar
              </span>
              <input
                type="time"
                value={fin}
                onChange={(e) => {
                  setFin(e.target.value);
                  setTocado(true);
                }}
                className="bg-surface-secondary rounded-pill px-4 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
          </div>

          <label className="mt-4 flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={celular === true}
              onChange={(e) => {
                setCelular(e.target.checked);
                setTocado(true);
              }}
              className="h-5 w-5 accent-text-primary"
            />
            <span className="text-[14px] text-text-secondary">Celular fuera</span>
          </label>

          <ContextoHora inicio={inicio} ultimosDias={ultimosDias} />

          <BarrasHistorial
            registros={ultimosDias ?? []}
            objetivo={objetivo}
            dias={HISTORIAL_DIAS}
            fecha={fecha}
          />

          <DeudaAcumulada
            registros={ultimosDias ?? []}
            objetivo={objetivo}
            dias={DEUDA_DIAS}
          />
        </>
      )}
    </BentoCard>
  );
}

// ---------- Subcomponentes ----------

/** Horas grandes + delta contra el objetivo. Si no hay registro, "—" + texto
 * explicando que falta.
 */
function HorasConContexto({
  horasNum,
  objetivo,
}: {
  horasNum: number | null;
  objetivo: number;
}) {
  if (horasNum === null) {
    return (
      <>
        <p className="text-[48px] font-bold leading-none tabular text-text-primary">
          —
          <span className="ml-2 text-base font-medium text-text-secondary">h</span>
        </p>
        <p className="mt-2 text-[13px] text-text-secondary">
          Sin registro de sueno hoy.
        </p>
      </>
    );
  }

  const delta = horasNum - objetivo;
  const horasTexto = horasNum.toFixed(1);
  const rengoBanda = clasificarBanda(horasNum, objetivo);

  const contextoDelta = (() => {
    if (Math.abs(delta) < 0.05) return "en objetivo";
    if (delta > 0) {
      return `${delta.toFixed(1)} sobre objetivo`;
    }
    return `${Math.abs(delta).toFixed(1)} bajo objetivo`;
  })();

  return (
    <>
      <div className="flex items-baseline gap-3">
        <p className="text-[48px] font-bold leading-none tabular text-text-primary">
          {horasTexto}
          <span className="ml-2 text-base font-medium text-text-secondary">h</span>
        </p>
        <p className="text-[13px] text-text-secondary">
          {contextoDelta}
          <span className="text-text-secondary"> · {objetivo} h</span>
        </p>
      </div>
      <BarraProgreso horas={horasNum} objetivo={objetivo} banda={rengoBanda} />
    </>
  );
}

function BarraProgreso({
  horas,
  objetivo,
  banda,
}: {
  horas: number;
  objetivo: number;
  banda: "ok" | "cerca" | "bajo";
}) {
  const proporcion = Math.min(horas / objetivo, 1);
  const color =
    banda === "ok"
      ? "bg-state-positive"
      : banda === "cerca"
        ? "bg-state-warning"
        : "bg-state-danger";
  return (
    <div className="mt-3 h-1.5 w-full rounded-full bg-surface-secondary overflow-hidden">
      <div
        className={`h-full ${color}`}
        style={{ width: `${(proporcion * 100).toFixed(1)}%` }}
        aria-label={`${horas.toFixed(1)} de ${objetivo} horas`}
      />
    </div>
  );
}

/** "Te acostaste a las 01:32, tu media es 00:30". Distancia angular:
 * la diferencia se mide en el reloj de 24h, asi que un inicio a la 01:32
 * con media 23:30 no es "22 horas antes" sino "2 horas despues".
 */
function ContextoHora({
  inicio,
  ultimosDias,
}: {
  inicio: string;
  ultimosDias: RegistroSueno[] | undefined;
}) {
  const media = useMemo(() => {
    if (!ultimosDias || ultimosDias.length === 0) return null;
    const minutos = ultimosDias
      .map((r) => toMinutos(r.inicio))
      .filter((m) => m !== null);
    if (minutos.length === 0) return null;
    const promedio = minutos.reduce((a, b) => a + (b ?? 0), 0) / minutos.length;
    return promedio;
  }, [ultimosDias]);

  if (!inicio || media === null) return null;

  const inicioMin = toMinutos(inicio);
  if (inicioMin === null) return null;

  // Distancia angular sobre el reloj de 24h. Si la diferencia lineal
  // es > 12h, el atajo mas corto es envolver el reloj por el otro lado.
  let diffMin = inicioMin - media;
  if (diffMin > 12 * 60) diffMin -= 24 * 60;
  else if (diffMin < -12 * 60) diffMin += 24 * 60;

  const absMin = Math.abs(Math.round(diffMin));
  const direccion = diffMin > 0 ? "despues" : "antes";
  const diffTexto =
    absMin < 1
      ? "a tu hora habitual"
      : `${absMin} min ${direccion}`;

  return (
    <p className="mt-4 text-[13px] text-text-secondary">
      Te acostaste a las {inicio} · {diffTexto} · media{" "}
      <span className="text-text-primary">{toHHMM(media)}</span>
    </p>
  );
}

/** Barras de los ultimos N dias. Altura proporcional a horas, color por
 * banda. Dias sin registro explicitos como placeholder.
 */
function BarrasHistorial({
  registros,
  objetivo,
  dias,
  fecha,
}: {
  registros: RegistroSueno[];
  objetivo: number;
  dias: number;
  fecha: string;
}) {
  // Construir el rango de fechas y mapear. `fecha` es hoy.
  const rango = useMemo(() => {
    const out: { fecha: Date; registro: RegistroSueno | undefined }[] = [];
    const base = new Date(`${fecha}T00:00:00`);
    for (let i = dias - 1; i >= 0; i--) {
      const d = new Date(base);
      d.setDate(d.getDate() - i);
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      const registro = registros.find((r) => r.fecha === iso);
      out.push({ fecha: d, registro });
    }
    return out;
  }, [registros, dias, fecha]);

  const maxHoras = useMemo(() => {
    const observadas = rango.map((r) => (r.registro ? Number(r.registro.horas_sueno) : 0));
    // Si el usuario siempre duerme menos que el objetivo, la barra superior
    // no debe hacer "zoom" raro: la referencia es el objetivo (o un poco
    // mas si la observacion lo supera).
    const max = Math.max(objetivo, ...observadas, 6);
    return Math.ceil(max);
  }, [rango, objetivo]);

  const diasConDato = rango.filter((r) => r.registro).length;
  const diasSinDato = rango.length - diasConDato;

  return (
    <div className="mt-6">
      <p className="mb-2 text-[11px] tracking-widest uppercase text-text-secondary">
        Ultimos {dias} dias
      </p>
      <div className="flex items-end gap-1 h-20">
        {rango.map(({ fecha: d, registro }) => {
          const horas = registro ? Number(registro.horas_sueno) : null;
          // B1: dias sin dato renderizan una ranura tenue de altura minima,
          // no ausencia. Asi el eje se lee completo desde el primer dia.
          const altura = horas === null ? "h-1" : `${Math.max(8, (horas / maxHoras) * 80)}px`;
          const banda = horas === null ? "vacio" : clasificarBanda(horas, objetivo);
          const color =
            banda === "ok"
              ? "bg-state-positive"
              : banda === "cerca"
                ? "bg-state-warning"
                : banda === "vacio"
                  ? "bg-border-subtle"
                  : "bg-state-danger";
          const titulo = `${d.getDate()}/${d.getMonth() + 1}: ${
            horas === null ? "sin registro" : `${horas.toFixed(1)} h`
          }`;
          return (
            <div
              key={d.toISOString()}
              className={`flex-1 rounded-t ${color}`}
              style={{ height: altura }}
              title={titulo}
              aria-label={titulo}
            />
          );
        })}
      </div>
      {diasSinDato > 0 && (
        <p className="mt-2 text-[11px] text-text-secondary">
          {diasSinDato} de {dias} dias sin registro.
        </p>
      )}
    </div>
  );
}

/** Deuda acumulada 7d (REGLAS_NEGOCIO §6):
 *   deuda_sueno_7d = Σ max(0, sueno_objetivo_horas - horas_sueno_del_dia)
 *
 * El texto es accionable: "deuda 7d 6.4 h" + "te faltan 6.4 h esta
 * semana". Si es 0, dice "al dia: deberias dormir bien el resto".
 */
function DeudaAcumulada({
  registros,
  objetivo,
  dias,
}: {
  registros: RegistroSueno[];
  objetivo: number;
  dias: number;
}) {
  const deuda = useMemo(() => {
    if (!registros || registros.length === 0) return 0;
    // Para el calculo de la deuda tomamos los primeros `dias` registros
    // contados desde el mas reciente (que es el orden de la query).
    const recientes = registros.slice(0, dias);
    const total = recientes.reduce((acc, r) => {
      const h = Number(r.horas_sueno);
      return acc + Math.max(0, objetivo - h);
    }, 0);
    return total;
  }, [registros, dias, objetivo]);

  if (deuda === 0) {
    return (
      <p className="mt-4 text-[13px] text-text-secondary">
        Deuda 7d: 0 h · al dia con el objetivo.
      </p>
    );
  }

  return (
    <p className="mt-4 text-[13px] text-text-secondary">
      Deuda 7d:{" "}
      <span className="font-bold text-text-primary tabular">
        {deuda.toFixed(1)} h
      </span>
    </p>
  );
}

// ---------- Helpers ----------

function clasificarBanda(
  horas: number,
  objetivo: number,
): "ok" | "cerca" | "bajo" {
  if (horas >= objetivo) return "ok";
  if (horas >= objetivo - 1) return "cerca";
  return "bajo";
}

function toLocalTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function toIsoLocal(fecha: string, hora: string): string {
  return `${fecha}T${hora}:00`;
}

function toIsoDeInicio(fecha: string, inicio: string, fin: string): string {
  const dia = inicio <= fin ? fecha : restarUnDia(fecha);
  return toIsoLocal(dia, inicio);
}

function restarUnDia(fecha: string): string {
  const [y = 1970, m = 1, d = 1] = fecha.split("-").map(Number);
  const local = new Date(y, m - 1, d);
  local.setDate(local.getDate() - 1);
  const yy = local.getFullYear();
  const mm = String(local.getMonth() + 1).padStart(2, "0");
  const dd = String(local.getDate()).padStart(2, "0");
  return `${yy}-${mm}-${dd}`;
}

function formatHorasSueno(inicio: string, fin: string): string {
  const [ih = 0, im = 0] = inicio.split(":").map(Number);
  const [fh = 0, fm = 0] = fin.split(":").map(Number);
  let minutos = fh * 60 + fm - (ih * 60 + im);
  if (minutos < 0) minutos += 24 * 60;
  return (minutos / 60).toFixed(1);
}

/** Minutos desde medianoche de una fecha ISO. Si la hora cruza
 * medianoche (porque inicio puede ser del dia anterior), lo detecta.
 */
function toMinutos(iso: string): number | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.getHours() * 60 + d.getMinutes();
}

function toHHMM(minutos: number): string {
  const h = Math.floor(minutos / 60) % 24;
  const m = Math.round(minutos % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

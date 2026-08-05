"use client";

import { useEffect, useRef, useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { useSuenoDeHoy, useUpsertSueno } from "@/lib/api/hooks";

type Props = { fecha: string };

const DEBOUNCE_MS = 800;

/**
 * Sueño del día (DESIGN.md §2.1, SPEC.md §1, REGLAS_NEGOCIO §6).
 * Dos inputs nativos time + un checkbox. Autoguardado con debounce, sin
 * botón: el registro se hace en 30s en la cama, la fricción mata.
 */
export function SuenoCard({ fecha }: Props) {
  const { data, isLoading } = useSuenoDeHoy(fecha);
  const { mutate, isPending, isSuccess } = useUpsertSueno(fecha);

  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const [celular, setCelular] = useState<boolean | null>(null);
  // El usuario ya tocó algo: no pisar su borrador si el servidor responde.
  const [tocado, setTocado] = useState(false);

  useEffect(() => {
    if (data && !tocado) {
      setInicio(toLocalTime(data.inicio));
      setFin(toLocalTime(data.fin));
      setCelular(data.celular_fuera);
    }
  }, [data, tocado]);

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
    inicio && fin ? formatHorasSueno(inicio, fin) : (data?.horas_sueno ?? null);

  return (
    <BentoCard ancho="half">
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Sueño
        </p>
        <span className="text-[11px] text-text-secondary">
          {isPending ? "Guardando…" : isSuccess || data ? "Guardado" : ""}
        </span>
      </header>

      {isLoading ? (
        <div className="h-20" />
      ) : (
        <>
          <p className="text-[48px] font-bold leading-none tabular text-text-primary">
            {horas === null ? "—" : horas}
            <span className="ml-2 text-base font-medium text-text-secondary">h</span>
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
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
        </>
      )}
    </BentoCard>
  );
}

// ---------- Helpers locales ----------

function toLocalTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function toIsoLocal(fecha: string, hora: string): string {
  return `${fecha}T${hora}:00`;
}

/**
 * `fecha` es siempre la fecha del despertar (REGLAS_NEGOCIO §6). La hora de
 * acostarse pertenece al día ANTERIOR si su reloj marca más tarde que el de
 * despertar (22:30 -> 05:20 cruza medianoche); si ya es más temprano
 * (00:30 -> 05:20), quedó dentro del mismo día que el despertar.
 */
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

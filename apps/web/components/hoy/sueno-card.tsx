"use client";

import { useEffect, useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useSuenoDeHoy,
  useUpsertSueno,
  type RegistroSueno,
} from "@/lib/api/hooks";

type Props = { fecha: string };

/**
 * Sueño del día (DESIGN.md §2.1, SPEC.md §1, REGLAS_NEGOCIO §6).
 * Dos inputs nativos time + un checkbox + un botón guardar inline.
 * Sin modal: el registro se hace en 30s en la cama, la fricción mata.
 */
export function SuenoCard({ fecha }: Props) {
  const { data, isLoading } = useSuenoDeHoy(fecha);
  const mutacion = useUpsertSueno(fecha);

  // El borrador se inicializa con lo que ya hay. Si el usuario está editando
  // y el servidor responde con datos nuevos, no pisamos su input.
  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const [celular, setCelular] = useState<boolean | null>(null);
  const [editando, setEditando] = useState(false);

  useEffect(() => {
    if (data && !editando) {
      setInicio(toLocalTime(data.inicio));
      setFin(toLocalTime(data.fin));
      setCelular(data.celular_fuera);
    }
  }, [data, editando]);

  const pendiente =
    editando &&
    data !== undefined &&
    (toLocalTime(data.inicio) !== inicio ||
      toLocalTime(data.fin) !== fin ||
      data.celular_fuera !== celular);

  const horas =
    data && validarHoras(inicio, fin)
      ? formatHorasSueno(inicio, fin)
      : data?.horas_sueno ?? null;

  return (
    <BentoCard ancho="half">
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Sueño
        </p>
        {data && (
          <span className="text-[11px] text-text-secondary">
            {new Date(fecha).toLocaleDateString("es-CO", { weekday: "short" })}
          </span>
        )}
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
                  setEditando(true);
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
                  setEditando(true);
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
                setEditando(true);
              }}
              className="h-5 w-5 accent-text-primary"
            />
            <span className="text-[14px] text-text-secondary">Celular fuera</span>
          </label>

          {pendiente && (
            <button
              type="button"
              onClick={async () => {
                await mutacion.mutateAsync({
                  inicio: toIsoLocal(fecha, inicio),
                  fin: toIsoLocal(fecha, fin),
                  celular_fuera: celular,
                });
                setEditando(false);
              }}
              disabled={!validarHoras(inicio, fin) || mutacion.isPending}
              className="mt-5 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
            >
              {mutacion.isPending ? "Guardando..." : "Guardar sueño"}
            </button>
          )}
        </>
      )}
    </BentoCard>
  );
}

// ---------- Helpers locales ----------

function toLocalTime(iso: string): string {
  // `iso` viene como "2026-08-04T12:00:00Z" o con offset. Devuelve "HH:MM" local.
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function toIsoLocal(fecha: string, hora: string): string {
  // "2026-08-04" + "07:00" -> "2026-08-04T07:00:00" sin TZ (interpretado como
  // hora local por el backend al convertirlo).
  return `${fecha}T${hora}:00`;
}

function validarHoras(inicio: string, fin: string): boolean {
  if (!inicio || !fin) return false;
  // En el formulario el usuario no puede poner fin < inicio porque el input
  // time no lo impide a priori. Pero el backend lo rechaza con 422 via el
  // invariante de fecha del despertar. Acá no validamos: dejamos que el
  // backend diga.
  return true;
}

function formatHorasSueno(inicio: string, fin: string): string {
  const [ih = 0, im = 0] = inicio.split(":").map(Number);
  const [fh = 0, fm = 0] = fin.split(":").map(Number);
  let minutos = fh * 60 + fm - (ih * 60 + im);
  if (minutos < 0) minutos += 24 * 60;
  return (minutos / 60).toFixed(1);
}

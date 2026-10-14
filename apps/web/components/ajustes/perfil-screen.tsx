"use client";

import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useGuardarPerfil,
  usePerfil,
  useTiposSesion,
  type EventoFijo,
  type LugarEntreno,
  type PerfilAtletaBase,
  type VentanaDisponible,
} from "@/lib/api/hooks";
import { DIAS, parsearLista, validarPerfil } from "@/lib/perfil";

const INPUT =
  "w-full rounded-xl bg-surface-secondary px-3 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus";
const ETIQUETA = "text-[10px] uppercase tracking-widest text-text-secondary";
const BOTON_SECUNDARIO =
  "inline-flex items-center gap-1.5 rounded-full border border-border-subtle px-3 py-1.5 text-[12px] font-medium text-text-primary";

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className={ETIQUETA}>{etiqueta}</span>
      {children}
    </label>
  );
}

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <BentoCard>
      <p className="mb-4 text-[11px] font-normal uppercase tracking-widest text-text-secondary">{titulo}</p>
      <div className="flex flex-col gap-3">{children}</div>
    </BentoCard>
  );
}

function Quitar({ onClick, etiqueta }: { onClick: () => void; etiqueta: string }) {
  return (
    <button type="button" onClick={onClick} aria-label={etiqueta} className="p-1 text-text-secondary">
      <Trash2 size={14} />
    </button>
  );
}

function mover<T>(lista: T[], i: number, dir: -1 | 1): T[] {
  const j = i + dir;
  if (j < 0 || j >= lista.length) return lista;
  const copia = [...lista];
  [copia[i], copia[j]] = [copia[j]!, copia[i]!];
  return copia;
}

function reemplazar<T>(lista: T[], i: number, valor: T): T[] {
  return lista.map((x, k) => (k === i ? valor : x));
}

export function PerfilScreen() {
  const perfil = usePerfil();
  const tipos = useTiposSesion();
  const guardar = useGuardarPerfil();
  const [form, setForm] = useState<PerfilAtletaBase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardado, setGuardado] = useState(false);

  useEffect(() => {
    if (perfil.data && form === null) {
      const { actualizado_en: _ignorado, ...resto } = perfil.data;
      setForm(resto);
    }
  }, [perfil.data, form]);

  if (perfil.isLoading) return <p className="text-[13px] text-text-secondary">Cargando...</p>;
  if (perfil.isError || !form) {
    return <p className="text-[13px] text-state-danger">No se pudo cargar el perfil.</p>;
  }

  const set = <K extends keyof PerfilAtletaBase>(k: K, v: PerfilAtletaBase[K]) => {
    setGuardado(false);
    setForm({ ...form, [k]: v });
  };

  async function enviar() {
    if (!form) return;
    const invalido = validarPerfil(form);
    setError(invalido);
    if (invalido) return;
    try {
      await guardar.mutateAsync(form);
      setGuardado(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar.");
    }
  }

  const nombresLugares = form.lugares.map((l) => l.nombre).filter(Boolean);

  return (
    <div className="flex flex-col gap-4">
      <Seccion titulo="Básicos">
        <Campo etiqueta="Posición">
          <input className={INPUT} value={form.posicion} onChange={(e) => set("posicion", e.target.value)} />
        </Campo>
        <Campo etiqueta="Pie dominante">
          <input className={INPUT} value={form.pie_dominante} onChange={(e) => set("pie_dominante", e.target.value)} />
        </Campo>
        <Campo etiqueta="Rol táctico">
          <textarea
            className={`${INPUT} min-h-28`}
            value={form.rol_tactico}
            onChange={(e) => set("rol_tactico", e.target.value)}
          />
        </Campo>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Talla (cm)">
            <input
              type="number"
              step="0.1"
              className={INPUT}
              value={form.talla_cm ?? ""}
              onChange={(e) => set("talla_cm", e.target.value === "" ? null : e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Peso declarado (kg)">
            <input
              type="number"
              step="0.1"
              className={INPUT}
              value={form.peso_kg ?? ""}
              onChange={(e) => set("peso_kg", e.target.value === "" ? null : e.target.value)}
            />
          </Campo>
        </div>
      </Seccion>

      <Seccion titulo="Lesiones activas">
        {form.lesiones_activas.length === 0 && (
          <p className="text-[13px] text-text-secondary">Ninguna.</p>
        )}
        {form.lesiones_activas.map((l, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              className={INPUT}
              value={l}
              onChange={(e) => set("lesiones_activas", reemplazar(form.lesiones_activas, i, e.target.value))}
            />
            <Quitar
              etiqueta="Quitar lesión"
              onClick={() => set("lesiones_activas", form.lesiones_activas.filter((_, k) => k !== i))}
            />
          </div>
        ))}
        <button type="button" className={BOTON_SECUNDARIO} onClick={() => set("lesiones_activas", [...form.lesiones_activas, ""])}>
          <Plus size={14} /> Agregar lesión
        </button>
      </Seccion>

      <Seccion titulo="Objetivos (en orden de prioridad)">
        {form.objetivos.map((o, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className="w-5 text-[12px] tabular text-text-secondary">{i + 1}</span>
            <input
              className={INPUT}
              value={o}
              onChange={(e) => set("objetivos", reemplazar(form.objetivos, i, e.target.value))}
            />
            <button type="button" aria-label="Subir" className="p-1 text-text-secondary" onClick={() => set("objetivos", mover(form.objetivos, i, -1))}>
              <ArrowUp size={14} />
            </button>
            <button type="button" aria-label="Bajar" className="p-1 text-text-secondary" onClick={() => set("objetivos", mover(form.objetivos, i, 1))}>
              <ArrowDown size={14} />
            </button>
            <Quitar etiqueta="Quitar objetivo" onClick={() => set("objetivos", form.objetivos.filter((_, k) => k !== i))} />
          </div>
        ))}
        <button type="button" className={BOTON_SECUNDARIO} onClick={() => set("objetivos", [...form.objetivos, ""])}>
          <Plus size={14} /> Agregar objetivo
        </button>
      </Seccion>

      <Seccion titulo="Eventos fijos de la semana">
        {form.eventos_fijos.map((ev, i) => {
          const cambiar = (parcial: Partial<EventoFijo>) =>
            set("eventos_fijos", reemplazar(form.eventos_fijos, i, { ...ev, ...parcial }));
          return (
            <div key={i} className="flex flex-col gap-2 rounded-xl border border-border-subtle p-3">
              <div className="grid grid-cols-2 gap-2">
                <select className={INPUT} value={ev.dia} onChange={(e) => cambiar({ dia: Number(e.target.value) })}>
                  {DIAS.map((d, k) => (
                    <option key={d} value={k}>
                      {d}
                    </option>
                  ))}
                </select>
                <input type="time" className={INPUT} value={ev.hora} onChange={(e) => cambiar({ hora: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select className={INPUT} value={ev.tipo_sesion} onChange={(e) => cambiar({ tipo_sesion: e.target.value })}>
                  {(tipos.data ?? []).map((t) => (
                    <option key={t.codigo} value={t.codigo}>
                      {t.nombre}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="Duración (min)"
                  aria-label="Duración en minutos"
                  className={INPUT}
                  value={ev.duracion_min ?? ""}
                  onChange={(e) => cambiar({ duracion_min: e.target.value === "" ? null : Number(e.target.value) })}
                />
              </div>
              <div className="flex items-center gap-2">
                <input placeholder="Nombre" className={INPUT} value={ev.nombre} onChange={(e) => cambiar({ nombre: e.target.value })} />
                <Quitar etiqueta="Quitar evento" onClick={() => set("eventos_fijos", form.eventos_fijos.filter((_, k) => k !== i))} />
              </div>
            </div>
          );
        })}
        <button
          type="button"
          className={BOTON_SECUNDARIO}
          onClick={() =>
            set("eventos_fijos", [
              ...form.eventos_fijos,
              { dia: 0, hora: "20:00", tipo_sesion: tipos.data?.[0]?.codigo ?? "partido", nombre: "", duracion_min: null },
            ])
          }
        >
          <Plus size={14} /> Agregar evento
        </button>
      </Seccion>

      <Seccion titulo="Lugares y equipamiento">
        {form.lugares.map((l, i) => {
          const cambiar = (parcial: Partial<LugarEntreno>) =>
            set("lugares", reemplazar(form.lugares, i, { ...l, ...parcial }));
          return (
            <div key={i} className="flex flex-col gap-2 rounded-xl border border-border-subtle p-3">
              <div className="flex items-center gap-2">
                <input placeholder="Nombre del lugar" className={INPUT} value={l.nombre} onChange={(e) => cambiar({ nombre: e.target.value })} />
                <Quitar etiqueta="Quitar lugar" onClick={() => set("lugares", form.lugares.filter((_, k) => k !== i))} />
              </div>
              <input
                // Se remonta al agregar/quitar lugares: defaultValue no sigue al
                // estado y, sin esto, un lugar quitado dejaria su texto en otra fila.
                key={`eq-${i}-${form.lugares.length}`}
                placeholder="Equipamiento, separado por comas"
                className={INPUT}
                defaultValue={l.equipamiento.join(", ")}
                onBlur={(e) => cambiar({ equipamiento: parsearLista(e.target.value) })}
              />
            </div>
          );
        })}
        <button type="button" className={BOTON_SECUNDARIO} onClick={() => set("lugares", [...form.lugares, { nombre: "", equipamiento: [] }])}>
          <Plus size={14} /> Agregar lugar
        </button>
      </Seccion>

      <Seccion titulo="Ventanas disponibles (los días sin ventana son descanso)">
        {form.ventanas.map((v, i) => {
          const cambiar = (parcial: Partial<VentanaDisponible>) =>
            set("ventanas", reemplazar(form.ventanas, i, { ...v, ...parcial }));
          return (
            <div key={i} className="flex flex-col gap-2 rounded-xl border border-border-subtle p-3">
              <select className={INPUT} value={v.dia} onChange={(e) => cambiar({ dia: Number(e.target.value) })}>
                {DIAS.map((d, k) => (
                  <option key={d} value={k}>
                    {d}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <Campo etiqueta="Inicio">
                  <input type="time" className={INPUT} value={v.inicio} onChange={(e) => cambiar({ inicio: e.target.value })} />
                </Campo>
                <Campo etiqueta="Fin">
                  <input type="time" className={INPUT} value={v.fin} onChange={(e) => cambiar({ fin: e.target.value })} />
                </Campo>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {nombresLugares.map((n) => {
                  const activo = v.lugares.includes(n);
                  return (
                    <button
                      key={n}
                      type="button"
                      aria-pressed={activo}
                      onClick={() => cambiar({ lugares: activo ? v.lugares.filter((x) => x !== n) : [...v.lugares, n] })}
                      className={`rounded-full px-3 py-1 text-[12px] ${
                        activo ? "bg-text-primary text-canvas" : "bg-surface-secondary text-text-secondary"
                      }`}
                    >
                      {n}
                    </button>
                  );
                })}
                <Quitar etiqueta="Quitar ventana" onClick={() => set("ventanas", form.ventanas.filter((_, k) => k !== i))} />
              </div>
            </div>
          );
        })}
        <button
          type="button"
          className={BOTON_SECUNDARIO}
          onClick={() => set("ventanas", [...form.ventanas, { dia: 0, inicio: "09:00", fin: "10:00", lugares: [] }])}
        >
          <Plus size={14} /> Agregar ventana
        </button>
      </Seccion>

      {error && <p className="text-[13px] text-state-danger">{error}</p>}
      {guardado && <p className="text-[13px] text-state-positive">Perfil guardado.</p>}
      <button
        type="button"
        disabled={guardar.isPending}
        onClick={enviar}
        className="w-full rounded-pill bg-text-primary py-3 text-[14px] font-semibold text-canvas disabled:opacity-50"
      >
        {guardar.isPending ? "Guardando..." : "Guardar perfil"}
      </button>
    </div>
  );
}

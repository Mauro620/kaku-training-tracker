"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";

import { BentoCard } from "@/components/ui/bento-card";
import { PillSelectorGroup } from "@/components/ui/pill-selector-group";
import {
  useAlimentos,
  useRecetas,
  useRegistrarComida,
  type MomentoComida,
} from "@/lib/api/hooks";

type Props = { fecha: string };

const MOMENTOS: MomentoComida[] = [
  "desayuno",
  "media_manana",
  "almuerzo",
  "merienda",
  "cena",
];

const ETIQUETA_MOMENTO: Record<MomentoComida, string> = {
  desayuno: "Desayuno",
  media_manana: "Media manana",
  almuerzo: "Almuerzo",
  merienda: "Merienda",
  cena: "Cena",
};

type Modo = "receta" | "items";

/**
 * Formulario de registro de comida (Fase 6, ROADMAP §6).
 *
 * El usuario elige un momento, despues si la comida es con receta o
 * improvisada. El server exige XOR (receta_id xor items); este
 * formulario ya lo garantiza por estructura.
 *
 * Va a la cola offline-first: aunque el server pueda responder sin red
 * (sesion), el dato pasa por `encolar` igual que las otras 6 mutaciones.
 */
export function RegistrarComida({ fecha }: Props) {
  const [momento, setMomento] = useState<MomentoComida>("almuerzo");
  const [modo, setModo] = useState<Modo>("receta");
  const [recetaId, setRecetaId] = useState<string>("");
  const [items, setItems] = useState<{ alimento_id: string; cantidad_g: string }[]>([
    { alimento_id: "", cantidad_g: "" },
  ]);
  const [nota, setNota] = useState("");

  const recetas = useRecetas();
  const alimentos = useAlimentos();
  const registrar = useRegistrarComida(fecha);

  function reset() {
    setMomento("almuerzo");
    setModo("receta");
    setRecetaId("");
    setItems([{ alimento_id: "", cantidad_g: "" }]);
    setNota("");
  }

  function enviar() {
    if (modo === "receta") {
      const rid = Number(recetaId);
      if (!Number.isFinite(rid) || rid <= 0) return;
      registrar.mutate(
        {
          momento,
          receta_id: rid,
          nota: nota || null,
          items: [],
        },
        { onSuccess: reset },
      );
      return;
    }

    // modo === "items": al menos un item valido
    const itemsValidos = items
      .map((it) => ({
        alimento_id: Number(it.alimento_id),
        cantidad_g: Number(it.cantidad_g),
      }))
      .filter(
        (it) =>
          Number.isFinite(it.alimento_id) &&
          it.alimento_id > 0 &&
          Number.isFinite(it.cantidad_g) &&
          it.cantidad_g > 0,
      );
    if (itemsValidos.length === 0) return;

    registrar.mutate(
      {
        momento,
        receta_id: null,
        nota: nota || null,
        items: itemsValidos,
      },
      { onSuccess: reset },
    );
  }

  return (
    <BentoCard>
      <header className="mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Registrar comida
        </p>
      </header>

      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <label className="text-[11px] tracking-widest uppercase text-text-secondary">
            Momento
          </label>
          <PillSelectorGroup<MomentoComida>
            opciones={MOMENTOS.map((m) => ({
              valor: m,
              etiqueta: ETIQUETA_MOMENTO[m],
            }))}
            valor={momento}
            onChange={setMomento}
            label="Momento de la comida"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[11px] tracking-widest uppercase text-text-secondary">
            Como
          </label>
          <PillSelectorGroup<Modo>
            opciones={[
              { valor: "receta", etiqueta: "Con receta" },
              { valor: "items", etiqueta: "Improvisada" },
            ]}
            valor={modo}
            onChange={setModo}
            label="Con receta o improvisada"
          />
        </div>

        {modo === "receta" ? (
          <div className="flex flex-col gap-2">
            <label className="text-[11px] tracking-widest uppercase text-text-secondary">
              Receta
            </label>
            <select
              value={recetaId}
              onChange={(e) => setRecetaId(e.target.value)}
              className="rounded-lg bg-surface-secondary px-3 py-3 text-[14px] text-text-primary"
            >
              <option value="">Elegir...</option>
              {(recetas.data ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.nombre}
                  {r.momento_default ? ` (${ETIQUETA_MOMENTO[r.momento_default]})` : ""}
                </option>
              ))}
            </select>
            {recetas.data && recetas.data.length === 0 && (
              <p className="text-[12px] text-text-secondary">
                No tenes recetas todavia. Crea una en la biblioteca de abajo.
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] tracking-widest uppercase text-text-secondary">
                Ingredientes
              </label>
              <span className="text-[11px] text-text-secondary">
                Cantidad en gramos. Ej: 1 huevo ≈ 50 g, 1 taza de avena ≈ 80 g,
                1 banano ≈ 120 g.
              </span>
            </div>
            {items.map((it, idx) => {
              const cantidadNum = Number(it.cantidad_g);
              const sinAlimento = !it.alimento_id;
              const advertencia = !sinAlimento
                && Number.isFinite(cantidadNum)
                && cantidadNum > 0
                && cantidadNum < 5;
              return (
                <div key={idx} className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <select
                      value={it.alimento_id}
                      onChange={(e) => {
                        const copia = [...items];
                        const actual = copia[idx];
                        if (actual) {
                          copia[idx] = { alimento_id: e.target.value, cantidad_g: actual.cantidad_g };
                        }
                        setItems(copia);
                      }}
                      className="flex-1 rounded-lg bg-surface-secondary px-3 py-3 text-[14px] text-text-primary"
                    >
                      <option value="">Elegir alimento...</option>
                      {(alimentos.data ?? []).map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.nombre}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      inputMode="numeric"
                      placeholder="ej. 100"
                      value={it.cantidad_g}
                      onChange={(e) => {
                        const copia = [...items];
                        const actual = copia[idx];
                        if (actual) {
                          copia[idx] = { alimento_id: actual.alimento_id, cantidad_g: e.target.value };
                        }
                        setItems(copia);
                      }}
                      className="w-20 rounded-lg bg-surface-secondary px-3 py-3 text-[14px] text-text-primary tabular"
                    />
                    {items.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setItems(items.filter((_, i) => i !== idx))}
                        aria-label="Quitar item"
                        className="shrink-0 rounded p-2 text-text-secondary hover:text-state-danger"
                      >
                        <X size={16} aria-hidden />
                      </button>
                    )}
                  </div>
                  {advertencia && (
                    <span className="pl-1 text-[11px] text-state-warning">
                      {cantidadNum} g es muy poco para un alimento entero.
                      Confirmá que es la cantidad real.
                    </span>
                  )}
                </div>
              );
            })}
            <button
              type="button"
              onClick={() =>
                setItems([...items, { alimento_id: "", cantidad_g: "" }])
              }
              className="flex items-center justify-center gap-2 rounded-lg bg-surface-secondary px-3 py-2 text-[13px] font-medium text-text-secondary hover:text-text-primary"
            >
              <Plus size={14} aria-hidden />
              Sumar ingrediente
            </button>
          </div>
        )}

        <div className="flex flex-col gap-2">
          <label className="text-[11px] tracking-widest uppercase text-text-secondary">
            Nota (opcional)
          </label>
          <input
            type="text"
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder="Ej: con el profe despues del entreno"
            className="rounded-lg bg-surface-secondary px-3 py-3 text-[14px] text-text-primary placeholder:text-text-secondary"
          />
        </div>

        <button
          type="button"
          onClick={enviar}
          disabled={registrar.isPending}
          className="self-start rounded-pill bg-text-primary px-6 py-3 text-[14px] font-bold text-canvas disabled:opacity-50"
        >
          {registrar.isPending ? "Registrando..." : "Registrar"}
        </button>
      </div>
    </BentoCard>
  );
}
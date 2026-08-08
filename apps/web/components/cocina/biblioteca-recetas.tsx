"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { BentoCard } from "@/components/ui/bento-card";
import { PillSelectorGroup } from "@/components/ui/pill-selector-group";
import {
  useAlimentos,
  useCrearReceta,
  useEliminarReceta,
  useRecetas,
  type MomentoComida,
} from "@/lib/api/hooks";

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

type ItemBorrador = { alimento_id: string; cantidad_g: string };

/**
 * Biblioteca de recetas del usuario (Fase 6, ROADMAP §6).
 *
 * Mostrar la lista + un toggle para crear una nueva sin salir de la
 * pantalla. La creacion NO va a la cola (es setup, no registro diario):
 * se hace con red, y si falla es 4xx y el form muestra el error.
 */
export function BibliotecaRecetas() {
  const recetas = useRecetas();
  const alimentos = useAlimentos();
  const crear = useCrearReceta();
  const eliminar = useEliminarReceta();

  const [mostrarForm, setMostrarForm] = useState(false);
  const [nombre, setNombre] = useState("");
  const [momentoDefault, setMomentoDefault] = useState<MomentoComida | null>(null);
  const [items, setItems] = useState<ItemBorrador[]>([
    { alimento_id: "", cantidad_g: "" },
  ]);

  function resetForm() {
    setNombre("");
    setMomentoDefault(null);
    setItems([{ alimento_id: "", cantidad_g: "" }]);
    setMostrarForm(false);
  }

  function enviar() {
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
    if (!nombre.trim() || itemsValidos.length === 0) return;
    crear.mutate(
      { nombre: nombre.trim(), momento_default: momentoDefault, items: itemsValidos },
      { onSuccess: resetForm },
    );
  }

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Biblioteca de recetas
        </p>
        <button
          type="button"
          onClick={() => setMostrarForm((v) => !v)}
          className="flex items-center gap-1 rounded-pill bg-surface-secondary px-3 py-1.5 text-[12px] font-semibold text-text-primary"
        >
          <Plus size={14} aria-hidden />
          Nueva
        </button>
      </header>

      {mostrarForm && (
        <div className="mb-4 flex flex-col gap-4 rounded-lg bg-surface-secondary p-4">
          <input
            type="text"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Nombre de la receta"
            className="rounded-lg bg-canvas px-3 py-3 text-[14px] text-text-primary placeholder:text-text-secondary"
          />
          <div className="flex flex-col gap-2">
            <label className="text-[11px] tracking-widest uppercase text-text-secondary">
              Momento por defecto
            </label>
            <PillSelectorGroup<MomentoComida | "ninguno">
              opciones={[
                { valor: "ninguno", etiqueta: "Ninguno" },
                ...MOMENTOS.map((m) => ({
                  valor: m,
                  etiqueta: ETIQUETA_MOMENTO[m],
                })),
              ]}
              valor={momentoDefault ?? "ninguno"}
              onChange={(v) =>
                setMomentoDefault(v === "ninguno" ? null : v)
              }
              label="Momento por defecto de la receta"
            />
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] tracking-widest uppercase text-text-secondary">
                Ingredientes
              </label>
              <span className="text-[11px] text-text-secondary">
                Cantidad en gramos.
              </span>
            </div>
            {items.map((it, idx) => (
              <div key={idx} className="flex items-center gap-2">
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
                  className="flex-1 rounded-lg bg-canvas px-3 py-2 text-[14px] text-text-primary"
                >
                  <option value="">Elegir...</option>
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
                  className="w-20 rounded-lg bg-canvas px-3 py-2 text-[14px] text-text-primary tabular"
                />
              </div>
            ))}
            <button
              type="button"
              onClick={() =>
                setItems([...items, { alimento_id: "", cantidad_g: "" }])
              }
              className="flex items-center justify-center gap-2 rounded-lg bg-canvas px-3 py-2 text-[13px] font-medium text-text-secondary"
            >
              <Plus size={14} aria-hidden />
              Sumar ingrediente
            </button>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={enviar}
              disabled={crear.isPending}
              className="rounded-pill bg-text-primary px-5 py-2.5 text-[13px] font-bold text-canvas disabled:opacity-50"
            >
              {crear.isPending ? "Guardando..." : "Guardar receta"}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="rounded-pill bg-canvas px-5 py-2.5 text-[13px] font-medium text-text-secondary"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {recetas.isLoading ? (
        <div className="h-20" />
      ) : (recetas.data ?? []).length === 0 ? (
        <p className="text-[13px] text-text-secondary">
          Aun no hay recetas. Las que crees aparecen aca para usarlas en el
          registro de comidas.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {(recetas.data ?? []).map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between gap-3 rounded-lg bg-surface-secondary px-3 py-2"
            >
              <div className="flex flex-col">
                <span className="text-[13px] font-semibold text-text-primary">
                  {r.nombre}
                </span>
                <span className="text-[11px] text-text-secondary">
                  {r.items.length} {r.items.length === 1 ? "item" : "items"}
                  {r.momento_default ? ` · ${ETIQUETA_MOMENTO[r.momento_default]}` : ""}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`Eliminar la receta "${r.nombre}"?`)) {
                    eliminar.mutate(r.id);
                  }
                }}
                disabled={eliminar.isPending}
                aria-label={`Eliminar ${r.nombre}`}
                className="shrink-0 rounded p-1 text-text-secondary hover:bg-canvas hover:text-state-danger disabled:opacity-50"
              >
                <Trash2 size={16} aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </BentoCard>
  );
}
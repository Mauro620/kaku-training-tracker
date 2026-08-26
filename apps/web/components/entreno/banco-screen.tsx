"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search } from "lucide-react";

import {
  useEjerciciosList,
  useCrearEjercicio,
  type TipoMedicion,
} from "@/lib/api/hooks";
import { formatearFechaLarga } from "@/lib/fecha";
import { EmptyState } from "@/components/ui/empty-state";
import { DetalleEjercicioSheet } from "./detalle-ejercicio-sheet";
import { FusionEjercicioDialog } from "./fusion-ejercicio-dialog";

const TIPOS_MEDICION: TipoMedicion[] = ["carga", "distancia", "tiempo", "tecnica"];

/**
 * BancoScreen: lista de ejercicios con busqueda, filtros y empty states.
 * - Buscador con debounce 300 ms
 * - Filtros multi-select por tipo_medicion (chips)
 * - Switch "Archivados" para toggle activo/false
 * - Lista de rows con nombre, tipo, usos y ultima_vez
 * - Empty states: sin ejercicios, sin resultados de busqueda
 * - Sheet de detalle al tocar una fila
 * - Dialog de fusion
 */
export function BancoScreen() {
  const router = useRouter();

  // Estado de filtros
  const [q, setQ] = useState("");
  const [qDebounce, setQDebounce] = useState("");
  const [tiposSeleccionados, setTiposSeleccionados] = useState<TipoMedicion[]>([]);
  const [mostrarArchivados, setMostrarArchivados] = useState(false);

  // Estado para sheet y dialog
  const [ejercicioSeleccionadoId, setEjercicioSeleccionadoId] = useState<number | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [fusionOpen, setFusionOpen] = useState(false);
  const [fusionOrigenId, setFusionOrigenId] = useState<number | null>(null);
  const [fusionDestinoId, setFusionDestinoId] = useState<number | null>(null);

  // Debounce 300 ms para la busqueda
  useEffect(() => {
    const timer = setTimeout(() => {
      setQDebounce(q);
    }, 300);
    return () => clearTimeout(timer);
  }, [q]);

  // Hook de lista de ejercicios
  const { data, isLoading } = useEjerciciosList(
    qDebounce || null,
    tiposSeleccionados.length > 0 ? tiposSeleccionados[0] : null,
    mostrarArchivados ? undefined : true, // si false, muestra solo activos; si undefined, muestra todos
    undefined,
  );

  const { data: crearData, mutate: crear } = useCrearEjercicio();

  // Handlers
  const toggleTipoMedicion = (tipo: TipoMedicion) => {
    setTiposSeleccionados((prev) =>
      prev.includes(tipo)
        ? prev.filter((t) => t !== tipo)
        : [...prev, tipo],
    );
  };

  const handleCrearDesdeBusqueda = () => {
    if (!qDebounce.trim()) return;
    crear(
      { nombre: qDebounce.trim(), tipo_medicion: "carga" },
      {
        onSuccess: () => {
          setQ("");
          setQDebounce("");
        },
      },
    );
  };

  const handleAbrirDetalle = (id: number) => {
    setEjercicioSeleccionadoId(id);
    setSheetOpen(true);
  };

  const handleFusionarClick = (origenId: number) => {
    setFusionOrigenId(origenId);
    setFusionDestinoId(null);
    setSheetOpen(false);
    setFusionOpen(true);
  };

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="animate-pulse rounded-2xl border border-border-subtle bg-surface-primary p-4"
          >
            <div className="mb-2 h-4 w-2/3 rounded bg-surface-secondary" />
            <div className="h-3 w-1/3 rounded bg-surface-secondary" />
          </div>
        ))}
      </div>
    );
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hayFiltros = qDebounce.trim() || tiposSeleccionados.length > 0 || mostrarArchivados;

  // Empty state: sin ejercicios
  if (total === 0 && !hayFiltros) {
    return (
      <EmptyState
        icon={<Plus className="h-8 w-8" />}
        title="Aun no hay ejercicios"
        description="Los ejercicios llegan cuando importas un plan semanal"
        action={{
          label: "Importar plan",
          onClick: () => router.push("/entreno/importar"),
        }}
      />
    );
  }

  // Empty state: sin resultados de busqueda
  if (items.length === 0 && qDebounce.trim()) {
    return (
      <EmptyState
        title={`Sin resultados para "${qDebounce.trim()}"`}
        action={{
          label: `Crear "${qDebounce.trim()}"`,
          onClick: handleCrearDesdeBusqueda,
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Buscador */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-secondary" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar ejercicio..."
          className="w-full rounded-2xl border border-border-subtle bg-surface-primary py-3 pl-11 pr-4 text-[14px] text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent"
        />
      </div>

      {/* Filtros de tipo_medicion (chips multi-select) */}
      <div className="flex flex-wrap gap-2">
        {TIPOS_MEDICION.map((tipo) => {
          const activo = tiposSeleccionados.includes(tipo);
          return (
            <button
              key={tipo}
              type="button"
              onClick={() => toggleTipoMedicion(tipo)}
              className={`min-h-[40px] rounded-pill px-4 text-[14px] font-medium transition ${
                activo
                  ? "bg-text-primary text-canvas font-semibold"
                  : "bg-surface-secondary text-text-secondary"
              }`}
            >
              {tipo}
            </button>
          );
        })}
      </div>

      {/* Switch Archivados */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setMostrarArchivados(!mostrarArchivados)}
          className={`relative h-6 w-11 rounded-full transition ${
            mostrarArchivados ? "bg-accent" : "bg-surface-secondary"
          }`}
          role="switch"
          aria-checked={mostrarArchivados}
        >
          <span
            className={`absolute top-1/2 -translate-y-1/2 h-4 w-4 rounded-full bg-bg transition ${
              mostrarArchivados ? "left-6" : "left-1"
            }`}
          />
        </button>
        <span className="text-[13px] text-text-secondary">Archivados</span>
      </div>

      {/* Header con contador */}
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-text-primary">Ejercicios</h2>
        <span className="text-[13px] text-text-secondary">
          {total} {total === 1 ? "activo" : "activos"}
        </span>
      </div>

      {/* Lista de ejercicios */}
      <ul className="space-y-2">
        {items.map((ejercicio) => (
          <li key={ejercicio.id}>
            <button
              type="button"
              onClick={() => handleAbrirDetalle(ejercicio.id)}
              className={`w-full rounded-2xl border border-border-subtle bg-surface-primary p-4 text-left transition hover:bg-surface-secondary ${
                ejercicio.usos === 0 ? "opacity-60" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-text-primary">
                  {ejercicio.nombre}
                </span>
                <span className="rounded-full bg-surface-secondary px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-text-secondary">
                  {ejercicio.tipo_medicion}
                </span>
              </div>
              <div className="mt-1 text-[13px] text-text-secondary">
                {ejercicio.usos === 0 ? (
                  <span>sin usar</span>
                ) : (
                  <span>
                    {ejercicio.usos} {ejercicio.usos === 1 ? "uso" : "usos"} · ultima{" "}
                    {ejercicio.ultima_vez ? formatearFechaLarga(ejercicio.ultima_vez) : "N/A"}
                  </span>
                )}
              </div>
            </button>
          </li>
        ))}
      </ul>

      {/* Sheet de detalle */}
      <DetalleEjercicioSheet
        ejercicioId={ejercicioSeleccionadoId}
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onFusionarClick={handleFusionarClick}
      />

      {/* Dialog de fusion */}
      <FusionEjercicioDialog
        origenId={fusionOrigenId}
        destinoIdPreseleccionado={fusionDestinoId}
        open={fusionOpen}
        onClose={() => setFusionOpen(false)}
        onConfirm={async (_destinoId: number) => {
          setFusionOpen(false);
          setFusionOrigenId(null);
          setFusionDestinoId(null);
        }}
      />
    </div>
  );
}

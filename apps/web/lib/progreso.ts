import type { Semaforo } from "@/lib/api/hooks";

// Logica pura de las tarjetas de Progreso (sin JSX, para poder testearla).

// Semaforo del ACWR (REGLAS_NEGOCIO §18.3). El color nunca va solo: cada nivel
// lleva su etiqueta textual.
export const SEMAFORO: Record<Semaforo, { color: string; etiqueta: string; rango: string }> = {
  baja: { color: "#86EFAC", etiqueta: "Baja", rango: "menos de 0,8" },
  verde: { color: "#22C55E", etiqueta: "Segura", rango: "0,8 a 1,3" },
  amarillo: { color: "#EAB308", etiqueta: "Alta", rango: "1,3 a 1,5" },
  rojo: { color: "#EF4444", etiqueta: "Muy alta", rango: "más de 1,5" },
};

// Estados del plan. Verde / azul / gris / hueco: se distinguen tambien por
// forma (el pendiente es un contorno) y por la etiqueta de la leyenda.
export const ESTADOS_PLAN = [
  { clave: "cumplido", etiqueta: "Cumplidas", color: "#22C55E" },
  { clave: "movido", etiqueta: "Movidas", color: "#60A5FA" },
  { clave: "descartado", etiqueta: "Descartadas", color: "#71717A" },
  { clave: "pendiente", etiqueta: "Pendientes", color: "transparent" },
] as const;

export function formatoNumero(n: number, decimales = 1): string {
  const texto = n.toFixed(decimales);
  // Solo se recortan ceros DECIMALES: "50" no puede quedar en "5".
  return (texto.includes(".") ? texto.replace(/\.?0+$/, "") : texto).replace(".", ",");
}

const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

// "2026-09-21" -> "21 sep"
export function etiquetaFecha(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${Number(d)} ${MESES_CORTOS[Number(m) - 1] ?? ""}`;
}

export type Punto = { x: number; y: number };

// Escala una serie a un area ancho x alto con margen. `invertir` pone el
// mayor arriba (coordenadas SVG crecen hacia abajo). Una serie constante o de
// un solo punto se dibuja a media altura: no hay rango que estirar.
export function escalarSerie(
  valores: number[],
  ancho: number,
  alto: number,
  margen = 6,
  dominio?: [number, number],
): Punto[] {
  if (valores.length === 0) return [];
  const [min, max] = dominio ?? [Math.min(...valores), Math.max(...valores)];
  const rango = max - min;
  const util = { ancho: ancho - 2 * margen, alto: alto - 2 * margen };
  return valores.map((v, i) => ({
    x: margen + (valores.length === 1 ? util.ancho / 2 : (util.ancho * i) / (valores.length - 1)),
    y: margen + (rango === 0 ? util.alto / 2 : util.alto * (1 - (v - min) / rango)),
  }));
}

export function rutaLinea(puntos: Punto[]): string {
  return puntos.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}

// Altura de cada barra como fraccion (0..1) del maximo; todo en cero -> 0.
export function alturasRelativas(valores: number[]): number[] {
  const max = Math.max(0, ...valores);
  return valores.map((v) => (max === 0 ? 0 : v / max));
}

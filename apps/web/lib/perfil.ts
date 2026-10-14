import type { PerfilAtletaBase } from "@/lib/api/hooks";

// Logica pura del formulario de perfil. Vive fuera del .tsx por la misma razon
// que lib/importar-plan.ts: apps/web no tiene jsdom y vitest no transforma JSX.

export const DIAS = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
] as const;

const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;

// Validacion local de lo barato, para mostrar el error junto al formulario sin
// ida y vuelta. El backend sigue siendo la fuente de verdad.
export function validarPerfil(p: PerfilAtletaBase): string | null {
  if (!p.posicion.trim()) return "La posición es obligatoria.";
  if (!p.pie_dominante.trim()) return "El pie dominante es obligatorio.";
  if (!p.rol_tactico.trim()) return "El rol táctico es obligatorio.";
  if (p.talla_cm !== null && !(Number(p.talla_cm) > 0)) return "La talla debe ser mayor que 0.";
  if (p.peso_kg !== null && !(Number(p.peso_kg) > 0)) return "El peso debe ser mayor que 0.";

  const nombres = p.lugares.map((l) => l.nombre.trim());
  if (nombres.some((n) => !n)) return "Todos los lugares necesitan nombre.";
  if (new Set(nombres).size !== nombres.length) return "Hay lugares repetidos.";

  for (const e of p.eventos_fijos) {
    if (!HORA.test(e.hora)) return `Evento fijo "${e.nombre}": hora inválida (HH:MM).`;
    if (!e.nombre.trim()) return "Todos los eventos fijos necesitan nombre.";
  }
  for (const v of p.ventanas) {
    const dia = DIAS[v.dia] ?? String(v.dia);
    if (!HORA.test(v.inicio) || !HORA.test(v.fin)) return `Ventana del ${dia}: hora inválida.`;
    if (v.inicio >= v.fin) return `Ventana del ${dia}: el inicio debe ser anterior al fin.`;
    if (v.lugares.length === 0) return `Ventana del ${dia}: elige al menos un lugar.`;
    const desconocidos = v.lugares.filter((l) => !nombres.includes(l));
    if (desconocidos.length) return `Ventana del ${dia}: lugar no declarado (${desconocidos.join(", ")}).`;
  }
  return null;
}

// Equipamiento se edita como texto separado por comas.
export function parsearLista(texto: string): string[] {
  return texto
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

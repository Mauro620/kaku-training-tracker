import { useParametro } from "@/lib/api/hooks";

const HORA_CORTE_DEFAULT = 4;

/**
 * La fecha de "hoy" para efectos de registro no es la fecha de calendario:
 * antes de `dia_registro_hora_corte` (parametro, default 4am) el día
 * sigue siendo el de ayer. Alguien que se acuesta a la 1am no debería ver
 * la pantalla Hoy en blanco antes de dormir; a las 4am+ ya es un día nuevo.
 */
export function useFechaDeRegistro(): string {
  const { data } = useParametro("dia_registro_hora_corte");
  const horaCorte = data ? Number(data.valor) : HORA_CORTE_DEFAULT;
  return calcularFechaDeRegistro(new Date(), horaCorte);
}

export function calcularFechaDeRegistro(ahora: Date, horaCorte: number): string {
  const d = new Date(ahora);
  if (d.getHours() < horaCorte) d.setDate(d.getDate() - 1);
  return formatFechaLocal(d);
}

function formatFechaLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

/**
 * Formatea una fecha YYYY-MM-DD a formato largo en español:
 * "Miércoles 26 de agosto"
 * Usa la hora local del sistema para evitar drift de TZ.
 */
export function formatearFechaLarga(iso: string): string {
  // Agregamos T00:00:00 para evitar que el parseo UTC nos mueva el día
  const d = new Date(iso + "T00:00:00");
  const diaSemana = DIAS[d.getDay()];
  const diaMes = d.getDate();
  const mes = MESES[d.getMonth()];
  return `${diaSemana} ${diaMes} de ${mes}`;
}

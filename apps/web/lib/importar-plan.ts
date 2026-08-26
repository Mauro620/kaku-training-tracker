import type { ExportRead } from "@/lib/api/hooks";
import type { PlanSemanalImport, TipoMedicion } from "@/lib/api/hooks";

// Logica pura de la pantalla de importacion de plan (Fase 4 R4 +
// llm-export-endpoints). Vive fuera de importar-plan-screen.tsx a proposito:
// apps/web no tiene jsdom/@testing-library/react y vitest.config.ts no
// puede transformar JSX de archivos .tsx fuera del pipeline de Next
// (tsconfig usa `jsx: "preserve"`, pensado para el compilador de Next, y
// vite/esbuild lo rechaza al importar un .tsx directo en un test). Sacando
// esta logica a un .ts se puede testear sin tocar vitest.config.ts ni
// agregar jsdom/RTL como dependencias nuevas.

export const VERSION_SOPORTADA = 2;
export const TIPOS_SESION_VALIDOS = [
  "fuerza",
  "velocidad_salto",
  "resistencia",
  "balon_control",
  "balon_distribucion",
  "recuperacion",
  "partido",
  "activacion",
] as const;
export const FASES_VALIDAS = ["readaptacion", "carga", "descarga"] as const;
export const TIPOS_MEDICION_VALIDOS: readonly TipoMedicion[] = [
  "carga",
  "distancia",
  "tiempo",
  "tecnica",
];

export type ErrorLocal = string | null;

// Validacion local solo de "lo barato": version, tipos enumerados, forma.
// El server es la fuente de verdad; duplicar cada regla de pydantic seria
// deuda sin valor.
export function validarForma(texto: string): { payload: PlanSemanalImport | null; error: ErrorLocal } {
  if (!texto.trim()) {
    return { payload: null, error: "Pega un JSON para empezar." };
  }
  let crudo: unknown;
  try {
    crudo = JSON.parse(texto);
  } catch (e) {
    return { payload: null, error: `JSON invalido: ${(e as Error).message}` };
  }
  if (!crudo || typeof crudo !== "object") {
    return { payload: null, error: "El JSON tiene que ser un objeto." };
  }
  const obj = crudo as Record<string, unknown>;

  if (obj.version !== VERSION_SOPORTADA) {
    return {
      payload: null,
      error: `version ${String(obj.version)} no soportada (esperada: ${VERSION_SOPORTADA})`,
    };
  }
  if (!obj.ciclo || !obj.semana || !Array.isArray(obj.sesiones)) {
    return {
      payload: null,
      error: "Faltan campos requeridos: ciclo, semana, sesiones.",
    };
  }
  const sesiones = obj.sesiones as Array<Record<string, unknown>>;
  for (let i = 0; i < sesiones.length; i++) {
    const s = sesiones[i];
    if (!s) continue;
    if (!TIPOS_SESION_VALIDOS.includes(s.tipo as (typeof TIPOS_SESION_VALIDOS)[number])) {
      return {
        payload: null,
        error: `Sesion ${i + 1}: tipo "${String(s.tipo)}" no esta en el catalogo.`,
      };
    }
    if (typeof s.dia !== "number" || s.dia < 0 || s.dia > 6) {
      return { payload: null, error: `Sesion ${i + 1}: dia debe ser un entero 0-6.` };
    }
    const bloques = (s.bloques as Array<Record<string, unknown>>) ?? [];
    for (let j = 0; j < bloques.length; j++) {
      const b = bloques[j];
      if (!b) continue;
      if (!TIPOS_MEDICION_VALIDOS.includes(b.tipo_medicion as TipoMedicion)) {
        return {
          payload: null,
          error: `Bloque ${j + 1} de sesion ${i + 1}: tipo_medicion invalido.`,
        };
      }
    }
  }
  return { payload: obj as unknown as PlanSemanalImport, error: null };
}

// ---------- llm-export-endpoints: boton "Copiar los 3 para el LLM" ----------

// Une los 3 ExportRead en un solo bloque de texto, con un encabezado "## "
// por recurso que sirve de delimitador. Pura: mismo input, mismo output.
export function armarBloqueParaCopiar(exports: ExportRead[]): string {
  return exports.map((e) => `## ${e.recurso}\n\n${e.contenido}`).join("\n\n");
}

export type CopiarParaLLMDeps = {
  obtenerExports: () => Promise<ExportRead[]>;
  clipboard: Pick<Clipboard, "writeText">;
};

// Orquesta fetch + armado + escritura al portapapeles. Nunca deja una copia
// parcial: si cualquier paso falla (un export cae, el portapapeles esta
// bloqueado por contexto inseguro o permiso denegado), no escribe nada y
// devuelve "error" sin dejar una excepcion sin manejar.
export async function copiarParaLLM(deps: CopiarParaLLMDeps): Promise<"ok" | "error"> {
  try {
    const exports = await deps.obtenerExports();
    const bloque = armarBloqueParaCopiar(exports);
    await deps.clipboard.writeText(bloque);
    return "ok";
  } catch {
    return "error";
  }
}

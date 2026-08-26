import { describe, expect, it, vi } from "vitest";

import type { ExportRead } from "@/lib/api/hooks";
import { armarBloqueParaCopiar, copiarParaLLM, validarForma } from "@/lib/importar-plan";

// Logica pura extraida de importar-plan-screen.tsx (ver comentario en
// lib/importar-plan.ts): apps/web no tiene jsdom/@testing-library/react y
// vitest no puede transformar JSX de un .tsx importado directo (tsconfig
// usa `jsx: "preserve"`, pensado para el compilador de Next). Se testea la
// logica sin renderizar nada, en vez de agregar jsdom/RTL como dependencias
// nuevas.

describe("validarForma", () => {
  it("acepta un plan version 2 con una sesion de tipo activacion", () => {
    const texto = JSON.stringify({
      version: 2,
      ciclo: { numero: 1, objetivo: "pretemporada", fecha_inicio: "2026-01-05", semanas: 4 },
      semana: { numero: 1, fase: "readaptacion", rpe_objetivo: null, volumen_pct: 100 },
      sesiones: [
        {
          dia: 0,
          tipo: "activacion",
          objetivo: null,
          duracion_min: 20,
          rpe_objetivo: null,
          bloques: [],
        },
      ],
    });

    const { payload, error } = validarForma(texto);

    expect(error).toBeNull();
    expect(payload?.sesiones[0]?.tipo).toBe("activacion");
  });

  it("rechaza una version distinta de 2 con un mensaje de version no soportada", () => {
    const texto = JSON.stringify({
      version: 1,
      ciclo: { numero: 1, objetivo: "x", fecha_inicio: "2026-01-05", semanas: 4 },
      semana: { numero: 1, fase: "readaptacion", rpe_objetivo: null, volumen_pct: 100 },
      sesiones: [],
    });

    const { payload, error } = validarForma(texto);

    expect(payload).toBeNull();
    expect(error).toContain("no soportada");
  });
});

const EXPORT_EJERCICIOS: ExportRead = {
  recurso: "ejercicios",
  formato: "json",
  contenido: '[{"nombre":"Sentadilla"}]',
};
const EXPORT_REGLAS: ExportRead = {
  recurso: "reglas",
  formato: "markdown",
  contenido: "# Reglas de importacion",
};
const EXPORT_EJEMPLO: ExportRead = {
  recurso: "ejemplo",
  formato: "json",
  contenido: '{"version":2}',
};

describe("armarBloqueParaCopiar", () => {
  it("junta los 3 contenidos en un solo bloque con delimitadores que identifican cada recurso", () => {
    const bloque = armarBloqueParaCopiar([EXPORT_EJERCICIOS, EXPORT_REGLAS, EXPORT_EJEMPLO]);

    expect(bloque).toContain("ejercicios");
    expect(bloque).toContain(EXPORT_EJERCICIOS.contenido);
    expect(bloque).toContain("reglas");
    expect(bloque).toContain(EXPORT_REGLAS.contenido);
    expect(bloque).toContain("ejemplo");
    expect(bloque).toContain(EXPORT_EJEMPLO.contenido);
    // El orden de aparicion respeta el de la lista de entrada.
    expect(bloque.indexOf(EXPORT_EJERCICIOS.contenido)).toBeLessThan(
      bloque.indexOf(EXPORT_REGLAS.contenido),
    );
    expect(bloque.indexOf(EXPORT_REGLAS.contenido)).toBeLessThan(
      bloque.indexOf(EXPORT_EJEMPLO.contenido),
    );
  });

  it("con un solo recurso, el bloque solo tiene ese delimitador y contenido (triangulacion)", () => {
    const bloque = armarBloqueParaCopiar([EXPORT_REGLAS]);

    expect(bloque).toContain("reglas");
    expect(bloque).toContain(EXPORT_REGLAS.contenido);
    expect(bloque).not.toContain(EXPORT_EJERCICIOS.contenido);
  });
});

describe("copiarParaLLM", () => {
  it("copia exitosa: escribe al portapapeles un bloque con los 3 payloads y devuelve 'ok'", async () => {
    const clipboard = { writeText: vi.fn().mockResolvedValue(undefined) };
    const obtenerExports = vi
      .fn()
      .mockResolvedValue([EXPORT_EJERCICIOS, EXPORT_REGLAS, EXPORT_EJEMPLO]);

    const estado = await copiarParaLLM({ obtenerExports, clipboard });

    expect(estado).toBe("ok");
    expect(clipboard.writeText).toHaveBeenCalledTimes(1);
    const bloqueEscrito = clipboard.writeText.mock.calls[0]?.[0] as string;
    expect(bloqueEscrito).toContain(EXPORT_EJERCICIOS.contenido);
    expect(bloqueEscrito).toContain(EXPORT_REGLAS.contenido);
    expect(bloqueEscrito).toContain(EXPORT_EJEMPLO.contenido);
  });

  it("portapapeles no disponible (contexto inseguro / permiso denegado): devuelve 'error' sin excepcion sin manejar", async () => {
    const clipboard = { writeText: vi.fn().mockRejectedValue(new Error("denegado")) };
    const obtenerExports = vi
      .fn()
      .mockResolvedValue([EXPORT_EJERCICIOS, EXPORT_REGLAS, EXPORT_EJEMPLO]);

    const estado = await copiarParaLLM({ obtenerExports, clipboard });

    expect(estado).toBe("error");
  });

  it("si uno de los 3 exports falla, devuelve 'error' y NUNCA escribe una copia parcial", async () => {
    const clipboard = { writeText: vi.fn().mockResolvedValue(undefined) };
    const obtenerExports = vi.fn().mockRejectedValue(new Error("fallo de red"));

    const estado = await copiarParaLLM({ obtenerExports, clipboard });

    expect(estado).toBe("error");
    expect(clipboard.writeText).not.toHaveBeenCalled();
  });
});

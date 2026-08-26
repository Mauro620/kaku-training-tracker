import { describe, expect, it, vi } from "vitest";

import { obtenerExportsLLM, type ExportRead } from "@/lib/api/hooks";

// obtenerExportsLLM es la unica pieza que sabe pegarle a los 3 endpoints de
// export (ejercicios/reglas/ejemplo). Sin este test, un path mal armado o un
// orden equivocado de recursos solo se nota manualmente en el boton de
// copiar. Sigue el patron de outbox.test.ts: se inyecta un `cliente` fake
// en vez de mockear el modulo `@/lib/api/client`.

function mockCliente(respuestas: Record<string, ExportRead>) {
  return {
    get: vi.fn((path: string) => {
      const recurso = path.split("/").pop() as string;
      const r = respuestas[recurso];
      if (!r) return Promise.reject(new Error(`sin mock para ${path}`));
      return Promise.resolve(r);
    }),
  };
}

describe("obtenerExportsLLM", () => {
  it("pega a los 3 recursos y devuelve sus ExportRead en orden ejercicios/reglas/ejemplo", async () => {
    const cliente = mockCliente({
      ejercicios: { recurso: "ejercicios", formato: "json", contenido: "[]" },
      reglas: { recurso: "reglas", formato: "markdown", contenido: "# Reglas" },
      ejemplo: { recurso: "ejemplo", formato: "json", contenido: "{}" },
    });

    const resultado = await obtenerExportsLLM(cliente);

    expect(cliente.get).toHaveBeenCalledWith("/planes/importar/export/ejercicios");
    expect(cliente.get).toHaveBeenCalledWith("/planes/importar/export/reglas");
    expect(cliente.get).toHaveBeenCalledWith("/planes/importar/export/ejemplo");
    expect(resultado.map((r) => r.recurso)).toEqual(["ejercicios", "reglas", "ejemplo"]);
  });

  it("propaga el rechazo si uno de los 3 recursos falla (no hay copia parcial)", async () => {
    const cliente = mockCliente({
      ejercicios: { recurso: "ejercicios", formato: "json", contenido: "[]" },
      // "reglas" ausente a proposito: su get() rechaza.
      ejemplo: { recurso: "ejemplo", formato: "json", contenido: "{}" },
    });

    await expect(obtenerExportsLLM(cliente)).rejects.toThrow("sin mock para");
  });
});

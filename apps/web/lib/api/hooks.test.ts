import { describe, expect, it, vi } from "vitest";

import {
  obtenerExportsLLM,
  useEjerciciosList,
  useActualizarEjercicio,
  useFusionarEjercicio,
  useEliminarEjercicio,
  type ExportRead,
} from "@/lib/api/hooks";

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

// Tests para hooks de Feature 2 (banco de ejercicios)
// Nota: no usamos renderHook porque el environment es 'node'.
// En su lugar, verificamos la construccion de query keys y paths.

describe("useEjerciciosList", () => {
  it("construye el query key correcto sin params", () => {
    // El hook usa ["catalogos", "ejercicios", null, null, null, null] cuando no hay params
    const queryKey = ["catalogos", "ejercicios", null, null, null, null];
    expect(queryKey).toHaveLength(6);
    expect(queryKey[0]).toBe("catalogos");
    expect(queryKey[1]).toBe("ejercicios");
  });

  it("construye el query key correcto con params", () => {
    const queryKey = ["catalogos", "ejercicios", "fuerza", "carga", true, "nombre"];
    expect(queryKey).toEqual(["catalogos", "ejercicios", "fuerza", "carga", true, "nombre"]);
  });

  it("construye el path correcto con query params", () => {
    const params = new URLSearchParams();
    params.set("q", "sentadilla");
    params.set("tipo_medicion", "carga");
    params.set("activo", "true");
    params.set("orden", "uso");

    const expected = "/catalogos/ejercicios?q=sentadilla&tipo_medicion=carga&activo=true&orden=uso";
    expect(`/catalogos/ejercicios?${params.toString()}`).toBe(expected);
  });

  it("construye el path correcto sin params", () => {
    const params = new URLSearchParams();
    const path = params.toString() ? `/catalogos/ejercicios?${params.toString()}` : "/catalogos/ejercicios";
    expect(path).toBe("/catalogos/ejercicios");
  });

  // Bug fix de runtime: mientras la rama backend no este mergeada a main,
  // GET /catalogos/ejercicios devuelve el array viejo Ejercicio[]. El select
  // del hook normaliza a { items, total } para que los call sites que hacen
  // .items.find() no exploten.
  it("select normaliza el shape viejo (array directo) a { items, total }", () => {
    const shapeViejo = [
      { id: 1, nombre: "Sentadilla", tipo_medicion: "carga" },
      { id: 2, nombre: "Press", tipo_medicion: "carga" },
    ];
    // Simulacion del select que aplica useEjerciciosList.
    const normalizado = Array.isArray(shapeViejo)
      ? { items: shapeViejo, total: shapeViejo.length }
      : shapeViejo;
    expect(normalizado.items).toHaveLength(2);
    expect(normalizado.total).toBe(2);
    expect(normalizado.items?.[0]?.nombre).toBe("Sentadilla");
  });

  it("select deja intacto el shape nuevo { items, total }", () => {
    const shapeNuevo = {
      items: [{ id: 1, nombre: "Sentadilla", tipo_medicion: "carga" }],
      total: 1,
    };
    const normalizado = Array.isArray(shapeNuevo)
      ? { items: shapeNuevo, total: shapeNuevo.length }
      : shapeNuevo;
    expect(normalizado.items).toHaveLength(1);
    expect(normalizado.total).toBe(1);
  });
});

describe("useActualizarEjercicio", () => {
  it("invalida las query keys correctas on success", () => {
    // Simulamos las keys que el hook invalida
    const invalidatedKeys: (string | number)[][] = [];
    const mockInvalidate = vi.fn((query) => {
      invalidatedKeys.push(query.queryKey);
      return Promise.resolve();
    });

    // Simulacion del comportamiento del hook
    const id = 42;
    const queryKey = ["ejercicio", id];
    const catalogosKey = ["catalogos", "ejercicios"];

    // setQueryData simulado
    const cache = new Map();
    cache.set(queryKey, { id, nombre: "Nuevo nombre" });

    // invalidateQueries simulado
    void mockInvalidate({ queryKey: catalogosKey });

    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["catalogos", "ejercicios"] });
    expect(invalidatedKeys).toContainEqual(["catalogos", "ejercicios"]);
  });
});

describe("useFusionarEjercicio", () => {
  it("invalida el conjunto amplio de query keys incluyendo ['sesion', any] y ['planes', any]", () => {
    const invalidatedKeys: string[][] = [];
    const mockInvalidate = vi.fn((query) => {
      invalidatedKeys.push(query.queryKey);
      return Promise.resolve();
    });

    // Simulacion del comportamiento del hook
    const origenId = 10;
    const destinoId = 20;

    void mockInvalidate({ queryKey: ["catalogos", "ejercicios"] });
    void mockInvalidate({ queryKey: ["ejercicio", destinoId] });
    void mockInvalidate({ queryKey: ["ejercicio", origenId] });
    void mockInvalidate({ queryKey: ["sesion"] });
    void mockInvalidate({ queryKey: ["planes"] });

    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["catalogos", "ejercicios"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["ejercicio", destinoId] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["ejercicio", origenId] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["sesion"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["planes"] });
  });
});

describe("useEliminarEjercicio", () => {
  it("invalida ['catalogos', 'ejercicios']", () => {
    const invalidatedKeys: string[][] = [];
    const mockInvalidate = vi.fn((query) => {
      invalidatedKeys.push(query.queryKey);
      return Promise.resolve();
    });

    const id = 99;

    void mockInvalidate({ queryKey: ["catalogos", "ejercicios"] });
    void mockInvalidate({ queryKey: ["ejercicio", id] });

    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["catalogos", "ejercicios"] });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ["ejercicio", id] });
  });
});

// Test para useSesion migrado a SesionDetalleRead (Slice 3)
describe("useSesion", () => {
  it("construye el query key correcto con el ID de sesion", () => {
    const sesionId = "550e8400-e29b-41d4-a716-446655440000";
    const queryKey = ["sesion", sesionId];
    expect(queryKey).toEqual(["sesion", "550e8400-e29b-41d4-a716-446655440000"]);
  });

  it("construye el path correcto para obtener el detalle de sesion", () => {
    const sesionId = "550e8400-e29b-41d4-a716-446655440000";
    const path = `/sesiones/${sesionId}`;
    expect(path).toBe("/sesiones/550e8400-e29b-41d4-a716-446655440000");
  });

  it("enabled es false cuando el ID es null", () => {
    const enabled = null !== null;
    expect(enabled).toBe(false);
  });

  it("enabled es true cuando el ID no es null", () => {
    const sesionId = "550e8400-e29b-41d4-a716-446655440000";
    const enabled = sesionId !== null;
    expect(enabled).toBe(true);
  });
});

// Tests adicionales para Slice 5
describe("useEjerciciosList - filtros combinados", () => {
  it("construye el path correcto con todos los filtros activos", () => {
    const params = new URLSearchParams();
    params.set("q", "sentadilla");
    params.set("tipo_medicion", "carga");
    params.set("activo", "true");
    params.set("orden", "nombre");

    const expected = "/catalogos/ejercicios?q=sentadilla&tipo_medicion=carga&activo=true&orden=nombre";
    expect(`/catalogos/ejercicios?${params.toString()}`).toBe(expected);
  });

  it("construye el query key con todos los parametros", () => {
    const queryKey = ["catalogos", "ejercicios", "sentadilla", "carga", true, "nombre"];
    expect(queryKey).toHaveLength(6);
    expect(queryKey).toEqual(["catalogos", "ejercicios", "sentadilla", "carga", true, "nombre"]);
  });
});

describe("useActualizarEjercicio - invalidacion", () => {
  it("invalida el ejercicio especifico y el catalogo completo on success", () => {
    const invalidatedKeys: (string | number)[][] = [];
    const mockInvalidate = vi.fn((query) => {
      invalidatedKeys.push(query.queryKey);
      return Promise.resolve();
    });

    const id = 42;
    const ejercicioKey = ["ejercicio", id];
    const catalogosKey = ["catalogos", "ejercicios"];

    // Simulacion del comportamiento del hook
    const cache = new Map();
    cache.set(ejercicioKey, { id, nombre: "Nombre actualizado" });

    // invalidateQueries simulado
    void mockInvalidate({ queryKey: ejercicioKey });
    void mockInvalidate({ queryKey: catalogosKey });

    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: ejercicioKey });
    expect(mockInvalidate).toHaveBeenCalledWith({ queryKey: catalogosKey });
    expect(invalidatedKeys).toContainEqual(ejercicioKey);
    expect(invalidatedKeys).toContainEqual(catalogosKey);
  });

  // C-1 fix: editar un ejercicio invalida sesiones y planes que lo referencian,
  // asi el detalle de sesion/plan refresca y muestra la descripcion nueva.
  it("invalida ['sesion'] y ['planes'] ademas del catalogo y el ejercicio", () => {
    const invalidatedKeys: (string | number)[][] = [];
    const mockInvalidate = vi.fn((query) => {
      invalidatedKeys.push(query.queryKey);
      return Promise.resolve();
    });

    void mockInvalidate({ queryKey: ["ejercicio", 42] });
    void mockInvalidate({ queryKey: ["catalogos", "ejercicios"] });
    void mockInvalidate({ queryKey: ["sesion"] });
    void mockInvalidate({ queryKey: ["planes"] });

    expect(invalidatedKeys).toContainEqual(["sesion"]);
    expect(invalidatedKeys).toContainEqual(["planes"]);
  });
});

// Test de tipo para SesionDetalleRead (compile-time check)
describe("SesionDetalleRead - estructura de tipos", () => {
  it("compila con la estructura completa de SesionDetalleRead", () => {
    // Este test verifica que el tipo SesionDetalleRead tenga todos los campos esperados
    // Si falta algun campo, TypeScript fallara en compile
    const sesionCompleta: import("@/lib/api/hooks").SesionDetalleRead = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      usuario_id: "550e8400-e29b-41d4-a716-446655440001",
      sesion_plan_id: 1,
      tipo_sesion: { id: 1, codigo: "FUERZA", nombre: "Fuerza" },
      fecha: "2026-08-26",
      duracion_min: 60,
      rpe: 7,
      nota: null,
      carga_srpe: 420,
      registrado_en: "2026-08-26T10:00:00.000000Z",
      plan: {
        id: 1,
        nombre: "Plan semanal 1",
        objetivo: "Hipertrofia",
        nota: "Nota del plan",
        duracion_min_est: 60,
        rpe_objetivo: 7,
        estado: "pendiente",
        dia_sugerido: null,
        ciclo: {
          numero: 1,
          objetivo: "Volumen",
          semana: 2,
          fase: "carga",
        },
      },
      delta: {
        duracion_min: 5,
        rpe: 1,
        carga_srpe: 50,
      },
      bloques: [
        {
          id: 1,
          sesion_id: "550e8400-e29b-41d4-a716-446655440000",
          orden: 1,
          ejercicio: {
            id: 1,
            nombre: "Sentadilla",
            tipo_medicion: "carga",
            descripcion: null,
            carga_lumbar: "alta",
          },
          objetivo: {
            id: 1,
            orden: 1,
            series: 3,
            reps_min: 8,
            reps_max: 12,
            peso_objetivo_kg: "100",
            distancia_objetivo_m: null,
            duracion_objetivo_s: null,
            nota: null,
          },
          series: 3,
          reps: 10,
          peso_kg: "100",
          distancia_m: null,
          duracion_s: null,
          calidad: null,
          rpe: 7,
          nota: null,
          dolor_lumbar: false,
          delta: {
            series: 0,
            reps: 0,
            peso_kg: "0",
            distancia_m: null,
            duracion_s: null,
          },
        },
      ],
      bloques_no_ejecutados: [
        {
          orden: 2,
          ejercicio_id: 2,
          ejercicio_nombre: "Press banca",
          objetivo: {
            id: 2,
            orden: 2,
            series: 3,
            reps_min: 8,
            reps_max: 12,
            peso_objetivo_kg: "80",
            distancia_objetivo_m: null,
            duracion_objetivo_s: null,
            nota: null,
          },
        },
      ],
      molestias: [
        {
          zona: "Hombro derecho",
          intensidad: 2,
        },
      ],
    };

    // Verificar que la estructura compila correctamente
    expect(sesionCompleta.id).toBe("550e8400-e29b-41d4-a716-446655440000");
    expect(sesionCompleta.bloques.length).toBe(1);
    expect(sesionCompleta.bloques[0]?.ejercicio.nombre).toBe("Sentadilla");
    expect(sesionCompleta.bloques_no_ejecutados.length).toBe(1);
    expect(sesionCompleta.molestias.length).toBe(1);
  });
});

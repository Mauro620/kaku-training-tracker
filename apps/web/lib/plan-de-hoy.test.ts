import { describe, expect, it } from "vitest";
import type { Sesion, SesionPlan } from "@/lib/api/hooks";
import { resolverPlanDeHoy } from "@/lib/plan-de-hoy";

function plan(id: number, estado: SesionPlan["estado"], dia = 2): SesionPlan {
  return { id, estado, dia_sugerido: dia, tipo_sesion_id: id } as unknown as SesionPlan;
}
function sesion(id: string, planId: number | null): Sesion {
  return { id, sesion_plan_id: planId } as unknown as Sesion;
}

describe("resolverPlanDeHoy", () => {
  it("con la activacion ya registrada, el partido sigue pendiente y se puede iniciar", () => {
    const activacion = plan(1, "cumplido");
    const partido = plan(2, "pendiente");

    const r = resolverPlanDeHoy([activacion, partido], [sesion("s1", 1)], [activacion, partido]);

    expect(r.sesiones).toHaveLength(1);
    expect(r.pendientes.map((p) => p.id)).toEqual([2]);
  });

  it("con la activacion descartada, el partido sigue pendiente y la descartada se conserva a la vista", () => {
    const r = resolverPlanDeHoy([plan(1, "descartado"), plan(2, "pendiente")], [], []);

    expect(r.pendientes.map((p) => p.id)).toEqual([2]);
    expect(r.descartados.map((p) => p.id)).toEqual([1]);
  });

  it("varias sesiones reales el mismo dia se conservan todas", () => {
    const r = resolverPlanDeHoy([], [sesion("a", null), sesion("b", null)], []);
    expect(r.sesiones.map((s) => s.id)).toEqual(["a", "b"]);
  });

  it("un plan con sesion real no es pendiente aunque su estado llegue desfasado", () => {
    const r = resolverPlanDeHoy([plan(1, "pendiente")], [sesion("s1", 1)], []);
    expect(r.pendientes).toEqual([]);
  });

  it("otras pendientes son solo de otros dias: ni las de hoy ni las ya ejecutadas", () => {
    const hoy = plan(1, "pendiente", 2);
    const martes = plan(3, "pendiente", 1);
    const viernes = plan(4, "pendiente", 4);
    const r = resolverPlanDeHoy([hoy], [sesion("s", 4)], [hoy, martes, viernes, plan(5, "cumplido", 0)]);
    expect(r.otrasPendientes.map((p) => p.id)).toEqual([3]);
  });

  it("sin nada: todo vacio", () => {
    expect(resolverPlanDeHoy([], [], [])).toEqual({
      sesiones: [],
      pendientes: [],
      descartados: [],
      otrasPendientes: [],
    });
  });
});

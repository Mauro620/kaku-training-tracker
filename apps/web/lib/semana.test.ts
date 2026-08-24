import { describe, expect, it } from "vitest";
import {
  diaDeLaSemana,
  elegirCicloActivo,
  numeroDeSemana,
  progresoDeSemana,
} from "@/lib/semana";
import type { Ciclo, SesionPlan } from "@/lib/api/hooks";

// El backend ancla ciclo.fecha_inicio al lunes ISO, asi que estos helpers
// pueden asumir que el dia 0 de la semana 1 ES fecha_inicio. Si ese anclaje
// se rompe, estos tests no lo ven: el que lo cubre es
// test_el_ciclo_se_ancla_al_lunes_de_su_semana en el backend.
const LUNES = "2026-08-17";

describe("numeroDeSemana", () => {
  it("empieza en 1, no en 0", () => {
    expect(numeroDeSemana(LUNES, LUNES)).toBe(1);
  });

  it("el ultimo dia de la semana 1 sigue siendo la semana 1", () => {
    expect(numeroDeSemana(LUNES, "2026-08-23")).toBe(1);
  });

  it("el dia 7 ya es la semana 2", () => {
    expect(numeroDeSemana(LUNES, "2026-08-24")).toBe(2);
  });

  it("cruza el cambio de mes sin perder un dia", () => {
    expect(numeroDeSemana(LUNES, "2026-09-07")).toBe(4);
  });
});

describe("diaDeLaSemana", () => {
  it("mapea lunes a 0 y domingo a 6", () => {
    expect(diaDeLaSemana(LUNES, LUNES)).toBe(0);
    expect(diaDeLaSemana(LUNES, "2026-08-23")).toBe(6);
  });

  it("vuelve a 0 al arrancar la semana siguiente", () => {
    expect(diaDeLaSemana(LUNES, "2026-08-24")).toBe(0);
  });
});

describe("progresoDeSemana", () => {
  const plan = (estado: SesionPlan["estado"]): SesionPlan =>
    ({ estado }) as SesionPlan;

  it("cuenta movido como hecho: se ejecuto otro dia pero cumple la semana", () => {
    expect(progresoDeSemana([plan("cumplido"), plan("movido"), plan("pendiente")]))
      .toEqual({ hechas: 2, total: 3 });
  });

  it("saca descartado del denominador para que no arrastre el progreso", () => {
    expect(progresoDeSemana([plan("cumplido"), plan("descartado")])).toEqual({
      hechas: 1,
      total: 1,
    });
  });

  it("no explota sin planes", () => {
    expect(progresoDeSemana([])).toEqual({ hechas: 0, total: 0 });
  });
});

describe("elegirCicloActivo", () => {
  const ciclo = (p: Partial<Ciclo>): Ciclo =>
    ({
      estado: "planificado",
      fecha_inicio: "2026-08-17",
      fecha_fin_prevista: "2026-09-13",
      ...p,
    }) as Ciclo;

  it("ignora los cerrados", () => {
    expect(elegirCicloActivo([ciclo({ estado: "cerrado" })], LUNES)).toBeNull();
  });

  it("prefiere el que cubre la fecha", () => {
    const viejo = ciclo({
      id: 1,
      fecha_inicio: "2026-01-05",
      fecha_fin_prevista: "2026-02-01",
    });
    const actual = ciclo({ id: 2 });
    expect(elegirCicloActivo([viejo, actual], LUNES)?.id).toBe(2);
  });

  it("cae al mas reciente si ninguno cubre la fecha", () => {
    const a = ciclo({
      id: 1,
      fecha_inicio: "2026-01-05",
      fecha_fin_prevista: "2026-02-01",
    });
    const b = ciclo({
      id: 2,
      fecha_inicio: "2026-03-02",
      fecha_fin_prevista: "2026-03-29",
    });
    expect(elegirCicloActivo([a, b], "2026-12-01")?.id).toBe(2);
  });
});

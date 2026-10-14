import { describe, expect, it } from "vitest";
import type { PerfilAtletaBase } from "@/lib/api/hooks";
import { parsearLista, validarPerfil } from "@/lib/perfil";

function base(): PerfilAtletaBase {
  return {
    posicion: "Extremo izquierdo",
    rol_tactico: "1v1",
    pie_dominante: "derecho",
    talla_cm: "178.0",
    peso_kg: "80.00",
    lesiones_activas: [],
    objetivos: ["a"],
    eventos_fijos: [{ dia: 0, hora: "21:00", tipo_sesion: "partido", nombre: "Equipo", duracion_min: 90 }],
    ventanas: [{ dia: 0, inicio: "09:00", fin: "10:30", lugares: ["Gimnasio"] }],
    lugares: [{ nombre: "Gimnasio", equipamiento: [] }],
    equipamiento_propio: ["conos"],
  };
}

describe("validarPerfil", () => {
  it("acepta un perfil válido", () => {
    expect(validarPerfil(base())).toBeNull();
  });
  it("exige posición, pie y rol", () => {
    expect(validarPerfil({ ...base(), posicion: " " })).toMatch(/posición/);
    expect(validarPerfil({ ...base(), pie_dominante: "" })).toMatch(/pie/);
    expect(validarPerfil({ ...base(), rol_tactico: "" })).toMatch(/rol/);
  });
  it("rechaza ventana con inicio posterior al fin", () => {
    const p = base();
    p.ventanas[0] = { dia: 0, inicio: "11:00", fin: "10:00", lugares: ["Gimnasio"] };
    expect(validarPerfil(p)).toMatch(/Lunes.*inicio/);
  });
  it("rechaza ventana con lugar no declarado", () => {
    const p = base();
    p.ventanas[0] = { dia: 1, inicio: "09:00", fin: "10:00", lugares: ["Piscina"] };
    expect(validarPerfil(p)).toMatch(/Piscina/);
  });
  it("rechaza lugares repetidos y horas mal formadas", () => {
    const p = base();
    p.lugares.push({ nombre: "Gimnasio", equipamiento: [] });
    expect(validarPerfil(p)).toMatch(/repetidos/);
    const q = base();
    q.eventos_fijos[0] = { ...q.eventos_fijos[0]!, hora: "9:00" };
    expect(validarPerfil(q)).toMatch(/hora inválida/);
  });
});

describe("parsearLista", () => {
  it("separa por comas, recorta y descarta vacíos", () => {
    expect(parsearLista(" barra, , mancuernas ,")).toEqual(["barra", "mancuernas"]);
    expect(parsearLista("")).toEqual([]);
  });
});

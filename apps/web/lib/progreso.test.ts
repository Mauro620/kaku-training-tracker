import { describe, expect, it } from "vitest";
import {
  alturasRelativas,
  escalarSerie,
  etiquetaFecha,
  formatoNumero,
  rutaLinea,
} from "@/lib/progreso";

describe("formatoNumero", () => {
  it("usa coma y recorta ceros de relleno", () => {
    expect(formatoNumero(7)).toBe("7");
    expect(formatoNumero(7.5)).toBe("7,5");
    expect(formatoNumero(1.081, 2)).toBe("1,08");
    expect(formatoNumero(100)).toBe("100");
  });
  it("con 0 decimales no recorta ceros enteros (regresion: 50 salia como 5)", () => {
    expect(formatoNumero(50, 0)).toBe("50");
    expect(formatoNumero(100, 0)).toBe("100");
    expect(formatoNumero(10)).toBe("10");
  });
});

describe("etiquetaFecha", () => {
  it("formatea YYYY-MM-DD sin pasar por Date (sin drift de zona)", () => {
    expect(etiquetaFecha("2026-09-21")).toBe("21 sep");
    expect(etiquetaFecha("2026-01-05")).toBe("5 ene");
  });
});

describe("escalarSerie", () => {
  it("el mayor valor queda arriba (y minima) y el menor abajo", () => {
    const [a, b] = escalarSerie([10, 20], 100, 50, 0);
    expect(a).toEqual({ x: 0, y: 50 });
    expect(b).toEqual({ x: 100, y: 0 });
  });
  it("una serie constante o de un punto va a media altura", () => {
    expect(escalarSerie([5, 5, 5], 100, 40, 0).map((p) => p.y)).toEqual([20, 20, 20]);
    expect(escalarSerie([5], 100, 40, 0)).toEqual([{ x: 50, y: 20 }]);
  });
  it("respeta un dominio fijo", () => {
    const [p] = escalarSerie([5], 100, 100, 0, [0, 10]);
    expect(p?.y).toBe(50);
  });
  it("serie vacia no explota", () => {
    expect(escalarSerie([], 100, 100)).toEqual([]);
  });
});

describe("rutaLinea", () => {
  it("arma un path SVG M/L", () => {
    expect(rutaLinea([{ x: 0, y: 1 }, { x: 2, y: 3 }])).toBe("M0.0,1.0 L2.0,3.0");
    expect(rutaLinea([])).toBe("");
  });
});

describe("alturasRelativas", () => {
  it("normaliza contra el maximo y tolera todo en cero", () => {
    expect(alturasRelativas([0, 50, 100])).toEqual([0, 0.5, 1]);
    expect(alturasRelativas([0, 0])).toEqual([0, 0]);
  });
});

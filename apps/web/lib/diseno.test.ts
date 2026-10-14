import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";
import config from "../tailwind.config";

// Guardas de diseno. Ambos bugs que cubren fueron silenciosos: no fallan al
// compilar ni en los tests, solo se ven en el telefono.

const RAIZ = join(__dirname, "..");

function archivos(dir: string): string[] {
  return readdirSync(dir).flatMap((nombre) => {
    const ruta = join(dir, nombre);
    if (statSync(ruta).isDirectory()) return archivos(ruta);
    return ruta.endsWith(".tsx") ? [ruta] : [];
  });
}

const FUENTES = [...archivos(join(RAIZ, "app")), ...archivos(join(RAIZ, "components"))];

describe("safe area superior", () => {
  // La PWA usa viewport-fit=cover y barra de estado translucida: el contenido
  // corre DEBAJO de la barra/notch. Una vista a pantalla completa sin
  // `env(safe-area-inset-top)` deja el titulo y "Volver" tapados; solo se ven
  // deslizando hacia abajo, y al soltar la vista rebota.
  it("toda vista a pantalla completa (max-w-3xl px-5) suma el safe-area-inset-top", () => {
    const infractores: string[] = [];
    for (const archivo of FUENTES) {
      readFileSync(archivo, "utf8")
        .split("\n")
        .forEach((linea, i) => {
          if (linea.includes("max-w-3xl px-5") && !linea.includes("safe-area-inset-top")) {
            infractores.push(`${relative(RAIZ, archivo)}:${i + 1}`);
          }
        });
    }
    expect(infractores).toEqual([]);
  });
});

describe("tokens de color de Tailwind", () => {
  const colores = (config.theme?.extend?.colors ?? {}) as Record<string, unknown>;

  // Una clase con un color que no existe (`bg-accent`) no falla: Tailwind la
  // descarta y el boton queda sin fondo, con solo el texto visible.
  it("define los alias que el codigo usa para el boton primario y las tarjetas", () => {
    expect(colores.accent).toBeDefined();
    expect((colores.bg as Record<string, unknown>)?.DEFAULT).toBeDefined();
    expect((colores.bg as Record<string, unknown>)?.card).toBeDefined();
  });

  it("todo color `bg-<nombre>` / `text-bg` que usan los componentes existe", () => {
    const usados = new Set<string>();
    for (const archivo of FUENTES) {
      const texto = readFileSync(archivo, "utf8");
      for (const m of texto.matchAll(/\b(?:bg|text)-(accent|bg)\b(?!-)/g)) usados.add(m[1]!);
    }
    for (const nombre of usados) expect(colores[nombre], nombre).toBeDefined();
  });
});

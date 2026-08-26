import { describe, expect, it } from "vitest";

import { formatearFechaLarga } from "@/lib/fecha";

describe("formatearFechaLarga", () => {
  it("formatea una fecha YYYY-MM-DD a formato largo en espanol", () => {
    // 26 de agosto de 2026 es miercoles
    const result = formatearFechaLarga("2026-08-26");
    expect(result).toBe("miércoles 26 de agosto");
  });

  it("formatea correctamente diferentes dias de la semana", () => {
    // 1 de enero de 2025 es miercoles
    expect(formatearFechaLarga("2025-01-01")).toBe("miércoles 1 de enero");

    // 2 de enero de 2025 es jueves
    expect(formatearFechaLarga("2025-01-02")).toBe("jueves 2 de enero");

    // 3 de enero de 2025 es viernes
    expect(formatearFechaLarga("2025-01-03")).toBe("viernes 3 de enero");
  });

  it("formatea correctamente diferentes meses", () => {
    expect(formatearFechaLarga("2025-12-25")).toBe("jueves 25 de diciembre");
    expect(formatearFechaLarga("2025-02-14")).toBe("viernes 14 de febrero");
    expect(formatearFechaLarga("2025-07-04")).toBe("viernes 4 de julio");
  });
});

import { describe, expect, it, vi } from "vitest";

import { endpointDesdeApi } from "@/lib/sync/outbox";
import type { EventoOutbox } from "@/lib/sync/tipos";

// endpointDesdeApi es la unica pieza que traduce un EventoOutbox en un
// llamado HTTP real. Sin este test, un path mal armado (ej. con el
// /api/v1 duplicado, o pegandole a un endpoint que no existe) solo se
// nota en runtime, offline, con el usuario mirando el chip de "fallido".

function mockApi() {
  return { post: vi.fn().mockResolvedValue({ id: "x" }) };
}

describe("endpointDesdeApi", () => {
  it("sueno pega a /sueno con el cuerpo tal cual", async () => {
    const api = mockApi();
    const evento: EventoOutbox = {
      tipo: "sueno",
      cuerpo: {
        fecha: "2026-08-07",
        inicio: "2026-08-06T23:00:00Z",
        fin: "2026-08-07T07:00:00Z",
        celular_fuera: true,
        origen: "manual",
        idempotency_key: "key-1",
      },
    };
    await endpointDesdeApi(api)(evento);
    expect(api.post).toHaveBeenCalledWith("/sueno", evento.cuerpo);
  });

  it("hidratacion pega a /hidratacion", async () => {
    const api = mockApi();
    const evento: EventoOutbox = {
      tipo: "hidratacion",
      cuerpo: { fecha: "2026-08-07", cantidad_ml: 500, idempotency_key: "key-2" },
    };
    await endpointDesdeApi(api)(evento);
    expect(api.post).toHaveBeenCalledWith("/hidratacion", evento.cuerpo);
  });

  it("habito_registro pega a /habitos/registro", async () => {
    const api = mockApi();
    const evento: EventoOutbox = {
      tipo: "habito_registro",
      cuerpo: { habito_id: 1, fecha: "2026-08-07", valor: true, idempotency_key: "key-3" },
    };
    await endpointDesdeApi(api)(evento);
    expect(api.post).toHaveBeenCalledWith("/habitos/registro", evento.cuerpo);
  });

  it("molestia pega a /molestias", async () => {
    const api = mockApi();
    const evento: EventoOutbox = {
      tipo: "molestia",
      cuerpo: {
        fecha: "2026-08-07",
        zona_id: 1,
        intensidad: 5,
        nota: null,
        idempotency_key: "key-4",
      },
    };
    await endpointDesdeApi(api)(evento);
    expect(api.post).toHaveBeenCalledWith("/molestias", evento.cuerpo);
  });

  it("sesion pega UNA vez a /sesiones con los bloques anidados en el body", async () => {
    const api = mockApi();
    const evento: EventoOutbox = {
      tipo: "sesion",
      cuerpo: {
        sesion: {
          id: "s1",
          idempotency_key: "key-5",
          sesion_plan_id: null,
          fecha: "2026-08-07",
          tipo_sesion_id: 1,
          duracion_min: 60,
          rpe: 7,
          nota: null,
        },
        bloques: [
          {
            ejercicio_id: 1,
            orden: 0,
            series: 3,
            reps: 10,
            distancia_m: null,
            duracion_s: null,
            calidad: null,
            peso_kg: 80,
            rpe: null,
            dolor_lumbar: false,
          },
        ],
      },
    };
    await endpointDesdeApi(api)(evento);
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith("/sesiones", {
      ...evento.cuerpo.sesion,
      bloques: evento.cuerpo.bloques,
    });
  });
});

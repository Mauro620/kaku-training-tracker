import { describe, expect, it, vi } from "vitest";

import {
  DELAYS_MS,
  intentarUnaVez,
  procesar,
  storeEnMemoria,
  type Dormir,
} from "@/lib/sync/nucleo";
import { MAX_INTENTOS, type EventoOutbox, type ItemOutbox } from "@/lib/sync/tipos";

const eventoDummy: EventoOutbox = {
  tipo: "sueno",
  cuerpo: {
    fecha: "2026-08-07",
    inicio: "2026-08-06T23:30:00Z",
    fin: "2026-08-07T07:00:00Z",
    celular_fuera: true,
    origen: "manual",
    idempotency_key: "key-1",
  },
};

function nuevoItem(overrides: Partial<ItemOutbox> = {}): ItemOutbox {
  return {
    id: "item-1",
    estado: "pendiente",
    intentos: 0,
    creado_en: "2026-08-07T00:00:00Z",
    actualizado_en: "2026-08-07T00:00:00Z",
    ultimo_error: null,
    evento: eventoDummy,
    ...overrides,
  };
}

async function getItem(
  store: ReturnType<typeof storeEnMemoria>,
  id: string,
): Promise<ItemOutbox> {
  const item = await store.get(id);
  if (!item) throw new Error(`test setup: item ${id} no existe`);
  return item;
}

describe("intentarUnaVez", () => {
  it("marca como sincronizado cuando el endpoint responde OK", async () => {
    const store = storeEnMemoria([nuevoItem()]);
    const enviar = vi.fn().mockResolvedValue(undefined);

    const exito = await intentarUnaVez(store, await getItem(store, "item-1"), enviar);

    expect(exito).toBe(true);
    expect((await store.get("item-1"))?.estado).toBe("sincronizado");
    expect(enviar).toHaveBeenCalledTimes(1);
  });

  it("incrementa intentos y queda pendiente si el endpoint falla y le quedan reintentos", async () => {
    const store = storeEnMemoria([nuevoItem()]);
    const enviar = vi.fn().mockRejectedValue(new Error("network"));

    const dormir: Dormir = vi.fn().mockResolvedValue(undefined);
    const exito = await intentarUnaVez(
      store,
      await getItem(store, "item-1"),
      enviar,
      dormir,
    );

    expect(exito).toBe(false);
    const item = await store.get("item-1");
    expect(item?.estado).toBe("pendiente");
    expect(item?.intentos).toBe(1);
    expect(item?.ultimo_error).toBe("network");
    // Duerme el delay del primer reintento (1s).
    expect(dormir).toHaveBeenCalledWith(DELAYS_MS[0]);
  });

  it("marca como fallido tras MAX_INTENTOS fallos consecutivos", async () => {
    const item = nuevoItem({ intentos: MAX_INTENTOS - 1 });
    const store = storeEnMemoria([item]);
    const enviar = vi.fn().mockRejectedValue(new Error("still down"));
    const dormir: Dormir = vi.fn().mockResolvedValue(undefined);

    await intentarUnaVez(store, await getItem(store, "item-1"), enviar, dormir);

    const actualizado = await store.get("item-1");
    expect(actualizado?.estado).toBe("fallido");
    expect(actualizado?.intentos).toBe(MAX_INTENTOS);
    expect(actualizado?.ultimo_error).toBe("still down");
  });

  it("atraviesa estados enviando -> sincronizado en una sola corrida", async () => {
    const store = storeEnMemoria([nuevoItem()]);
    const itemsVistos: string[] = [];
    const observer = {
      ...store,
      async put(i: ItemOutbox) {
        itemsVistos.push(i.estado);
        await store.put(i);
      },
    };
    await intentarUnaVez(observer, await getItem(observer, "item-1"), vi.fn().mockResolvedValue(undefined));
    expect(itemsVistos).toContain("enviando");
    expect(itemsVistos).toContain("sincronizado");
  });
});

describe("procesar", () => {
  it("procesa todos los pendientes hasta vaciar la cola", async () => {
    const items = [
      nuevoItem({ id: "a", creado_en: "2026-08-07T00:00:00Z" }),
      nuevoItem({
        id: "b",
        creado_en: "2026-08-07T00:01:00Z",
        evento: {
          tipo: "bienestar",
          cuerpo: {
            fecha: "2026-08-07",
            sueno_pobre: 2,
            fatiga: 3,
            dolor_muscular: 1,
            estres: 2,
            idempotency_key: "key-2",
          },
        },
      }),
    ];
    const store = storeEnMemoria(items);
    const enviar = vi.fn().mockResolvedValue(undefined);

    await procesar(store, enviar);

    expect(enviar).toHaveBeenCalledTimes(2);
    expect((await store.get("a"))?.estado).toBe("sincronizado");
    expect((await store.get("b"))?.estado).toBe("sincronizado");
  });

  it("respeta el orden FIFO: el item mas viejo se procesa primero", async () => {
    const viejo = nuevoItem({ id: "viejo", creado_en: "2026-08-07T00:00:00Z" });
    const nuevo = nuevoItem({ id: "nuevo", creado_en: "2026-08-07T01:00:00Z" });
    const store = storeEnMemoria([nuevo, viejo]); // desordenados a proposito
    const enviar = vi.fn().mockResolvedValue(undefined);

    await procesar(store, enviar);

    const ordenLlamadas = enviar.mock.calls.map((c) => {
      const ev = c[0] as EventoOutbox;
      // Sueno, bienestar, hidratacion, habito y molestia tienen key
      // directa en `cuerpo`. Sesion la tiene en `cuerpo.sesion`.
      if (ev.tipo === "sesion") return ev.cuerpo.sesion.idempotency_key;
      return (ev.cuerpo as { idempotency_key: string }).idempotency_key;
    });
    expect(ordenLlamadas[0]).toBe("key-1"); // el viejo
  });

  it("respeta AbortSignal: si aborta durante un delay, no procesa mas items", async () => {
    const store = storeEnMemoria([
      nuevoItem({ id: "a", creado_en: "2026-08-07T00:00:00Z" }),
      nuevoItem({ id: "b", creado_en: "2026-08-07T00:01:00Z" }),
    ]);
    const enviar = vi.fn().mockRejectedValue(new Error("network"));
    const controller = new AbortController();
    const dormir: Dormir = async () => {
      controller.abort();
    };

    await procesar(store, enviar, { dormir, abortar: controller.signal });

    // El primer intento fallo, se intento dormir (y aborto ahi). El segundo
    // item no llega a procesarse.
    expect(enviar).toHaveBeenCalledTimes(1);
  });

  it("tras 5 intentos, el item queda en fallido y la cola sigue con el siguiente", async () => {
    const a = nuevoItem({
      id: "a",
      creado_en: "2026-08-07T00:00:00Z",
      intentos: MAX_INTENTOS - 1, // un intento mas y cae en fallido
    });
    const b = nuevoItem({
      id: "b",
      creado_en: "2026-08-07T00:01:00Z",
      evento: {
        tipo: "bienestar",
        cuerpo: {
          fecha: "2026-08-07",
          sueno_pobre: 2,
          fatiga: 3,
          dolor_muscular: 1,
          estres: 2,
          idempotency_key: "key-2",
        },
      },
    });
    const store = storeEnMemoria([a, b]);
    const enviar = vi.fn().mockImplementation((ev: EventoOutbox) => {
      const key =
        ev.tipo === "sesion"
          ? ev.cuerpo.sesion.idempotency_key
          : (ev.cuerpo as { idempotency_key: string }).idempotency_key;
      if (key === "key-1") {
        return Promise.reject(new Error("down"));
      }
      return Promise.resolve();
    });
    const dormir: Dormir = vi.fn().mockResolvedValue(undefined);

    await procesar(store, enviar, { dormir });

    expect((await store.get("a"))?.estado).toBe("fallido");
    expect((await store.get("b"))?.estado).toBe("sincronizado");
  });
});
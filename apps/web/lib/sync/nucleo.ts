/**
 * Nucleo de la cola de salida offline-first (Fase 5).
 *
 * Logica pura: dado un store (`{ get, put, delete, where }`) y un endpoint,
 * procesa los items con retroceso exponencial. La capa de adaptacion a
 * Dexie vive en `outbox.ts`; este modulo no importa la base ni el reloj
 * (recibe `dormir` por parametro para tests).
 *
 * Estados: `pendiente` -> `enviando` -> `sincronizado` (exito) o
 * `pendiente` (fallo con reintentos disponibles) o `fallido` (5 fallos).
 *
 * Delays: 1s, 2s, 4s, 8s, 16s. Total: ~31s para 5 intentos.
 */

import {
  MAX_INTENTOS,
  type EstadoOutbox,
  type EventoOutbox,
  type ItemOutbox,
} from "@/lib/sync/tipos";

/** Delays entre reintentos, en milisegundos. */
export const DELAYS_MS = [1_000, 2_000, 4_000, 8_000, 16_000] as const;

/** Store minimo que necesita el nucleo. */
export interface StoreOutbox {
  get(id: string): Promise<ItemOutbox | undefined>;
  put(item: ItemOutbox): Promise<void>;
  delete(id: string): Promise<void>;
  firstPendiente(): Promise<ItemOutbox | undefined>;
  clear(): Promise<void>;
}

/** Inyectable para tests. La app pasa `api` de `@/lib/api/client`. */
export type EndpointOutbox = (evento: EventoOutbox) => Promise<void>;

/** Helper para tests. Default: setTimeout. */
export type Dormir = (ms: number) => Promise<void>;
export const dormirDefault: Dormir = (ms) =>
  new Promise((resolver) => setTimeout(resolver, ms));

export interface ProcesarOpciones {
  dormir?: Dormir;
  abortar?: AbortSignal;
}

/** Procesa toda la cola hasta vaciar `pendiente` o pasarlos a `fallido`. */
export async function procesar(
  store: StoreOutbox,
  enviar: EndpointOutbox,
  opciones: ProcesarOpciones = {},
): Promise<void> {
  const dormir = opciones.dormir ?? dormirDefault;
  const señal = opciones.abortar;

  let iteraciones = 0;
  const LIMITE_ITERACIONES = 1_000;

  while (iteraciones < LIMITE_ITERACIONES) {
    iteraciones += 1;
    if (señal?.aborted) return;

    const siguiente = await store.firstPendiente();
    if (!siguiente) return;

    await intentarUnaVez(store, siguiente, enviar, dormir, señal);
  }
}

/** Procesa UN item. Util para tests y para reintentos manuales. */
export async function intentarUnaVez(
  store: StoreOutbox,
  item: ItemOutbox,
  enviar: EndpointOutbox,
  dormir: Dormir = dormirDefault,
  señal?: AbortSignal,
): Promise<boolean> {
  await store.put({
    ...item,
    estado: "enviando",
    actualizado_en: new Date().toISOString(),
  });

  try {
    await enviar(item.evento);
    await store.put({
      ...item,
      estado: "sincronizado",
      actualizado_en: new Date().toISOString(),
      ultimo_error: null,
    });
    return true;
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : String(error);
    const intentos = item.intentos + 1;

    if (intentos >= MAX_INTENTOS) {
      await store.put({
        ...item,
        estado: "fallido",
        intentos,
        actualizado_en: new Date().toISOString(),
        ultimo_error: mensaje,
      });
      return false;
    }

    await store.put({
      ...item,
      estado: "pendiente",
      intentos,
      actualizado_en: new Date().toISOString(),
      ultimo_error: mensaje,
    });
    await dormir(DELAYS_MS[intentos - 1] ?? DELAYS_MS.at(-1) ?? 16_000);
    if (señal?.aborted) return false;
    return false;
  }
}

/** Helper para tests: adapter en memoria sobre un Map. */
export function storeEnMemoria(
  inicial: ItemOutbox[] = [],
): StoreOutbox & { _items: Map<string, ItemOutbox> } {
  const items = new Map<string, ItemOutbox>();
  for (const it of inicial) items.set(it.id, it);
  return {
    _items: items,
    async get(id) {
      return items.get(id);
    },
    async put(item) {
      items.set(item.id, item);
    },
    async delete(id) {
      items.delete(id);
    },
    async firstPendiente() {
      // FIFO: el item mas viejo primero.
      let oldest: ItemOutbox | undefined;
      for (const item of items.values()) {
        if (item.estado !== "pendiente") continue;
        if (!oldest || item.creado_en < oldest.creado_en) oldest = item;
      }
      return oldest;
    },
    async clear() {
      items.clear();
    },
  };
}
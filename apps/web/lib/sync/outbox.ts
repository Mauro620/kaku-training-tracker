/**
 * Capa de adaptacion Dexie del nucleo de la cola (Fase 5).
 *
 * La logica de reintentos, estados y delays vive en `nucleo.ts` (pura, testeable
 * sin IndexedDB). Este archivo es la cara que la app usa: persistir en
 * Dexie, exponer helpers para la UI, construir el endpoint desde `api`.
 *
 * Sesion lleva sus bloques anidados en el mismo POST (no hay endpoint
 * separado para bloques), asi que la cola ve "un evento = un envio" para
 * las 6 entidades por igual.
 */

import { db } from "@/lib/db/dexie";
import {
  intentarUnaVez,
  procesar,
  type Dormir,
  type EndpointOutbox,
  type ProcesarOpciones,
} from "@/lib/sync/nucleo";
import type { EstadoOutbox, EventoOutbox, ItemOutbox } from "@/lib/sync/tipos";

export {
  type Dormir,
  type EndpointOutbox,
  type ProcesarOpciones,
} from "@/lib/sync/nucleo";
export {
  MAX_INTENTOS,
  tipoEvento,
  type EventoOutbox,
  type ItemOutbox,
  type EstadoOutbox,
} from "@/lib/sync/tipos";

// Adaptador Dexie -> StoreOutbox. La cola lee/escribe via este objeto.
const adaptador = {
  async get(id: string) {
    return db.table<ItemOutbox>("outbox").get(id);
  },
  async put(item: ItemOutbox) {
    await db.table<ItemOutbox>("outbox").put(item);
  },
  async delete(id: string) {
    await db.table<ItemOutbox>("outbox").delete(id);
  },
  async firstPendiente() {
    return db.table<ItemOutbox>("outbox")
      .where("estado")
      .equals("pendiente")
      .first();
  },
  async clear() {
    await db.table<ItemOutbox>("outbox").clear();
  },
};

/**
 * Encola un evento para envio. Devuelve el id del item para que la UI
 * pueda mostrar el estado.
 */
export async function encolar(
  evento: EventoOutbox,
  opciones: { sesionLocalId?: string } = {},
): Promise<string> {
  const ahora = new Date().toISOString();
  const id = crypto.randomUUID();
  const item: ItemOutbox = {
    id,
    estado: "pendiente",
    intentos: 0,
    creado_en: ahora,
    actualizado_en: ahora,
    ultimo_error: null,
    evento,
    sesion_local_id: opciones.sesionLocalId,
  };
  await adaptador.put(item);
  return id;
}

/** Devuelve todos los items en cualquier estado, ordenados por creacion. */
export async function listar(): Promise<ItemOutbox[]> {
  return db.table<ItemOutbox>("outbox").orderBy("creado_en").toArray();
}

/** Cuenta items pendientes o en envio (lo que la UI muestra como "sincronizando"). */
export async function contarPendientes(): Promise<number> {
  return db.table<ItemOutbox>("outbox")
    .where("estado")
    .anyOf(["pendiente", "enviando"])
    .count();
}

/** Cuenta items en estado fallido (lo que la UI muestra como "fallidos"). */
export async function contarFallidos(): Promise<number> {
  return db.table<ItemOutbox>("outbox").where("estado").equals("fallido").count();
}

/** Borra un item de la cola. */
export async function descartar(id: string): Promise<void> {
  await adaptador.delete(id);
}

/** Vuelve a poner en cola un item `fallido` para reintentar manualmente. */
export async function reintentar(id: string): Promise<void> {
  const item = await adaptador.get(id);
  if (!item) return;
  if (item.estado !== "fallido") return;
  await adaptador.put({
    ...item,
    estado: "pendiente",
    intentos: 0,
    ultimo_error: null,
    actualizado_en: new Date().toISOString(),
  });
}

/** Procesa toda la cola con el endpoint dado. Ver `procesar` en nucleo.ts. */
export async function procesarCola(
  enviar: EndpointOutbox,
  opciones: ProcesarOpciones = {},
): Promise<void> {
  await procesar(adaptador, enviar, opciones);
}

/** Procesa UN item. Util para reintentos forzados. */
export async function enviarUnaVez(
  id: string,
  enviar: EndpointOutbox,
): Promise<EstadoOutbox> {
  const item = await adaptador.get(id);
  if (!item) throw new Error(`outbox item ${id} no existe`);
  await intentarUnaVez(adaptador, item, enviar);
  const actualizado = await adaptador.get(id);
  return actualizado?.estado ?? "sincronizado";
}

/**
 * Construye el `EndpointOutbox` para la app real, usando `api` del cliente
 * HTTP (`apps/web/lib/api/client.ts`). Ese cliente ya arma la URL completa
 * a partir de `NEXT_PUBLIC_API_URL` (que incluye `/api/v1`), asi que las
 * rutas de aca son relativas, iguales a las que usan los hooks de
 * `lib/api/hooks.ts`. La cola queda desacoplada del cliente: tests pasan
 * un mock.
 */
export function endpointDesdeApi(api: {
  post: <T>(path: string, cuerpo: unknown) => Promise<T>;
}): EndpointOutbox {
  return async (evento) => {
    switch (evento.tipo) {
      case "sueno":
        await api.post("/sueno", evento.cuerpo);
        return;
      case "bienestar":
        await api.post("/bienestar", evento.cuerpo);
        return;
      case "hidratacion":
        await api.post("/hidratacion", evento.cuerpo);
        return;
      case "habito_registro":
        await api.post("/habitos/registro", evento.cuerpo);
        return;
      case "molestia":
        await api.post("/molestias", evento.cuerpo);
        return;
      case "sesion":
        // Bloques anidados en el mismo POST (SesionCreate.bloques): no hay
        // endpoint separado para crearlos.
        await api.post("/sesiones", {
          ...evento.cuerpo.sesion,
          bloques: evento.cuerpo.bloques,
        });
        return;
    }
  };
}

/**
 * Suscribe a cambios de la cola. La UI lo usa para refrescar el chip de
 * sincronizacion cuando se encola, sincroniza o falla algo.
 *
 * Implementacion: poll cada 1s. Dexie soporta `liveQuery` (reactivo) pero
 * requiere hook en el cliente. Un poll simple es suficiente para el chip.
 */
export function suscribir(
  callback: (items: ItemOutbox[]) => void,
): () => void {
  const handler = async () => {
    const items = await db.table<ItemOutbox>("outbox").orderBy("creado_en").toArray();
    callback(items);
  };
  const interval = setInterval(handler, 1_000);
  void handler();
  return () => clearInterval(interval);
}
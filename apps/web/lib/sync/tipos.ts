/**
 * Tipos compartidos entre la cola (outbox.ts) y el schema Dexie (db/dexie.ts).
 *
 * Viven en un archivo aparte para evitar un import circular: la cola
 * referencia los `Captura*` de Dexie, y Dexie referencia `ItemOutbox` de la
 * cola.
 */

import type { CapturaBloque, CapturaSesion } from "@/lib/db/dexie";

export const MAX_INTENTOS = 5;

/** Estados posibles de un item de la cola. */
export type EstadoOutbox = "pendiente" | "enviando" | "sincronizado" | "fallido";

// Re-export para que la cola pueda nombrar `CapturaBloque` sin importar
// directamente de db/dexie (rompe el ciclo).
export type { CapturaBloque, CapturaSesion };

/**
 * Las 6 mutaciones que van a la cola. El switch de envio esta en
 * `endpointDesdeApi` (en outbox.ts). Si se agrega una entidad nueva con
 * outbox, hay que sumar el caso aca y en el switch.
 */
export type EventoOutbox =
  | { tipo: "sueno"; cuerpo: CapturaSuenoBody }
  | { tipo: "bienestar"; cuerpo: CapturaBienestarBody }
  | { tipo: "hidratacion"; cuerpo: CapturaHidratacionBody }
  | { tipo: "habito_registro"; cuerpo: CapturaHabitoBody }
  | { tipo: "molestia"; cuerpo: CapturaMolestiaBody }
  | { tipo: "sesion"; cuerpo: CapturaSesionBody };

export type CapturaSuenoBody = {
  fecha: string;
  inicio: string;
  fin: string;
  celular_fuera: boolean | null;
  origen: string;
  idempotency_key: string;
};

export type CapturaBienestarBody = {
  fecha: string;
  sueno_pobre: number;
  fatiga: number;
  dolor_muscular: number;
  estres: number;
  idempotency_key: string;
};

export type CapturaHidratacionBody = {
  fecha: string;
  cantidad_ml: number;
  idempotency_key: string;
};

export type CapturaHabitoBody = {
  habito_id: number;
  fecha: string;
  valor: boolean;
  idempotency_key: string;
};

export type CapturaMolestiaBody = {
  fecha: string;
  zona_id: number;
  intensidad: number;
  nota: string | null;
  idempotency_key: string;
};

/** Sesion con bloques. El backend espera POST sesion + POST bloques
 * separados (no hay endpoint anidado). La cola lo maneja como "un
 * evento = N envios" en `endpointDesdeApi`. */
export type CapturaSesionBody = {
  sesion: {
    id: string;
    fecha: string;
    tipo_sesion_id: number;
    duracion_min: number;
    rpe: number;
    nota: string | null;
    idempotency_key: string;
  };
  bloques: CapturaBloque[];
};

/** Item persistido en la tabla `outbox` de Dexie. */
export interface ItemOutbox {
  /** UUID del item. No confundir con la key del cuerpo. */
  id: string;
  estado: EstadoOutbox;
  /** Cuantas veces se intento enviar. 0 recien encolado. */
  intentos: number;
  /** ISO cuando se encolo por primera vez. */
  creado_en: string;
  /** ISO del ultimo envio (sea exito o fallo). */
  actualizado_en: string;
  /** Ultimo error, si hubo. */
  ultimo_error: string | null;
  evento: EventoOutbox;
  // Referencia para rehidratar `CapturaSesion` desde el `outbox`: si el tipo
  // es "sesion", la sesion y sus bloques ya estan en `db.sesion` con la
  // misma `idempotency_key`. Guardamos el id para borrar de ahi al sync.
  sesion_local_id?: string;
}
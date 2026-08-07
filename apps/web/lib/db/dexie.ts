/**
 * Schema Dexie espejo de las entidades de captura.
 *
 * El cliente escribe primero aca (offline-first) y la cola de salida (en
 * `apps/web/lib/sync/outbox.ts`) sincroniza con el backend. Cada entity local
 * lleva `idempotency_key` generado por el cliente con `crypto.randomUUID()`:
 * es la llave que el backend usa para hacer upsert idempotente.
 *
 * El espejo no es 1-a-1 con el backend: guardamos lo minimo para reconstruir
 * la UI antes de tener red. Las columnas calculadas del backend (horas_sueno,
 * hooper, carga_srpe) NO se persisten aca; se recalculan en el cliente solo
 * si la UI las necesita y se refrescan al sincronizar.
 */

import Dexie, { type Table } from "dexie";

/** Registro de sueno en el cliente. Espejo de `registro_sueno`. */
export interface CapturaSueno {
  fecha: string; // ISO YYYY-MM-DD
  inicio: string; // ISO timestamptz
  fin: string;
  celular_fuera: boolean | null;
  origen: string;
  idempotency_key: string;
}

/** Registro de bienestar en el cliente. Espejo de `registro_bienestar`. */
export interface CapturaBienestar {
  fecha: string;
  sueno_pobre: number;
  fatiga: number;
  dolor_muscular: number;
  estres: number;
  idempotency_key: string;
}

/** Tap de hidratacion. Espejo de la fila agregada en `registro_hidratacion`. */
export interface CapturaHidratacion {
  /** ISO YYYY-MM-DD. La fila backend tiene UNIQUE (usuario_id, fecha). */
  fecha: string;
  /** Cantidad de ESTE tap. El backend suma a `ml_totales`. */
  cantidad_ml: number;
  idempotency_key: string;
}

/** Registro de un habito en una fecha. Espejo de `habito_registro`. */
export interface CapturaHabitoRegistro {
  habito_id: number;
  fecha: string;
  valor: boolean;
  idempotency_key: string;
}

/** Molestia. Espejo de `molestia`. */
export interface CapturaMolestia {
  fecha: string;
  zona_id: number;
  intensidad: number;
  nota: string | null;
  idempotency_key: string;
}

/** Sesion de entrenamiento con bloques. Espejo de `sesion` + `bloque`. */
export interface CapturaSesion {
  /** UUID generado por el cliente. */
  id: string;
  fecha: string;
  tipo_sesion_id: number;
  duracion_min: number;
  rpe: number;
  nota: string | null;
  bloques: CapturaBloque[];
  idempotency_key: string;
}

export interface CapturaBloque {
  id: string;
  sesion_id: string;
  ejercicio_id: number;
  /** 1-based; se calcula en el cliente al armar la sesion. */
  numero: number;
  /** Carga | Distancia | Tiempo | Tecnica, segun `ejercicio.tipo_medicion`. */
  peso_kg: number | null;
  distancia_m: number | null;
  tiempo_s: number | null;
  repeticiones: number | null;
  /** Solo para tipos tecnica: texto libre. */
  nota: string | null;
  rpe: number | null;
}

export class DexieCapturas extends Dexie {
  sueno!: Table<CapturaSueno, string>;
  bienestar!: Table<CapturaBienestar, string>;
  hidratacion!: Table<CapturaHidratacion, string>;
  habito_registro!: Table<CapturaHabitoRegistro, string>;
  molestia!: Table<CapturaMolestia, string>;
  sesion!: Table<CapturaSesion, string>;

  constructor() {
    super("training_tracker");
    // Las primary keys son la clave idempotente: cada intento del cliente es
    // unico por su UUID. La unicidad natural del backend (ej. usuario+fecha)
    // se valida ahi; aca el cliente nunca intenta deduplicar dos keys
    // distintas, solo guarda el intento.
    //
    // Las secundarias son los indices que la UI consulta antes de sincronizar
    // (ej. "traeme el sueno de hoy").
    this.version(1).stores({
      sueno: "&idempotency_key, fecha",
      bienestar: "&idempotency_key, fecha",
      hidratacion: "&idempotency_key, fecha",
      habito_registro: "&[habito_id+fecha], idempotency_key, fecha",
      molestia: "&idempotency_key, fecha, zona_id",
      sesion: "&id, idempotency_key, fecha",
    });
  }
}

export const db = new DexieCapturas();
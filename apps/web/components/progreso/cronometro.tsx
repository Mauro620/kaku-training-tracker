"use client";

import { useEffect, useRef, useState } from "react";
import { Flag, Play, Square } from "lucide-react";

/**
 * Cronometro para capturar intentos de tiempo (ej. RSA 6x30m): arrancar
 * una vez, "Marcar" registra el split actual como intento y reinicia el
 * conteo sin detener el reloj, "Detener" para. Solo tiene sentido para
 * tipo_test.unidad === "s"; los tests de distancia usan input numerico
 * directo (ver RegistrarTestCard).
 */
export function Cronometro({ onMarcar }: { onMarcar: (segundos: number) => void }) {
  const [corriendo, setCorriendo] = useState(false);
  const [transcurridoMs, setTranscurridoMs] = useState(0);
  const inicioRef = useRef<number | null>(null);

  useEffect(() => {
    if (!corriendo) return;
    const interval = setInterval(() => {
      if (inicioRef.current !== null) {
        setTranscurridoMs(Date.now() - inicioRef.current);
      }
    }, 50);
    return () => clearInterval(interval);
  }, [corriendo]);

  function iniciar() {
    inicioRef.current = Date.now();
    setTranscurridoMs(0);
    setCorriendo(true);
  }

  function marcar() {
    if (inicioRef.current === null) return;
    const segundos = (Date.now() - inicioRef.current) / 1000;
    onMarcar(Math.round(segundos * 1000) / 1000);
    inicioRef.current = Date.now();
    setTranscurridoMs(0);
  }

  function detener() {
    setCorriendo(false);
    inicioRef.current = null;
    setTranscurridoMs(0);
  }

  return (
    <div className="flex items-center gap-3 rounded-bento bg-canvas px-4 py-3">
      <span className="flex-1 text-[24px] font-bold tabular text-text-primary">
        {(transcurridoMs / 1000).toFixed(2)}s
      </span>
      {!corriendo ? (
        <button
          type="button"
          onClick={iniciar}
          className="flex items-center gap-1 rounded-pill bg-text-primary px-4 py-2 text-[13px] font-semibold text-canvas"
        >
          <Play size={14} /> Iniciar
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={marcar}
            className="flex items-center gap-1 rounded-pill bg-text-primary px-4 py-2 text-[13px] font-semibold text-canvas"
          >
            <Flag size={14} /> Marcar
          </button>
          <button
            type="button"
            onClick={detener}
            aria-label="Detener"
            className="p-2 text-text-secondary"
          >
            <Square size={16} />
          </button>
        </>
      )}
    </div>
  );
}

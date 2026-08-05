"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api/client";
import { guardarTokens } from "@/lib/auth";

/**
 * Pantalla de login (Fase 3 entrada a la app).
 * Form centrado, dos campos, submit contra el api. Sin loader elaborate:
 * el botón cambia su texto a "Entrando..." mientras la promesa está en vuelo.
 */
export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const respuesta = await api.post<{ access_token: string; refresh_token: string }>(
        "/auth/login",
        { email, password },
        { conAuth: false },
      );
      guardarTokens(respuesta.access_token, respuesta.refresh_token);
      router.replace("/hoy");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Credenciales inválidas.");
      } else {
        setError("No pude conectar con el servidor.");
      }
    } finally {
      setCargando(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6">
      <h1 className="text-[32px] font-bold tracking-tight text-text-primary">Rendimiento</h1>
      <p className="mt-2 text-[14px] text-text-secondary">Iniciá sesión para registrar tu día.</p>

      <form onSubmit={onSubmit} className="mt-10 flex flex-col gap-4">
        <label className="flex flex-col gap-2">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="bg-surface-secondary rounded-pill px-5 py-3 text-[15px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">
            Contraseña
          </span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="bg-surface-secondary rounded-pill px-5 py-3 text-[15px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>

        {error && (
          <p role="alert" className="text-[13px] text-state-danger">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={cargando}
          className="mt-2 bg-text-primary text-canvas rounded-pill py-3 text-[15px] font-semibold disabled:opacity-50"
        >
          {cargando ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}

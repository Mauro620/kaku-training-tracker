import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  // El display=swap es la única opción razonable acá: la fuente no debería
  // bloquear la primera pintura de la pantalla Hoy.
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Rendimiento",
  description: "Registro diario de entrenamiento, sueño, hábitos y nutrición.",
};

export const viewport: Viewport = {
  themeColor: "#09090B",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={inter.variable}>
      <body className="bg-canvas text-text-primary antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}

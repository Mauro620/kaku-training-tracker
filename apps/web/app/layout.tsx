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
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icons/apple-touch-icon.png",
  },
  appleWebApp: {
    // iOS no lee el manifest para "Agregar a inicio": necesita estas meta
    // tags propias. black-translucent deja el contenido correr debajo de
    // la barra de estado, que es justo el "sin bordes" que pide DESIGN.md.
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Rendimiento",
  },
};

export const viewport: Viewport = {
  themeColor: "#09090B",
  width: "device-width",
  initialScale: 1,
  // Bloqueo el zoom para que la PWA se sienta como app nativa: pinch
  // sobre cualquier boton rompe la jerarquia visual y un usuario
  // desesperado termina persiguiendo un input por toda la pantalla.
  // Accesibilidad: este producto no tiene bloques largos de lectura,
  // la interaccion es de captura (formularios). El argumento clasico
  // contra bloquear el zoom aplica a articulos y documentacion, no a
  // una UI de botones y checklists.
  maximumScale: 1,
  userScalable: false,
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

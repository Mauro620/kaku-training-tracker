import type { Config } from "tailwindcss";

// Los tokens del DESIGN.md se exponen como CSS vars en globals.css. Tailwind
// los consume acá para que las clases (`bg-canvas`, `text-primary`, etc.)
// reflejen los valores del documento y no haya colores hardcoded en JSX.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        surface: {
          primary: "var(--surface-primary)",
          secondary: "var(--surface-secondary)",
        },
        border: {
          subtle: "var(--border-subtle)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
        },
        state: {
          positive: "var(--state-positive)",
          warning: "var(--state-warning)",
          danger: "var(--state-danger)",
          focus: "var(--state-focus)",
        },
      },
      borderRadius: {
        bento: "var(--radius-bento)",
        pill: "var(--radius-pill)",
        modal: "var(--radius-modal)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;

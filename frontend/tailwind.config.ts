import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme palette
        bg: "#0a0e1a",
        surface: "#111827",
        border: "#1f2937",
        muted: "#374151",
        // Node type colors
        "node-event": "#7c3aed",
        "node-metric": "#0d9488",
        "node-entity": "#ea580c",
        "node-policy": "#1d4ed8",
      },
    },
  },
  plugins: [],
};
export default config;

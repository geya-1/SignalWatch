import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Groww-inspired palette: deep forest green primary, soft off-white
        // background, subtle rounded cards.
        primary: {
          DEFAULT: "#00875A",
          light: "#E8F5EF",
          dark: "#006A46",
        },
        surface: "#FFFFFF",
        background: "#F7F9F8",
        danger: "#D64545",
        muted: "#6B7280",
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
      },
      keyframes: {
        fadein: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(0,135,90,0.35)" },
          "50%": { boxShadow: "0 0 0 8px rgba(0,135,90,0)" },
        },
      },
      animation: {
        fadein: "fadein 0.25s ease-out",
        glow: "glow 1.4s ease-in-out 2",
      },
    },
  },
  plugins: [],
};

export default config;

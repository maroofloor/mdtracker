import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0a0a0c",
          800: "#0d0d11",
          700: "#121218",
          600: "#16161d",
          500: "#1c1c24",
          400: "#26262f",
        },
        teal: {
          DEFAULT: "#00e5c0",
          bright: "#2ff0d2",
          deep: "#0bbfa2",
          ink: "#04201b",
        },
        mute: {
          DEFAULT: "#8a8a95",
          soft: "#6a6a74",
        },
      },
      fontFamily: {
        sans: ["var(--font-noto)", "system-ui", "sans-serif"],
        display: ["var(--font-rajdhani)", "var(--font-noto)", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "grid-pan": {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "60px 60px" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.7s cubic-bezier(0.22,1,0.36,1) both",
        "grid-pan": "grid-pan 8s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;

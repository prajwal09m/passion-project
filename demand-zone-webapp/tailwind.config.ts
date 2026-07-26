import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces — descending depth. Bloomberg/TradingView-flavored, flatter.
        ink: {
          950: "#08090b",
          900: "#0c0d10",
          850: "#101216",
          800: "#15171c",
          700: "#1c1f26",
          600: "#262a33",
          500: "#343943",
        },
        line: {
          DEFAULT: "#1f222a",
          strong: "#2b2f38",
          faint: "#15171c",
        },
        // Text hierarchy. NOT for data — only chrome.
        fg: {
          DEFAULT: "#e6e8ee",
          muted: "#9ba1ad",
          subtle: "#6b7180",
          dim: "#464a55",
        },
        // Sentiment palette — only used to communicate meaning.
        pos: {
          DEFAULT: "#3ecf8e",
          soft: "#1a3a2c",
          line: "#2a9d6f",
        },
        neg: {
          DEFAULT: "#ef5160",
          soft: "#3a1e22",
          line: "#b53b48",
        },
        ai: {
          DEFAULT: "#7c8cff",
          soft: "#1c2046",
          line: "#5b6cff",
        },
        warn: {
          DEFAULT: "#e0a458",
          soft: "#332618",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        // Micro labels for column headers in dense tables.
        "2xs": ["10px", { lineHeight: "12px", letterSpacing: "0.06em" }],
      },
      spacing: {
        // 4px grid; tighten default scale to support density.
        0.5: "2px",
        1.5: "6px",
        2.5: "10px",
        3.5: "14px",
      },
      borderRadius: {
        // Sharper corners, no pill buttons.
        DEFAULT: "2px",
        sm: "2px",
        md: "3px",
        lg: "4px",
      },
      transitionTimingFunction: {
        crisp: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "data-pulse": {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        "scan-x": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both",
        "data-pulse": "data-pulse 1.4s ease-in-out infinite",
        "scan-x": "scan-x 2.2s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: { DEFAULT: "#244C40", 700: "#1C3D33", 800: "#163128", 50: "#EEF3F0" },
        sage: "#E7ECE8",
        ivory: "#F3EFE5",
        champagne: { DEFAULT: "#D8C9A5", 600: "#B9A578", 100: "#F1EADA" },
        ink: { DEFAULT: "#292D2A", soft: "#4B524D", muted: "#6B726D" },
        line: "#E2E5E1",
        register: "#8E2B3A",
        danger: { DEFAULT: "#A3332B", bg: "#F8E9E7" },
        caution: { DEFAULT: "#7A5A12", bg: "#F6EEDA" },
        ok: { DEFAULT: "#2F6B4F", bg: "#E4EFE8" },
      },
      fontFamily: {
        display: ['"Tiro Telugu"', "Georgia", "serif"],
        sans: ['"Hind Guntur"', "system-ui", "sans-serif"],
      },
      boxShadow: { soft: "0 1px 2px rgba(36,76,64,0.06), 0 4px 16px rgba(36,76,64,0.05)" },
      borderRadius: { sm: "4px", DEFAULT: "6px", md: "8px", lg: "12px" },
    },
  },
  plugins: [],
};

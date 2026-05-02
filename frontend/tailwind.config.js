/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["'Plus Jakarta Sans'", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'",    "sans-serif"],
        mono:    ["'JetBrains Mono'",   "monospace"],
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#bcd4ff",
          300: "#8eb8ff",
          400: "#5991ff",
          500: "#3369f5",
          600: "#204ae0",
          700: "#1b3bb5",
          800: "#1c348f",
          900: "#1c3070",
        },
      },
    },
  },
  plugins: [],
};

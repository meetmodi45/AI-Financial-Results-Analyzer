/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brutalist: {
          bg: '#F2EBE3',
          dark: '#1A1A1A',
          orange: '#D95A2B',
          green: '#2E6F40',
        }
      }
    },
  },
  plugins: [],
}

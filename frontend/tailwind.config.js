/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // NagVis state colors
        state: {
          up: '#00ff00',
          down: '#ff0000',
          unreachable: '#ff8800',
          ok: '#00ff00',
          warning: '#ffff00',
          critical: '#ff0000',
          unknown: '#ff8800',
          pending: '#aaaaaa',
        },
      },
    },
  },
  plugins: [],
}

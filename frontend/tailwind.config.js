/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        warning: '#ffd000',
        state: {
          up: '#00ff00',
          down: '#ff0000',
          unreachable: '#ff8800',
          ok: '#00ff00',
          warning: '#ffd000',
          critical: '#ff0000',
          unknown: '#ff8800',
          pending: '#aaaaaa',
        },
        // CMK brand colors (as CSS variable references)
        'corporate-green': {
          DEFAULT: 'var(--color-corporate-green-50)',
          50: 'var(--color-corporate-green-50)',
          60: 'var(--color-corporate-green-60)',
          70: 'var(--color-corporate-green-70)',
        },
        'cmk-primary': 'var(--default-button-primary-color)',
        'cmk-bg': 'var(--default-bg-color)',
        'cmk-surface': 'var(--ux-theme-3)',
        'cmk-nav': 'var(--default-nav-bg-color)',
        'cmk-form': 'var(--default-form-element-bg-color)',
        'cmk-border': 'var(--default-border-color)',
        'cmk-text': 'var(--font-color)',
        'cmk-text-dim': 'var(--font-color-dimmed)',
      },
    },
  },
  plugins: [],
}

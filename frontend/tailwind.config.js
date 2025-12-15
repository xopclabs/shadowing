/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Spanish-inspired warm color palette
        'sol': {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        'tierra': {
          50: '#fdf4f3',
          100: '#fce7e4',
          200: '#fbd3cd',
          300: '#f7b3a9',
          400: '#f08677',
          500: '#e55a47',
          600: '#d13d29',
          700: '#af311f',
          800: '#912c1d',
          900: '#782a1e',
        },
        'noche': {
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d4d9e3',
          300: '#afb8ca',
          400: '#8491ac',
          500: '#657392',
          600: '#505c79',
          700: '#424b63',
          800: '#394053',
          900: '#333847',
          950: '#1e2029',
        },
      },
      fontFamily: {
        sans: ['Nunito', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}


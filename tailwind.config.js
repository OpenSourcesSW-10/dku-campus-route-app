/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#BE3A60',
          light: '#D98AA0',
          lighter: '#EBC0CD',
          dark: '#A32E50',
          50: '#FBEEF2',
        },
        ink: {
          DEFAULT: '#2B2B2B',
          soft: '#6B6B6B',
          faint: '#9A9A9A',
        },
        line: '#E5E5E5',
      },
      fontFamily: {
        sans: ['Pretendard', 'system-ui', 'Apple SD Gothic Neo', 'sans-serif'],
      },
      boxShadow: {
        sheet: '0 -4px 24px rgba(0,0,0,0.10)',
        card: '0 2px 12px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}

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
      keyframes: {
        'fade-in': { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'sheet-up': {
          '0%': { opacity: '0', transform: 'translateY(100%)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pop-in': {
          '0%': { opacity: '0', transform: 'scale(0.85)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'heart-beat': {
          '0%,100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.12)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease both',
        'fade-up': 'fade-up 0.45s cubic-bezier(0.22,1,0.36,1) both',
        'sheet-up': 'sheet-up 0.35s cubic-bezier(0.22,1,0.36,1) both',
        'pop-in': 'pop-in 0.3s cubic-bezier(0.34,1.56,0.64,1) both',
        'heart-beat': 'heart-beat 1.1s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

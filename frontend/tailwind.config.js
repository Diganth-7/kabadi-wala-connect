/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17221d',
        leaf: '#1f7a4d',
        mint: '#eaf7ef',
        cream: '#f7f8f4',
        amber: '#e6a23c',
      },
      boxShadow: {
        soft: '0 12px 32px rgba(23,34,29,.08)',
      },
    },
  },
  plugins: [],
}

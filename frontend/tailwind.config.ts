import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        mfu: {
          navy: '#0f172a',
          accent: '#2563eb',
        },
      },
    },
  },
  plugins: [],
} satisfies Config;

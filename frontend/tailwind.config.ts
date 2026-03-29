import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0f172a',
        slate: {
          50: '#f8fafc',
          900: '#0f172a',
        },
      },
    },
  },
  plugins: [],
}
export default config

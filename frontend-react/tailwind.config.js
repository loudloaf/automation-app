/** Sama dengan tailwind.config di index.html lama */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: { fontFamily: { sans: ['IBM Plex Sans', 'sans-serif'], mono: ['IBM Plex Mono', 'monospace'] } } },
  plugins: [],
}

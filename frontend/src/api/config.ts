// Mocks are ON by default in `npm run dev`; set VITE_USE_MOCKS=false to use the real API.
// In production, mocks are OFF unless VITE_USE_MOCKS=true is explicitly set
// (e.g. set it in Vercel env vars to run a fully standalone demo without a backend).
export const USE_MOCKS =
  import.meta.env.VITE_USE_MOCKS === 'true' ||
  (import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS !== 'false')

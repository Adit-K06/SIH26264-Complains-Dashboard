// Mocks are ON by default in `npm run dev`; set VITE_USE_MOCKS=false to use the real API.
// A production build (import.meta.env.DEV is false) can never use mocks.
export const USE_MOCKS = import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS !== 'false'

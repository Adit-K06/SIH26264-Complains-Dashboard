// Mock mode logic:
// - Explicitly forced:   VITE_USE_MOCKS=true  → always mocks
// - Explicitly real:     VITE_USE_MOCKS=false → always real API
// - Auto (dev):          dev server with no override  → mocks
// - Auto (production):   no VITE_API_BASE_URL set     → mocks (standalone demo on Vercel)
// - Auto (production):   VITE_API_BASE_URL is set     → real API

const hasExplicitOverride = import.meta.env.VITE_USE_MOCKS !== undefined
const explicitlyMocked    = import.meta.env.VITE_USE_MOCKS === 'true'
const explicitlyReal      = import.meta.env.VITE_USE_MOCKS === 'false'
const hasBackendUrl       = !!import.meta.env.VITE_API_BASE_URL

export const USE_MOCKS: boolean = hasExplicitOverride
  ? explicitlyMocked && !explicitlyReal
  : import.meta.env.DEV || !hasBackendUrl

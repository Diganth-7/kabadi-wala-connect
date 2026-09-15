// Real backend implementation (see api.ts). Swap back to
// "export * from './mock'" to return to the offline/localStorage demo.
export * from './api'

// Safety guides are static prototype content with no backend endpoint
// (see mockData.ts) — kept as-is, everything else there is unused now.
export { safetyGuides } from '../data/mockData'

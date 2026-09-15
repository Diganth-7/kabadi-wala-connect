export function readStorage<T>(key: string, fallback: T): T {
  try { const value = localStorage.getItem(key); return value ? JSON.parse(value) as T : fallback } catch { return fallback }
}
export function writeStorage<T>(key: string, value: T) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* prototype: storage can be unavailable */ }
}
export function makeId(prefix: string) { return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}` }
export function makeLotId() {
  const n = Math.floor(10000 + Math.random() * 89999)
  return `EW-2026-${n}`
}
export function formatINR(value: number) {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(value)
}
export function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-IN', { day:'2-digit', month:'short', year:'numeric' }).format(new Date(value))
}

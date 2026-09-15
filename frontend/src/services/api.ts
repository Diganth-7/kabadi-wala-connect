/**
 * api.ts
 * -------
 * Real backend client for Kabadiwala Connect. Replaces mock.ts.
 * Implements the SAME exported service objects/functions that the
 * pages already import from '../services', so no page code needs to
 * change except where the mock and real backend contracts genuinely
 * differ (documented inline below and in INTEGRATION_NOTES.md).
 *
 * Configure the backend URL via a Vite env var:
 *   VITE_API_BASE_URL=http://localhost:8000/api   (see .env.example)
 */
import type {
  Condition, Earnings, Lot, Material, Notification as Notif, PaymentMethod,
  Pickup, PickupStatus, Price, Recycler, Transaction, User,
} from '../types'

// In dev, talk to the backend on its own port (proxy-free, via CORS).
// In production, the backend serves this build itself from the same
// origin, so a relative /api path is used automatically.
const API_BASE: string = (import.meta as any).env?.VITE_API_BASE_URL
  || ((import.meta as any).env?.PROD ? '/api' : 'http://localhost:8000/api')
const TOKEN_KEY = 'kbc_token'

export function getToken() { return localStorage.getItem(TOKEN_KEY) }
export function setToken(token: string) { localStorage.setItem(TOKEN_KEY, token) }
export function clearToken() { localStorage.removeItem(TOKEN_KEY) }

export class ApiError extends Error {
  code: string
  constructor(code: string, message: string) { super(message); this.code = code }
}

/** Every backend response is {success, data} or {success:false, error:{code,message}}. */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options.headers as Record<string, string> | undefined) }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new ApiError('NETWORK_ERROR', 'Could not reach the backend. Is it running and CORS-configured?')
  }

  let body: any = null
  try { body = await res.json() } catch { /* empty body, e.g. some errors */ }

  if (!res.ok || !body || body.success === false) {
    const message = body?.error?.message || `Request failed (${res.status})`
    const code = body?.error?.code || 'ERROR'
    throw new ApiError(code, message)
  }
  return body.data as T
}

/** No real map/GPS in this prototype yet — every location field defaults here. */
function defaultLocation() { return { latitude: 12.9716, longitude: 77.5946 } } // Bengaluru

// ---------------------------------------------------------------------------
// Materials cache — Lot/Price responses only carry material_id, not the full
// Material object the frontend types expect, so we resolve it client-side.
// ---------------------------------------------------------------------------
let materialsCache: Material[] | null = null
async function getMaterialsCached(): Promise<Material[]> {
  if (materialsCache) return materialsCache
  materialsCache = await request<Material[]>('/materials')
  return materialsCache
}

function mapUser(u: any): User {
  return { id: u.id, name: u.name, phone: u.phone || u.email || '', role: u.role, language: 'en', area: undefined }
}

export const authService = {
  /** Step 1: request an OTP. In dev, backend returns `dev_otp` directly (no SMS provider). */
  async login(identifier: string): Promise<{ message: string; dev_otp?: string }> {
    return request('/auth/login', { method: 'POST', body: JSON.stringify({ identifier }) })
  },
  /** Step 2: verify OTP, store the JWT, return the user. */
  async verifyOtp(identifier: string, otp: string): Promise<User> {
    const data = await request<{ access_token: string; token_type: string; user: any }>(
      '/auth/verify-otp', { method: 'POST', body: JSON.stringify({ identifier, otp }) },
    )
    setToken(data.access_token)
    return mapUser(data.user)
  },
  async me(): Promise<User> {
    return mapUser(await request<any>('/auth/me'))
  },
  logout() { clearToken() },
}

async function mapLot(l: any): Promise<Lot> {
  const materials = await getMaterialsCached()
  const material = materials.find(m => m.id === l.material_id)
    || { id: l.material_id, name: l.material_id, display_name: l.material_id, icon: '', unit: 'kg' }
  return {
    id: l.id, client_request_id: l.id, material, estimated_weight: l.estimated_weight,
    actual_weight: l.actual_weight ?? undefined, condition: l.condition,
    estimated_value: Number(l.estimated_value), status: l.status, created_at: l.created_at,
    photo_url: l.photo_url ?? undefined,
  }
}

export const lotService = {
  async getLots(): Promise<Lot[]> {
    const lots = await request<any[]>('/lots')
    return Promise.all(lots.map(mapLot))
  },
  async getLot(id: string): Promise<Lot> {
    return mapLot(await request<any>(`/lots/${id}`))
  },
  /**
   * NOTE: the backend's LotCreateRequest deliberately has no
   * `client_request_id` or `estimated_value` field (estimated_value is
   * always server-calculated). `client_request_id` is silently dropped
   * here; it existed only for the mock's offline-dedup logic.
   */
  async createLot(input: { client_request_id?: string; material_id: string; estimated_weight: number; condition: Condition; photo_url?: string }): Promise<Lot> {
    const body = {
      material_id: input.material_id, estimated_weight: input.estimated_weight,
      condition: input.condition, photo_url: input.photo_url, location: defaultLocation(),
    }
    return mapLot(await request<any>('/lots', { method: 'POST', body: JSON.stringify(body) }))
  },
}

export const materialService = {
  async getAll(): Promise<Material[]> { return getMaterialsCached() },
}

export const priceService = {
  async getPrices(): Promise<Price[]> {
    const [prices, materials] = await Promise.all([request<any[]>('/prices'), getMaterialsCached()])
    return prices.map(p => ({
      material_id: p.material_id,
      material_name: materials.find(m => m.id === p.material_id)?.display_name || p.material_id,
      current_price: Number(p.current_price), min_price: Number(p.min_price), max_price: Number(p.max_price),
      unit: p.unit, currency: p.currency, updated_at: p.updated_at,
      history: [], // backend has no price-history endpoint yet; chart will render flat
    }))
  },
  async getPrice(materialId: string): Promise<Price> {
    const [p, materials] = await Promise.all([request<any>(`/prices/${materialId}`), getMaterialsCached()])
    return {
      material_id: p.material_id,
      material_name: materials.find(m => m.id === p.material_id)?.display_name || p.material_id,
      current_price: Number(p.current_price), min_price: Number(p.min_price), max_price: Number(p.max_price),
      unit: p.unit, currency: p.currency, updated_at: p.updated_at, history: [],
    }
  },
}

function mapRecyclerMatch(r: any): Recycler {
  return {
    recycler_id: r.recycler_id, name: r.name, distance_km: r.distance_km, buying_price: r.buying_price,
    pickup_available: r.pickup_available, authorized: r.authorized,
    accepted_materials: r.accepted_materials.map((m: any) => m.name), match_score: r.match_score,
  }
}
function mapRecyclerFull(r: any): Recycler {
  // GET /recyclers is the public directory and does NOT include
  // distance_km / buying_price / match_score — those only exist on the
  // per-lot /recyclers/match result. They default to 0 here.
  return {
    recycler_id: r.id, name: r.name, distance_km: 0, buying_price: 0,
    pickup_available: r.pickup_available, authorized: r.authorized,
    accepted_materials: r.accepted_materials.map((m: any) => m.name), match_score: 0,
  }
}

export const recyclerService = {
  /**
   * IMPORTANT CONTRACT CHANGE: the mock matched by material *name*.
   * The real backend's GET /recyclers/match requires a `lot_id` (it
   * ranks recyclers against one specific lot's material/location), so
   * this now takes a lot id. Falls back to the full directory if no
   * lot id is available yet.
   */
  async findMatches(lotId?: string): Promise<Recycler[]> {
    if (!lotId) return recyclerService.getAll()
    const matches = await request<any[]>(`/recyclers/match?lot_id=${encodeURIComponent(lotId)}`)
    return matches.map(mapRecyclerMatch)
  },
  async getAll(): Promise<Recycler[]> {
    const recyclers = await request<any[]>('/recyclers')
    return recyclers.filter((r: any) => r.authorized).map(mapRecyclerFull)
  },
}

function mapPickup(p: any): Pickup {
  return { id: p.id, lot_id: p.lot_id, recycler_id: p.recycler_id, status: p.status, created_at: p.created_at, updated_at: p.updated_at }
}

export const pickupService = {
  async createPickup(lotId: string, recyclerId: string): Promise<Pickup> {
    const body = { lot_id: lotId, recycler_id: recyclerId, pickup_location: defaultLocation() }
    return mapPickup(await request<any>('/pickups', { method: 'POST', body: JSON.stringify(body) }))
  },
  async getPickup(id: string): Promise<Pickup> {
    return mapPickup(await request<any>(`/pickups/${id}`))
  },
  async updateStatus(id: string, status: PickupStatus): Promise<Pickup> {
    return mapPickup(await request<any>(`/pickups/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }))
  },
  async getPickups(): Promise<Pickup[]> {
    return (await request<any[]>('/pickups')).map(mapPickup)
  },
}

export const transactionService = {
  async getTransactions(): Promise<Transaction[]> {
    const list = await request<any[]>('/transactions')
    return list.map((t: any) => ({
      id: t.id, lot_id: t.lot_id, material: t.material, weight: t.weight, amount: Number(t.amount),
      payment_method: t.payment_method, payment_status: t.payment_status, created_at: t.created_at,
    }))
  },
  /**
   * IMPORTANT CONTRACT CHANGE: there is no POST /transactions endpoint.
   * The backend auto-creates a transaction when a handover completes
   * (see handoverService.complete). This method is kept only so
   * Payment.tsx's existing call still resolves — it looks up the
   * transaction the handover already created instead of making one.
   */
  async createTransaction(input: { lotId: string; material?: string; weight?: number; amount?: number; payment_method?: PaymentMethod; payment_status?: string }): Promise<Transaction> {
    const list = await transactionService.getTransactions()
    const tx = list.find(t => t.lot_id === input.lotId)
    if (!tx) throw new ApiError('TRANSACTION_NOT_FOUND', 'No transaction found for this lot yet — complete the handover first.')
    return tx
  },
}

export const paymentService = {
  async pay(transactionId: string, method: PaymentMethod, shouldFail = false) {
    const p = await request<any>('/payments', {
      method: 'POST',
      body: JSON.stringify({ transaction_id: transactionId, method, simulate_failure: shouldFail }),
    })
    return { id: p.id, transaction_id: p.transaction_id, method: p.method, amount: Number(p.amount), status: p.status, paid_at: p.updated_at }
  },
}

export const notificationService = {
  async getNotifications(): Promise<Notif[]> {
    const list = await request<any[]>('/notifications')
    return list.map((n: any) => ({ id: n.id, title: n.title, message: n.message, type: n.type, read: n.read, created_at: n.created_at }))
  },
  async markRead(id: string): Promise<Notif> {
    const n = await request<any>(`/notifications/${id}/read`, { method: 'PATCH' })
    return { id: n.id, title: n.title, message: n.message, type: n.type, read: n.read, created_at: n.created_at }
  },
}

export const handoverService = {
  async complete(input: { lotId: string; pickupId: string; actualWeight: number; agreedPrice: number; verificationReference: string }) {
    const body = {
      lot_id: input.lotId, pickup_id: input.pickupId, actual_weight: input.actualWeight,
      agreed_price: input.agreedPrice, verification_reference: input.verificationReference,
    }
    const h = await request<any>('/handovers', { method: 'POST', body: JSON.stringify(body) })
    return {
      id: h.id, lot_id: h.lot_id, pickup_id: h.pickup_id, estimated_weight: h.estimated_weight,
      actual_weight: h.actual_weight, agreed_price: Number(h.agreed_price), final_amount: Number(h.final_amount),
      verification_reference: h.verification_reference, status: 'COMPLETED' as const, created_at: h.created_at,
    }
  },
}

export const earningsService = {
  async get(): Promise<Earnings> { return request<Earnings>('/earnings') },
}

export const adminService = {
  async dashboard() { return request<any>('/admin/dashboard') },
  async collectors() { return request<any[]>('/admin/collectors') },
  async recyclers() { return request<any[]>('/admin/recyclers') },
}

export type UserRole = 'COLLECTOR' | 'RECYCLER' | 'ADMIN'
export type Language = 'en' | 'hi' | 'mr'
export type Condition = 'GOOD' | 'MIXED' | 'DAMAGED'
export type PaymentMethod = 'UPI' | 'CASH'
export type PaymentStatus = 'PENDING' | 'PAID' | 'FAILED' | 'DISPUTED'
export type LotStatus = 'DRAFT' | 'CREATED' | 'PICKUP_REQUESTED' | 'ACCEPTED' | 'HANDOVER' | 'COMPLETED' | 'CANCELLED'
export type PickupStatus = 'REQUESTED' | 'ACCEPTED' | 'ASSIGNED' | 'ON_THE_WAY' | 'ARRIVED' | 'HANDOVER' | 'COMPLETED' | 'CANCELLED'

export interface User {
  id: string; name: string; phone: string; role: UserRole; language: Language; area?: string
}
export interface Material {
  id: string; name: string; display_name: string; icon: string; unit: string
}
export interface Price {
  material_id: string; material_name: string; current_price: number; min_price: number; max_price: number; unit: string; currency: string; updated_at: string; history: number[]
}
export interface Lot {
  id: string; client_request_id: string; material: Material; estimated_weight: number; actual_weight?: number; condition: Condition; estimated_value: number; status: LotStatus; created_at: string; photo_url?: string; pendingSync?: boolean
}
export interface Recycler {
  recycler_id: string; name: string; distance_km: number; buying_price: number; pickup_available: boolean; authorized: boolean; accepted_materials: string[]; match_score: number
}
export interface Pickup {
  id: string; lot_id: string; recycler_id: string; status: PickupStatus; created_at: string; updated_at: string
}
export interface Handover {
  id: string; lot_id: string; pickup_id: string; estimated_weight: number; actual_weight: number; agreed_price: number; final_amount: number; verification_reference: string; status: 'COMPLETED'; created_at: string
}
export interface Transaction {
  id: string; lot_id: string; material: string; weight: number; amount: number; payment_method: PaymentMethod; payment_status: PaymentStatus; created_at: string
}
export interface Notification {
  id: string; title: string; message: string; type: string; read: boolean; created_at: string
}
export interface Earnings { today: number; this_week: number; this_month: number; pending: number; currency: string }
export interface AppError { code: string; message: string }
export interface SafetyGuide { material: string; dangerous_actions: string[]; safe_actions: string[] }
export interface DemoState {
  draft: { photoUrl?: string; materialId?: string; weight?: number; condition?: Condition }
  selectedLotId?: string
  selectedRecyclerId?: string
  selectedPickupId?: string
  handover?: { actualWeight: number; agreedPrice: number; verificationReference: string }
  payment?: { method: PaymentMethod; status: PaymentStatus }
}

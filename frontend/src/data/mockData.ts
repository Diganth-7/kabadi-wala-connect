import type { Earnings, Lot, Material, Notification, Price, Recycler, SafetyGuide, Transaction, User } from '../types'

export const mockUser: User = { id: 'USR001', name: 'Demo Collector', phone: '9876543210', role: 'COLLECTOR', language: 'en', area: 'Bengaluru' }

export const materials: Material[] = [
  ['MAT001','Copper','copper','kg'], ['MAT002','Aluminium','aluminium','kg'], ['MAT003','PCB','pcb','kg'],
  ['MAT004','LCD','lcd','kg'], ['MAT005','CRT','crt','kg'], ['MAT006','Battery','battery','kg'],
  ['MAT007','Cable','cable','kg'], ['MAT008','Plastic','plastic','kg'], ['MAT009','Other','other','kg'],
].map(([id,name,icon,unit]) => ({ id, name, display_name: name, icon, unit }))

export const prices: Price[] = [
  { material_id:'MAT001', material_name:'Copper', current_price:650, min_price:620, max_price:680, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[590,610,625,615,640,630,650] },
  { material_id:'MAT002', material_name:'Aluminium', current_price:180, min_price:165, max_price:195, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[160,168,171,175,170,182,180] },
  { material_id:'MAT003', material_name:'PCB', current_price:420, min_price:380, max_price:460, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[360,390,380,410,405,430,420] },
  { material_id:'MAT004', material_name:'LCD', current_price:210, min_price:190, max_price:235, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[195,200,188,205,215,208,210] },
  { material_id:'MAT005', material_name:'CRT', current_price:80, min_price:65, max_price:95, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[70,72,68,75,82,79,80] },
  { material_id:'MAT006', material_name:'Battery', current_price:105, min_price:90, max_price:120, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[92,96,98,100,108,103,105] },
  { material_id:'MAT007', material_name:'Cable', current_price:310, min_price:285, max_price:330, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[280,292,300,305,295,320,310] },
  { material_id:'MAT008', material_name:'Plastic', current_price:45, min_price:35, max_price:55, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[40,42,38,43,46,44,45] },
  { material_id:'MAT009', material_name:'Other', current_price:35, min_price:25, max_price:45, unit:'kg', currency:'INR', updated_at:'2026-09-09T14:00:00Z', history:[30,31,29,34,33,36,35] },
]

export const recyclers: Recycler[] = [
  { recycler_id:'REC001', name:'Green Recycling Pvt Ltd', distance_km:4.2, buying_price:650, pickup_available:true, authorized:true, accepted_materials:['Copper','Aluminium','PCB'], match_score:92 },
  { recycler_id:'REC002', name:'EcoLoop Materials', distance_km:7.1, buying_price:660, pickup_available:true, authorized:true, accepted_materials:['Copper','Cable','PCB','Plastic'], match_score:89 },
  { recycler_id:'REC003', name:'Bengaluru E-Waste Hub', distance_km:5.4, buying_price:640, pickup_available:false, authorized:true, accepted_materials:['Copper','Aluminium','LCD','CRT','Battery'], match_score:86 },
  { recycler_id:'REC004', name:'City Scrap Traders', distance_km:3.1, buying_price:675, pickup_available:true, authorized:false, accepted_materials:['Copper','Aluminium'], match_score:70 },
]

export const seedLots: Lot[] = [
  { id:'EW-2026-00121', client_request_id:'LOCAL-SEED-121', material:materials[1], estimated_weight:18, condition:'MIXED', estimated_value:3240, status:'PICKUP_REQUESTED', created_at:'2026-09-08T11:00:00Z' },
  { id:'EW-2026-00118', client_request_id:'LOCAL-SEED-118', material:materials[2], estimated_weight:8, condition:'GOOD', estimated_value:3360, status:'COMPLETED', created_at:'2026-09-07T09:30:00Z', actual_weight:8 },
]

export const seedTransactions: Transaction[] = [
  { id:'TXN001', lot_id:'EW-2026-00118', material:'PCB', weight:8, amount:3360, payment_method:'UPI', payment_status:'PAID', created_at:'2026-09-07T17:05:00Z' },
  { id:'TXN002', lot_id:'EW-2026-00105', material:'Aluminium', weight:12, amount:2160, payment_method:'CASH', payment_status:'PAID', created_at:'2026-09-04T15:10:00Z' },
  { id:'TXN003', lot_id:'EW-2026-00098', material:'Copper', weight:5, amount:3250, payment_method:'UPI', payment_status:'PENDING', created_at:'2026-09-02T13:20:00Z' },
]

export const seedNotifications: Notification[] = [
  { id:'NOT001', title:'Pickup accepted', message:'Green Recycling accepted your pickup request.', type:'PICKUP', read:false, created_at:'2026-09-09T16:00:00Z' },
  { id:'NOT002', title:'Copper price updated', message:'Copper is now ₹650/kg.', type:'PRICE', read:false, created_at:'2026-09-09T14:00:00Z' },
  { id:'NOT003', title:'Safety reminder', message:'Keep batteries dry and avoid short circuits.', type:'SAFETY', read:true, created_at:'2026-09-08T10:00:00Z' },
]

export const earnings: Earnings = { today:1840, this_week:6240, this_month:22480, pending:1200, currency:'INR' }

export const safetyGuides: SafetyGuide[] = [
  { material:'Batteries', dangerous_actions:['Do not burn','Do not puncture','Do not break open'], safe_actions:['Keep dry','Avoid short circuits','Send to authorized recycler'] },
  { material:'CRTs', dangerous_actions:['Do not smash','Do not cut glass','Do not handle broken glass bare-handed'], safe_actions:['Keep intact','Use gloves','Send to authorized e-waste recycler'] },
  { material:'Electronics', dangerous_actions:['Do not burn cables','Do not strip live equipment','Do not mix hazardous parts'], safe_actions:['Disconnect power','Keep components sorted','Use authorized recyclers'] },
  { material:'Damaged electronics', dangerous_actions:['Do not touch exposed wires','Do not charge damaged batteries','Do not dismantle unknown components'], safe_actions:['Isolate damaged items','Use protective gloves','Ask an authorized recycler'] },
]

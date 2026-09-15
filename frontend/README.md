# KABADIWALA CONNECT — Frontend Prototype

SIH 2026 · Problem Statement SIH26229

This is a frontend-only React + TypeScript + Vite prototype. It uses mock services and localStorage so the demo works without a backend.

## Stack
- React + TypeScript + Vite
- Tailwind CSS
- React Router
- Lucide React

## Run
```bash
npm install
npm run dev
```
Open the Vite URL shown in the terminal.

Production build:
```bash
npm run build
npm run preview
```

## Demo login
Phone: any 10-digit number  
OTP: `123456`

## Demo flow
Collector → Add Scrap → Photo → Copper → 10 kg → Good → Create Lot → Price → Find Recycler → Select Recycler → Request Pickup → Pickup Tracking → Handover → Payment → Earnings.

## Role demos
After login, Collector Profile has buttons to switch to Recycler or Admin demo. This is intentionally a mock role switch, not real authorization.

## Backend replacement
All mock backend behavior is isolated under `src/services/mock.ts`. Replace those implementations with FastAPI calls later while keeping the service interfaces consumed by pages.

The UI follows the supplied API contract concepts: roles, materials, prices, lots, recycler matching, pickup statuses, handover, payment statuses, transactions, earnings, notifications and safety guides.

## Prototype boundaries
- No backend
- No database
- No AI/ML
- No real authentication
- No real payment gateway
- No real maps
- QR is mock UI only and is not cryptographically secure
- Frontend validation is not a security boundary

## Offline
`navigator.onLine` drives the indicator. New lots created offline are marked `PENDING_SYNC` in localStorage. When the browser returns online the UI shows “Back online — syncing...”; the actual synchronization engine is intentionally left for the backend/integration phase.

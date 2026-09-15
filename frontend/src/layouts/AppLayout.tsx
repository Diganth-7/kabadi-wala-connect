import type React from 'react'
import { BottomNav } from '../components/BottomNav'
import { OfflineIndicator } from '../components/OfflineIndicator'
import { useApp } from '../contexts/AppContext'
export function AppLayout({children}:{children:React.ReactNode}){
 const {role}=useApp()
 return <div className="min-h-screen bg-cream pb-24"><main className="mx-auto min-h-screen max-w-6xl px-4 py-5 md:px-8">{children}</main><BottomNav/><OfflineIndicator/><div className="fixed left-4 top-4 z-30 rounded-full bg-white/90 px-3 py-1.5 text-[10px] font-bold text-gray-500 shadow-sm">PROTOTYPE · {role}</div></div>
}

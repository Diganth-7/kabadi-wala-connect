import { Home, Package, Bell, Wallet, UserCircle, LayoutDashboard, Truck, Receipt, Settings, Users, BarChart3 } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useApp } from '../contexts/AppContext'
const collector=[['/collector',Home,'Home'],['/collector/lots',Package,'Lots'],['/collector/earnings',Wallet,'Earnings'],['/collector/notifications',Bell,'Alerts'],['/collector/profile',UserCircle,'Profile']] as const
const recycler=[['/recycler',LayoutDashboard,'Dashboard'],['/recycler/requests',Package,'Requests'],['/recycler/pickups',Truck,'Pickups'],['/recycler/transactions',Receipt,'Transactions'],['/recycler/profile',Settings,'Profile']] as const
const admin=[['/admin',LayoutDashboard,'Dashboard'],['/admin/collectors',Users,'Collectors'],['/admin/recyclers',Users,'Recyclers'],['/admin/transactions',Receipt,'Transactions'],['/admin/analytics',BarChart3,'Analytics']] as const
export function BottomNav(){
 const {role}=useApp(); const location=useLocation()
 const items=role==='COLLECTOR'?collector:role==='RECYCLER'?recycler:admin
 return <nav className="fixed bottom-0 left-0 right-0 z-40 mx-auto max-w-6xl border-t border-black/5 bg-white/95 px-2 py-2 backdrop-blur md:rounded-t-3xl md:border md:bottom-3 md:left-3 md:right-3"><div className="mx-auto flex max-w-3xl justify-around">{items.map(([to,Icon,label])=>{const active=location.pathname===to;return <Link key={to} to={to} className={`flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-2 text-xs font-semibold ${active?'bg-mint text-leaf':'text-gray-500'}`}><Icon size={20}/><span>{label}</span></Link>})}</div></nav>
}

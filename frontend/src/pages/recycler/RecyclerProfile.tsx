import { UserCircle, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AppLayout } from '../../layouts/AppLayout'
import { PageHeader } from '../../components/PageHeader'
import { useApp } from '../../contexts/AppContext'
export default function RecyclerProfile(){const {setRole,logout}=useApp();const nav=useNavigate();return <AppLayout><div className="mx-auto max-w-xl"><PageHeader title="Recycler profile"/><div className="card p-6"><div className="flex items-center gap-4"><div className="rounded-full bg-mint p-4 text-leaf"><UserCircle size={40}/></div><div><div className="text-xl font-black">Green Recycling Pvt Ltd</div><div className="text-sm text-gray-500">Authorized · Bengaluru</div></div></div><div className="mt-6 space-y-2"><button className="secondary w-full" onClick={()=>{setRole('COLLECTOR');nav('/collector')}}>Switch to Collector demo</button><button className="secondary w-full" onClick={()=>{setRole('ADMIN');nav('/admin')}}>Switch to Admin demo</button><button className="danger w-full" onClick={()=>{logout();nav('/login')}}><LogOut/> Log out</button></div></div></div></AppLayout>}

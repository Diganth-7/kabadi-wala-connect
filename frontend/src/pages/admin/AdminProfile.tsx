import { Settings, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AppLayout } from '../../layouts/AppLayout'
import { PageHeader } from '../../components/PageHeader'
import { useApp } from '../../contexts/AppContext'
export default function AdminProfile(){const {setRole,logout}=useApp();const nav=useNavigate();return <AppLayout><div className="mx-auto max-w-xl"><PageHeader title="Admin profile"/><div className="card p-6"><Settings size={42} className="text-leaf"/><h2 className="mt-4 text-2xl font-black">Prototype administrator</h2><p className="mt-2 text-gray-500">Admin routes are frontend-only in this prototype.</p><div className="mt-6 space-y-2"><button className="secondary w-full" onClick={()=>{setRole('COLLECTOR');nav('/collector')}}>Switch to Collector</button><button className="secondary w-full" onClick={()=>{setRole('RECYCLER');nav('/recycler')}}>Switch to Recycler</button><button className="danger w-full" onClick={()=>{logout();nav('/login')}}><LogOut/> Log out</button></div></div></div></AppLayout>}

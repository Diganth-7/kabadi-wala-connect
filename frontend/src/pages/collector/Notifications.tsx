import { useEffect,useState } from 'react'
import { Bell, Check } from 'lucide-react'
import { AppLayout } from '../../layouts/AppLayout'
import { PageHeader } from '../../components/PageHeader'
import { notificationService } from '../../services'
import type { Notification } from '../../types'
export default function Notifications(){const [items,setItems]=useState<Notification[]>([]);useEffect(()=>{notificationService.getNotifications().then(setItems)},[]);const read=async(id:string)=>{const n=await notificationService.markRead(id);setItems(x=>x.map(i=>i.id===id?n:i))};return <AppLayout><div className="mx-auto max-w-2xl"><PageHeader title="Notifications"/><div className="space-y-3">{items.map(n=><div key={n.id} className={`card p-5 ${!n.read?'border-leaf/20 bg-mint/40':''}`}><div className="flex gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-leaf"><Bell size={19}/></div><div className="flex-1"><div className="font-black">{n.title}</div><p className="mt-1 text-sm text-gray-600">{n.message}</p><div className="mt-3 flex items-center justify-between"><span className="text-xs text-gray-400">{new Date(n.created_at).toLocaleString('en-IN')}</span>{!n.read&&<button className="secondary min-h-9 px-3 py-1 text-xs" onClick={()=>read(n.id)}><Check size={14}/> Mark read</button>}</div></div></div></div>)}</div></div></AppLayout>}

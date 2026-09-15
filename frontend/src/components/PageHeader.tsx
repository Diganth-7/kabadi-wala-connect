import { ArrowLeft, Bell } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'
export function PageHeader({title,back=true,notification=false}:{title:string;back?:boolean;notification?:boolean}){
 const nav=useNavigate()
 return <header className="mb-5 flex items-center gap-3"><div className="flex-1 flex items-center gap-3">{back&&<button onClick={()=>nav(-1)} className="rounded-full bg-white p-3 shadow-sm border border-black/5" aria-label="Back"><ArrowLeft size={20}/></button>}<h1 className="text-2xl font-extrabold tracking-tight">{title}</h1></div>{notification&&<Link to="/collector/notifications" className="rounded-full bg-white p-3 shadow-sm border border-black/5"><Bell size={20}/></Link>}</header>
}

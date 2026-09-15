import { X } from 'lucide-react'
export function Toast({message,onClose,type='error'}:{message:string;onClose:()=>void;type?:'error'|'success'|'info'}){
  return <div className={`fixed left-1/2 top-5 z-[100] flex w-[min(92vw,480px)] -translate-x-1/2 items-start gap-3 rounded-2xl border p-4 shadow-soft ${type==='success'?'bg-mint border-green-200 text-green-900':type==='info'?'bg-blue-50 border-blue-200 text-blue-900':'bg-red-50 border-red-200 text-red-900'}`}><div className="flex-1 text-sm font-semibold">{message}</div><button onClick={onClose} className="rounded-full p-1 hover:bg-black/5" aria-label="Close"><X size={18}/></button></div>
}

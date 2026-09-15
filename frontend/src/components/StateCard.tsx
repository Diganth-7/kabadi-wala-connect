import { AlertCircle, CheckCircle2, Inbox, LoaderCircle } from 'lucide-react'
export function StateCard({state,message,onRetry}:{state:'loading'|'success'|'error'|'empty';message:string;onRetry?:()=>void}){
 const icon = state==='loading'?<LoaderCircle className="animate-spin"/>:state==='success'?<CheckCircle2/>:state==='error'?<AlertCircle/>:<Inbox/>
 return <div className="card flex min-h-40 flex-col items-center justify-center gap-3 p-6 text-center text-gray-600"><div className="text-leaf">{icon}</div><p>{message}</p>{state==='error'&&onRetry&&<button className="secondary" onClick={onRetry}>Try again</button>}</div>
}

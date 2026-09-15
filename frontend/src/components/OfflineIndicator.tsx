import { Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
export function OfflineIndicator(){
  const {online,syncing}=useApp()
  if (online && !syncing) return <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs font-semibold shadow-soft border border-black/5"><Wifi size={15} className="text-leaf"/> Online</div>
  return <div className={`fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold shadow-soft ${syncing?'bg-amber-50 text-amber-800':'bg-red-50 text-red-700'}`}>{syncing?<RefreshCw size={15} className="animate-spin"/>:<WifiOff size={15}/>} {syncing?'Back online — syncing...':'⚠️ You are offline.'}</div>
}

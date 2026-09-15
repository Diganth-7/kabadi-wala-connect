import type React from 'react'
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { Condition, DemoState, Language, User, UserRole } from '../types'
import { authService } from '../services'
import { readStorage, writeStorage } from '../utils/storage'

interface AppContextValue {
  user: User | null; role: UserRole; language: Language; online: boolean; syncing: boolean
  demo: DemoState; setLanguage: (language:Language)=>void; login:(phone:string,otp:string)=>Promise<void>; logout:()=>void
  setRole:(role:UserRole)=>void; updateDemo:(patch:Partial<DemoState>)=>void; setDraft:(patch:Partial<DemoState['draft']>)=>void
}
const Ctx = createContext<AppContextValue | null>(null)

export function AppProvider({children}:{children:React.ReactNode}) {
  const [user,setUser] = useState<User|null>(() => readStorage<User|null>('kbc_user', null))
  const [language,setLanguageState] = useState<Language>(() => readStorage<Language>('kbc_language','en'))
  const [online,setOnline] = useState(navigator.onLine)
  const [syncing,setSyncing] = useState(false)
  const [demo,setDemo] = useState<DemoState>(() => readStorage<DemoState>('kbc_demo',{draft:{}}))

  useEffect(() => {
    const on = () => { setOnline(true); setSyncing(true); window.setTimeout(()=>setSyncing(false),1400) }
    const off = () => setOnline(false)
    window.addEventListener('online',on); window.addEventListener('offline',off)
    return () => { window.removeEventListener('online',on); window.removeEventListener('offline',off) }
  },[])
  useEffect(()=>writeStorage('kbc_demo',demo),[demo])
  const login = async (identifier:string,otp:string) => { const u = await authService.verifyOtp(identifier,otp); setUser(u); writeStorage('kbc_user',u) }
  const logout = () => { authService.logout(); setUser(null); localStorage.removeItem('kbc_user') }
  const setLanguage = (v:Language) => { setLanguageState(v); writeStorage('kbc_language',v) }
  const updateDemo = (patch:Partial<DemoState>) => setDemo(d=>({...d,...patch}))
  const setDraft = (patch:Partial<DemoState['draft']>) => setDemo(d=>({...d,draft:{...d.draft,...patch}}))
  const role = user?.role ?? 'COLLECTOR'
  const value = useMemo(()=>({user,role,language,online,syncing,demo,setLanguage,login,logout,setRole:(r:UserRole)=>setUser(u=>u?{...u,role:r}:{...(readStorage<User|null>('kbc_user',null) || ({} as User)),role:r}),updateDemo,setDraft}),[user,role,language,online,syncing,demo])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
export function useApp(){ const v=useContext(Ctx); if(!v) throw new Error('useApp must be used inside AppProvider'); return v }

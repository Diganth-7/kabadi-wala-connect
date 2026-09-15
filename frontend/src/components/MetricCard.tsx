import type React from 'react'
export function MetricCard({label,value,icon}:{label:string;value:string;icon:React.ReactNode}){return <div className="card p-4"><div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-mint text-leaf">{icon}</div><div className="text-2xl font-black">{value}</div><div className="mt-1 text-sm text-gray-500">{label}</div></div>}

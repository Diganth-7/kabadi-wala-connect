import type React from 'react'
export function AuthLayout({children}:{children:React.ReactNode}){ return <div className="min-h-screen bg-gradient-to-br from-mint via-cream to-white"><div className="mx-auto flex min-h-screen max-w-md items-center px-5 py-8">{children}</div></div> }

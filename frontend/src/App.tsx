import type React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Splash from './pages/Splash'
import Language from './pages/Language'
import Login from './pages/Login'
import CollectorHome from './pages/collector/CollectorHome'
import { PhotoUpload,MaterialSelection,Weight,Condition,LotReview } from './pages/collector/AddScrap'
import LotCreated from './pages/collector/LotCreated'
import Prices from './pages/collector/Prices'
import Recyclers from './pages/collector/Recyclers'
import { PickupRequest,PickupTracking } from './pages/collector/Pickup'
import Handover from './pages/collector/Handover'
import Payment from './pages/collector/Payment'
import Lots,{LotDetails} from './pages/collector/Lots'
import Earnings from './pages/collector/Earnings'
import Notifications from './pages/collector/Notifications'
import Safety from './pages/collector/Safety'
import Profile from './pages/collector/Profile'
import RecyclerDashboard from './pages/recycler/RecyclerDashboard'
import RecyclerRequests from './pages/recycler/RecyclerRequests'
import RecyclerPickups from './pages/recycler/RecyclerPickups'
import RecyclerMaterials from './pages/recycler/RecyclerMaterials'
import RecyclerTransactions from './pages/recycler/RecyclerTransactions'
import RecyclerProfile from './pages/recycler/RecyclerProfile'
import AdminDashboard from './pages/admin/AdminDashboard'
import { Collectors,Recyclers as AdminRecyclers,AdminTransactions,AdminAnalytics } from './pages/admin/AdminLists'
import AdminProfile from './pages/admin/AdminProfile'
import { useApp } from './contexts/AppContext'

function Guard({role,children}:{role:'COLLECTOR'|'RECYCLER'|'ADMIN';children:React.ReactNode}){const {user}=useApp();return user?.role===role?<>{children}</>:<Navigate to="/login" replace/>}

export default function App(){
 return <Routes>
  <Route path="/" element={<Navigate to="/splash" replace/>}/><Route path="/splash" element={<Splash/>}/><Route path="/language" element={<Language/>}/><Route path="/login" element={<Login/>}/>
  <Route path="/collector" element={<Guard role="COLLECTOR"><CollectorHome/></Guard>}/>
  <Route path="/collector/add/photo" element={<Guard role="COLLECTOR"><PhotoUpload/></Guard>}/>
  <Route path="/collector/add/material" element={<Guard role="COLLECTOR"><MaterialSelection/></Guard>}/>
  <Route path="/collector/add/weight" element={<Guard role="COLLECTOR"><Weight/></Guard>}/>
  <Route path="/collector/add/condition" element={<Guard role="COLLECTOR"><Condition/></Guard>}/>
  <Route path="/collector/add/review" element={<Guard role="COLLECTOR"><LotReview/></Guard>}/>
  <Route path="/collector/lot-created/:id" element={<Guard role="COLLECTOR"><LotCreated/></Guard>}/>
  <Route path="/collector/prices" element={<Guard role="COLLECTOR"><Prices/></Guard>}/>
  <Route path="/collector/recyclers" element={<Guard role="COLLECTOR"><Recyclers/></Guard>}/>
  <Route path="/collector/pickup/request" element={<Guard role="COLLECTOR"><PickupRequest/></Guard>}/>
  <Route path="/collector/pickup/tracking" element={<Guard role="COLLECTOR"><PickupTracking/></Guard>}/>
  <Route path="/collector/handover" element={<Guard role="COLLECTOR"><Handover/></Guard>}/>
  <Route path="/collector/payment" element={<Guard role="COLLECTOR"><Payment/></Guard>}/>
  <Route path="/collector/lots" element={<Guard role="COLLECTOR"><Lots/></Guard>}/>
  <Route path="/collector/lots/:id" element={<Guard role="COLLECTOR"><LotDetails/></Guard>}/>
  <Route path="/collector/earnings" element={<Guard role="COLLECTOR"><Earnings/></Guard>}/>
  <Route path="/collector/notifications" element={<Guard role="COLLECTOR"><Notifications/></Guard>}/>
  <Route path="/collector/safety" element={<Guard role="COLLECTOR"><Safety/></Guard>}/>
  <Route path="/collector/profile" element={<Guard role="COLLECTOR"><Profile/></Guard>}/>
  <Route path="/recycler" element={<Guard role="RECYCLER"><RecyclerDashboard/></Guard>}/>
  <Route path="/recycler/requests" element={<Guard role="RECYCLER"><RecyclerRequests/></Guard>}/>
  <Route path="/recycler/pickups" element={<Guard role="RECYCLER"><RecyclerPickups/></Guard>}/>
  <Route path="/recycler/materials" element={<Guard role="RECYCLER"><RecyclerMaterials/></Guard>}/>
  <Route path="/recycler/transactions" element={<Guard role="RECYCLER"><RecyclerTransactions/></Guard>}/>
  <Route path="/recycler/profile" element={<Guard role="RECYCLER"><RecyclerProfile/></Guard>}/>
  <Route path="/admin" element={<Guard role="ADMIN"><AdminDashboard/></Guard>}/>
  <Route path="/admin/collectors" element={<Guard role="ADMIN"><Collectors/></Guard>}/>
  <Route path="/admin/recyclers" element={<Guard role="ADMIN"><AdminRecyclers/></Guard>}/>
  <Route path="/admin/transactions" element={<Guard role="ADMIN"><AdminTransactions/></Guard>}/>
  <Route path="/admin/analytics" element={<Guard role="ADMIN"><AdminAnalytics/></Guard>}/>
  <Route path="/admin/profile" element={<Guard role="ADMIN"><AdminProfile/></Guard>}/>
  <Route path="*" element={<Navigate to="/splash" replace/>}/>
 </Routes>
}

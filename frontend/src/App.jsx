import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Portfolio from './pages/Portfolio'
import Backtest from './pages/Backtest'
import Settings from './pages/Settings'
import Navbar from './components/Navbar'
import { auth } from './api'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      auth.me().then(u => { setUser(u); setLoading(false) }).catch(() => { localStorage.removeItem('token'); setLoading(false) })
    } else {
      setLoading(false)
    }
  }, [])

  if (loading) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4">📈</div>
        <div className="text-slate-400">載入中...</div>
      </div>
    </div>
  )

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 pb-20">
        {user && <Navbar />}
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <Login setUser={setUser} />} />
          <Route path="/" element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} />
          <Route path="/stock/:symbol" element={user ? <StockDetail user={user} /> : <Navigate to="/login" />} />
          <Route path="/portfolio" element={user ? <Portfolio user={user} /> : <Navigate to="/login" />} />
          <Route path="/backtest" element={user ? <Backtest /> : <Navigate to="/login" />} />
          <Route path="/settings" element={user ? <Settings user={user} setUser={setUser} /> : <Navigate to="/login" />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

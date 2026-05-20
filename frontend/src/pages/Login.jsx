import { useState } from 'react'
import { auth } from '../api'

export default function Login({ setUser }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      let res
      if (mode === 'login') {
        const form = new URLSearchParams({ username: email, password })
        res = await fetch('/api/auth/login', { method: 'POST', body: form })
        res = await res.json()
        if (!res.access_token) throw new Error(res.detail || '登入失敗')
      } else {
        res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, display_name: name }),
        })
        res = await res.json()
        if (!res.access_token) throw new Error(res.detail || '註冊失敗')
      }
      localStorage.setItem('token', res.access_token)
      setUser(res.user)
    } catch (err) {
      setError(err.message || '發生錯誤，請重試')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-6xl mb-3">📈</div>
          <h1 className="text-2xl font-bold text-white">台股交易小幫手</h1>
          <p className="text-slate-400 text-sm mt-1">智能分析・精準交易</p>
        </div>

        <div className="card">
          <div className="flex mb-6 bg-slate-700 rounded-lg p-1">
            {['login', 'register'].map(m => (
              <button key={m} onClick={() => setMode(m)}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${mode === m ? 'bg-brand-500 text-white' : 'text-slate-400'}`}>
                {m === 'login' ? '登入' : '註冊'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === 'register' && (
              <input type="text" placeholder="暱稱（選填）" value={name} onChange={e => setName(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-brand-500" />
            )}
            <input type="email" placeholder="Email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-brand-500" />
            <input type="password" placeholder="密碼" required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-brand-500" />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary w-full py-3 disabled:opacity-50">
              {loading ? '處理中...' : (mode === 'login' ? '登入' : '建立帳號')}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          本工具僅供資料分析參考，不構成投資建議。<br />投資有風險，操作請謹慎。
        </p>
      </div>
    </div>
  )
}

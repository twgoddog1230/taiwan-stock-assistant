import { useState } from 'react'
import { auth, push } from '../api'

export default function Settings({ user, setUser }) {
  const [capital, setCapital] = useState(user.total_capital || 100000)
  const [risk, setRisk] = useState(user.risk_level || 'moderate')
  const [name, setName] = useState(user.display_name || '')
  const [saved, setSaved] = useState(false)
  const [notifyStatus, setNotifyStatus] = useState('')

  const save = async () => {
    const updated = await auth.updateSettings({ total_capital: capital, risk_level: risk, display_name: name })
    setUser(u => ({ ...u, total_capital: capital, risk_level: risk, display_name: name }))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const enableNotifications = async () => {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      setNotifyStatus('此裝置不支援推播通知')
      return
    }
    try {
      const permission = await Notification.requestPermission()
      if (permission !== 'granted') { setNotifyStatus('請允許通知權限'); return }

      const reg = await navigator.serviceWorker.ready
      const keyRes = await push.getPublicKey()
      const vapidKey = keyRes.public_key

      if (!vapidKey) { setNotifyStatus('推播服務尚未設定，請聯絡管理員'); return }

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      })

      const subJson = sub.toJSON()
      await push.subscribe({ endpoint: subJson.endpoint, keys: subJson.keys })
      setNotifyStatus('✅ 推播通知已開啟！')
    } catch (e) {
      setNotifyStatus(`設定失敗：${e.message}`)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  return (
    <div className="max-w-lg mx-auto px-4 pt-6">
      <h1 className="text-xl font-bold mb-4">⚙️ 設定</h1>

      <div className="card mb-4">
        <div className="text-sm font-semibold text-slate-300 mb-4">個人設定</div>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">暱稱</label>
            <input value={name} onChange={e => setName(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-500" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">可用資金（元）</label>
            <input type="number" value={capital} onChange={e => setCapital(+e.target.value)} step="10000"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-500" />
            <div className="text-xs text-slate-500 mt-1">約 {(capital / 10000).toFixed(1)} 萬元，影響每筆建議倉位大小</div>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">風險偏好</label>
            <div className="grid grid-cols-3 gap-2">
              {[['conservative', '保守'], ['moderate', '穩健'], ['aggressive', '積極']].map(([val, label]) => (
                <button key={val} onClick={() => setRisk(val)}
                  className={`py-2 text-sm rounded-lg transition-colors ${risk === val ? 'bg-brand-500 text-white' : 'bg-slate-700 text-slate-300'}`}>
                  {label}
                </button>
              ))}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {risk === 'conservative' ? '每筆最多投入 15%' : risk === 'moderate' ? '每筆最多投入 20%' : '每筆最多投入 25%'}
            </div>
          </div>
          <button onClick={save} className="btn-primary w-full py-3">
            {saved ? '✅ 已儲存' : '儲存設定'}
          </button>
        </div>
      </div>

      <div className="card mb-4">
        <div className="text-sm font-semibold text-slate-300 mb-3">推播通知</div>
        <p className="text-xs text-slate-400 mb-3">開啟後，每日盤前（08:00）和盤後（15:30）自動推播分析結果</p>
        <button onClick={enableNotifications} className="btn-outline w-full py-2.5 text-sm">
          🔔 開啟推播通知
        </button>
        {notifyStatus && <p className="text-xs mt-2 text-center text-slate-300">{notifyStatus}</p>}
      </div>

      <div className="card mb-4 bg-slate-800/50">
        <div className="text-sm font-semibold text-slate-300 mb-2">帳號資訊</div>
        <div className="text-xs text-slate-400 mb-4">{user.email}</div>
        <button onClick={logout} className="w-full py-2.5 text-sm text-red-400 border border-red-800/50 rounded-lg hover:bg-red-900/20 transition-colors">
          登出
        </button>
      </div>

      <div className="text-center text-xs text-slate-500 mt-4 pb-4">
        台股交易小幫手 v1.0<br />
        本工具僅供資料分析參考，不構成投資建議<br />
        投資有風險，操作請謹慎自行判斷
      </div>
    </div>
  )
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)))
}

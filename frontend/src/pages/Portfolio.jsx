import { useState, useEffect } from 'react'
import { trades, watchlist } from '../api'
import { useNavigate } from 'react-router-dom'

export default function Portfolio({ user }) {
  const nav = useNavigate()
  const [tradeList, setTradeList] = useState([])
  const [watchList, setWatchList] = useState([])
  const [stats, setStats] = useState(null)
  const [tab, setTab] = useState('watchlist')

  useEffect(() => {
    trades.get().then(setTradeList)
    trades.stats().then(setStats)
    watchlist.get().then(setWatchList)
  }, [])

  const removeWatch = (sym) => {
    watchlist.remove(sym).then(() => setWatchList(w => w.filter(s => s.symbol !== sym)))
  }

  return (
    <div className="max-w-lg mx-auto px-4 pt-6">
      <h1 className="text-xl font-bold mb-4">持倉管理</h1>

      {/* 資金概覽 */}
      {stats && (
        <div className="card mb-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-xs text-slate-400 mb-1">總資金</div>
              <div className="font-bold text-sm">{(user.total_capital / 10000).toFixed(1)}萬</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 mb-1">已投入</div>
              <div className="font-bold text-sm text-yellow-400">{(stats.total_invested / 10000).toFixed(1)}萬</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 mb-1">可用資金</div>
              <div className="font-bold text-sm text-green-400">{(stats.cash_available / 10000).toFixed(1)}萬</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab切換 */}
      <div className="flex gap-2 mb-4">
        {[['watchlist', '自選股'], ['trades', '交易紀錄']].map(([val, label]) => (
          <button key={val} onClick={() => setTab(val)}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${tab === val ? 'bg-brand-500 text-white' : 'bg-slate-700 text-slate-300'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* 自選股 */}
      {tab === 'watchlist' && (
        <div className="space-y-2">
          {watchList.length === 0 ? (
            <div className="card text-center py-10 text-slate-400">
              <div className="text-3xl mb-2">☆</div>
              尚無自選股，在個股頁面點星號加入
            </div>
          ) : watchList.map(s => (
            <div key={s.symbol} className="card flex items-center justify-between cursor-pointer" onClick={() => nav(`/stock/${s.symbol}`)}>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{s.name}</span>
                  <span className="text-slate-400 text-sm">{s.symbol}</span>
                </div>
                {s.score != null && (
                  <div className="text-xs text-slate-400 mt-0.5">評分：{s.score?.toFixed(0)} 分・{s.signal}</div>
                )}
              </div>
              <button onClick={e => { e.stopPropagation(); removeWatch(s.symbol) }} className="text-slate-500 hover:text-red-400 px-2 py-1">✕</button>
            </div>
          ))}
        </div>
      )}

      {/* 交易紀錄 */}
      {tab === 'trades' && (
        <div className="space-y-2">
          {tradeList.length === 0 ? (
            <div className="card text-center py-10 text-slate-400">
              <div className="text-3xl mb-2">📝</div>
              尚無交易紀錄
            </div>
          ) : tradeList.map(t => (
            <div key={t.id} className="card">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${t.action === 'buy' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                      {t.action === 'buy' ? '買進' : '賣出'}
                    </span>
                    <span className="font-semibold">{t.name}</span>
                    <span className="text-slate-400 text-sm">{t.symbol}</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">{t.trade_date}・{t.shares.toLocaleString()} 股・@ {t.price} 元</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-sm">{(t.total_amount / 10000).toFixed(2)} 萬</div>
                  {t.strategy && <div className="text-xs text-slate-400">{t.strategy}</div>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

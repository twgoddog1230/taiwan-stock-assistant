import { useState, useEffect } from 'react'
import { market, admin } from '../api'
import StockCard from '../components/StockCard'
import dayjs from 'dayjs'

function MarketBadge({ label, value, suffix = '%' }) {
  const isPos = value > 0
  const isNeg = value < 0
  return (
    <div className="bg-slate-700/50 rounded-lg p-3 text-center">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className={`text-sm font-bold ${isPos ? 'text-red-400' : isNeg ? 'text-green-400' : 'text-slate-300'}`}>
        {value != null ? `${isPos ? '+' : ''}${typeof value === 'number' ? value.toFixed(2) : value}${suffix}` : '-'}
      </div>
    </div>
  )
}

export default function Dashboard({ user }) {
  const [summary, setSummary] = useState(null)
  const [picks, setPicks] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState('all')

  useEffect(() => {
    Promise.all([market.today(), market.picks()])
      .then(([s, p]) => { setSummary(s); setPicks(p) })
      .finally(() => setLoading(false))
  }, [])

  const triggerAnalysis = async () => {
    setRunning(true)
    await admin.runAnalysis()
    setTimeout(() => { window.location.reload() }, 2000)
  }

  const filtered = picks.filter(p => {
    if (tab === 'all') return true
    return p.strategy?.includes(tab)
  })

  if (loading) return <div className="p-6 text-slate-400 text-center mt-20">載入中...</div>

  return (
    <div className="max-w-lg mx-auto px-4 pt-6">
      {/* 標題 */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-xl font-bold">早安，{user.display_name || '投資者'} 👋</h1>
          <p className="text-slate-400 text-sm">{dayjs().format('YYYY年M月D日')}</p>
        </div>
        <button onClick={triggerAnalysis} disabled={running}
          className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50">
          {running ? '分析中...' : '🔄 立即分析'}
        </button>
      </div>

      {/* 美股指數 */}
      {summary && (
        <div className="card mb-4">
          <div className="text-sm font-semibold text-slate-300 mb-3">昨日美股</div>
          <div className="grid grid-cols-4 gap-2">
            <MarketBadge label="S&P500" value={summary.sp500_change_pct} />
            <MarketBadge label="NASDAQ" value={summary.nasdaq_change_pct} />
            <MarketBadge label="費半SOX" value={summary.sox_change_pct} />
            <MarketBadge label="VIX" value={summary.vix} suffix="" />
          </div>
          {summary.usd_twd && (
            <div className="text-xs text-slate-400 mt-2 text-right">美元/台幣：{summary.usd_twd?.toFixed(2)}</div>
          )}
        </div>
      )}

      {/* 盤前報告 */}
      {summary?.pre_market_report && (
        <div className="card mb-4 bg-blue-900/20 border-blue-800/50">
          <div className="text-sm font-semibold text-blue-300 mb-2">📊 盤前分析</div>
          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">{summary.pre_market_report}</pre>
        </div>
      )}

      {/* 策略篩選 */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {[['all', '全部'], ['day_trade', '當沖'], ['short_term', '短線'], ['swing', '波段']].map(([val, label]) => (
          <button key={val} onClick={() => setTab(val)}
            className={`whitespace-nowrap text-sm px-3 py-1.5 rounded-lg transition-colors ${tab === val ? 'bg-brand-500 text-white' : 'bg-slate-700 text-slate-300'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* 推薦股票列表 */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="card text-center py-10">
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-slate-400">今日尚無推薦，請點「立即分析」</p>
          </div>
        ) : (
          filtered.map(s => <StockCard key={s.symbol} stock={s} />)
        )}
      </div>

      <div className="mt-6 mb-4 text-center text-xs text-slate-500">
        本工具僅供資料分析參考，不構成投資建議，投資須自負盈虧
      </div>
    </div>
  )
}

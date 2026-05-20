import { useState } from 'react'
import { stocks } from '../api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const MONTH_NAMES = { 1:'1月',2:'2月',3:'3月',4:'4月',5:'5月',6:'6月',7:'7月',8:'8月',9:'9月',10:'10月',11:'11月',12:'12月' }

export default function Backtest() {
  const [symbol, setSymbol] = useState('')
  const [years, setYears] = useState(5)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    if (!symbol) return
    setLoading(true)
    setError('')
    try {
      const r = await stocks.backtest(symbol.toUpperCase(), years)
      if (r.error) { setError(r.error); setResult(null) }
      else setResult(r)
    } catch {
      setError('回測失敗，請確認股票代號')
    } finally {
      setLoading(false)
    }
  }

  const monthData = result?.monthly_stats
    ? Object.entries(result.monthly_stats).map(([m, v]) => ({ month: MONTH_NAMES[+m], win_rate: v.win_rate, trades: v.trades }))
    : []

  return (
    <div className="max-w-lg mx-auto px-4 pt-6">
      <h1 className="text-xl font-bold mb-4">📊 歷史回測</h1>

      <div className="card mb-4">
        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">股票代號</label>
            <input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="例：2330" onKeyDown={e => e.key === 'Enter' && run()}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">回測年限：{years} 年</label>
            <input type="range" min="1" max="25" value={years} onChange={e => setYears(+e.target.value)}
              className="w-full accent-brand-500" />
            <div className="flex justify-between text-xs text-slate-500 mt-1"><span>1年</span><span>25年</span></div>
          </div>
          <button onClick={run} disabled={loading || !symbol} className="btn-primary w-full py-3 disabled:opacity-50">
            {loading ? '計算中...' : '開始回測'}
          </button>
        </div>
      </div>

      {error && <div className="card border-red-500/50 text-red-400 text-sm mb-4">{error}</div>}

      {result && (
        <>
          {/* 統計摘要 */}
          <div className="card mb-4">
            <div className="text-sm font-semibold mb-3">回測結果（{result.years} 年）</div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: '總交易次數', value: `${result.total_trades} 次` },
                { label: '歷史勝率', value: `${result.win_rate}%`, color: result.win_rate >= 50 ? 'text-red-400' : 'text-green-400' },
                { label: '平均報酬率', value: `${result.avg_return > 0 ? '+' : ''}${result.avg_return}%`, color: result.avg_return > 0 ? 'text-red-400' : 'text-green-400' },
                { label: '獲利因子', value: result.profit_factor.toFixed(2) },
                { label: '最大單筆虧損', value: `${result.max_loss}%`, color: 'text-green-400' },
                { label: '最大單筆獲利', value: `+${result.max_gain}%`, color: 'text-red-400' },
                { label: '平均持有天數', value: `${result.avg_hold_days} 天` },
              ].map(item => (
                <div key={item.label} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-1">{item.label}</div>
                  <div className={`font-bold ${item.color || 'text-white'}`}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* 月份勝率 */}
          {monthData.length > 0 && (
            <div className="card mb-4">
              <div className="text-sm font-semibold mb-3">月份勝率分布</div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={monthData} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
                  <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }}
                    formatter={v => [`${v}%`, '勝率']} />
                  <Bar dataKey="win_rate" radius={[3, 3, 0, 0]}>
                    {monthData.map((entry, i) => (
                      <Cell key={i} fill={entry.win_rate >= 55 ? '#ef4444' : entry.win_rate >= 45 ? '#f59e0b' : '#22c55e'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex gap-3 text-xs text-slate-400 mt-2 justify-center">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block"></span>勝率≥55%</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400 inline-block"></span>45-55%</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-400 inline-block"></span>低於45%</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

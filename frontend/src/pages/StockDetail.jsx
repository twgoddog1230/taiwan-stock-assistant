import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { stocks, watchlist, trades } from '../api'
import ScoreBar from '../components/ScoreBar'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function StockDetail({ user }) {
  const { symbol } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [prices, setPrices] = useState([])
  const [loading, setLoading] = useState(true)
  const [addingTrade, setAddingTrade] = useState(false)
  const [tradeForm, setTradeForm] = useState({ action: 'buy', shares: 1000, price: 0, strategy: '' })

  useEffect(() => {
    Promise.all([stocks.analysis(symbol), stocks.prices(symbol, 90)])
      .then(([a, p]) => { setData(a); setPrices(p); setTradeForm(f => ({ ...f, price: a.entry_price || 0 })) })
      .finally(() => setLoading(false))
  }, [symbol])

  const addWatch = () => watchlist.add(symbol).then(() => alert('已加入自選股'))
  const submitTrade = async () => {
    await trades.add({ symbol, ...tradeForm, trade_date: new Date().toISOString().split('T')[0] })
    setAddingTrade(false)
    alert('交易紀錄已儲存')
  }

  if (loading) return <div className="p-6 text-slate-400 text-center mt-20">載入中...</div>
  if (!data) return <div className="p-6 text-red-400 text-center">找不到股票資料</div>

  const scoreItems = [
    { label: '技術面', score: data.technical?.score || 0, color: 'blue' },
    { label: '籌碼面', score: data.chip?.score || 0, color: 'purple' },
    { label: '季節效應', score: data.seasonal?.score || 0, color: 'yellow' },
    { label: '基本面', score: data.fundamental?.score || 0, color: 'green' },
    { label: '資金動能', score: data.momentum?.score || 0, color: 'orange' },
  ]

  const pos = data.position

  return (
    <div className="max-w-lg mx-auto px-4 pt-6 pb-8">
      {/* 標題列 */}
      <div className="flex items-center gap-3 mb-5">
        <button onClick={() => nav(-1)} className="text-slate-400 text-xl">←</button>
        <div className="flex-1">
          <div className="flex items-baseline gap-2">
            <h1 className="text-xl font-bold">{data.name}</h1>
            <span className="text-slate-400">{symbol}</span>
          </div>
        </div>
        <button onClick={addWatch} className="text-yellow-400 text-xl">☆</button>
      </div>

      {/* 總評分 */}
      <div className="card mb-4 text-center">
        <div className="text-5xl font-bold text-brand-500 mb-1">{data.score?.toFixed(0)}</div>
        <div className="text-slate-400 text-sm">綜合評分 / 100</div>
      </div>

      {/* 五大面向分數 */}
      <div className="card mb-4">
        <div className="text-sm font-semibold text-slate-300 mb-3">評分明細</div>
        {scoreItems.map(item => <ScoreBar key={item.label} {...item} />)}
      </div>

      {/* K線圖 */}
      {prices.length > 0 && (
        <div className="card mb-4">
          <div className="text-sm font-semibold text-slate-300 mb-3">近90日走勢</div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={prices}>
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', color: '#f1f5f9' }}
                formatter={(v, n) => [v?.toFixed(2), n === 'close' ? '收盤價' : n]} />
              <Line type="monotone" dataKey="close" stroke="#1a56db" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="ma20" stroke="#f59e0b" dot={false} strokeWidth={1} strokeDasharray="3 3" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 交易計畫 */}
      {pos && (
        <div className="card mb-4">
          <div className="text-sm font-semibold text-slate-300 mb-3">建議交易計畫</div>
          <div className="grid grid-cols-2 gap-3 text-sm mb-3">
            <div className="bg-slate-700/50 rounded-lg p-3">
              <div className="text-slate-400 text-xs mb-1">第一批進場</div>
              <div className="font-bold">{pos.first_batch.entry_price} 元</div>
              <div className="text-slate-400 text-xs">
                {pos.first_batch.lots > 0 ? `${pos.first_batch.lots} 張` : `${pos.first_batch.shares} 股（零股）`}
                ・約 {(pos.first_batch.amount / 10000).toFixed(1)} 萬
              </div>
            </div>
            <div className="bg-red-900/30 rounded-lg p-3">
              <div className="text-red-400 text-xs mb-1">⚠️ 停損點</div>
              <div className="font-bold text-red-300">{pos.stop_loss.price} 元</div>
              <div className="text-red-400 text-xs">最大虧損 {pos.stop_loss.max_loss?.toLocaleString()} 元</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm mb-3">
            <div className="bg-green-900/30 rounded-lg p-3">
              <div className="text-green-400 text-xs mb-1">🎯 目標①</div>
              <div className="font-bold text-green-300">{pos.targets.target1.price} 元</div>
              <div className="text-xs text-green-400">+6.5%，出50%</div>
            </div>
            <div className="bg-green-900/20 rounded-lg p-3">
              <div className="text-green-400 text-xs mb-1">🎯 目標②</div>
              <div className="font-bold text-green-200">{pos.targets.target2.price} 元</div>
              <div className="text-xs text-green-400">+12%，全出</div>
            </div>
          </div>
          <div className="bg-blue-900/20 rounded-lg p-3 text-xs text-blue-300">
            <div className="font-semibold mb-1">📈 加碼時機</div>
            <div>突破 {pos.second_batch_add.trigger_price} 元 → 加碼 {(pos.second_batch_add.amount / 10000).toFixed(1)} 萬</div>
            <div className="mt-1">回測 {pos.second_batch_dip.trigger_price} 元止穩 → 補買 {(pos.second_batch_dip.amount / 10000).toFixed(1)} 萬</div>
          </div>
        </div>
      )}

      {/* 評分理由 */}
      {data.reasoning?.length > 0 && (
        <div className="card mb-4">
          <div className="text-sm font-semibold text-slate-300 mb-2">分析理由</div>
          <ul className="space-y-1">
            {data.reasoning.map((r, i) => <li key={i} className="text-xs text-slate-400 flex items-start gap-2"><span>•</span><span>{r}</span></li>)}
          </ul>
        </div>
      )}

      {/* 記錄交易按鈕 */}
      <button onClick={() => setAddingTrade(true)} className="btn-primary w-full py-3 mb-3">
        📝 記錄這筆交易
      </button>

      {/* 交易記錄表單 */}
      {addingTrade && (
        <div className="card mb-4 border-brand-500/50">
          <div className="text-sm font-semibold mb-3">記錄交易</div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">買/賣</label>
              <select value={tradeForm.action} onChange={e => setTradeForm(f => ({ ...f, action: e.target.value }))}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white">
                <option value="buy">買進</option>
                <option value="sell">賣出</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">股數</label>
              <input type="number" value={tradeForm.shares} onChange={e => setTradeForm(f => ({ ...f, shares: +e.target.value }))}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
          </div>
          <div className="mb-3">
            <label className="text-xs text-slate-400 block mb-1">成交價格</label>
            <input type="number" step="0.1" value={tradeForm.price} onChange={e => setTradeForm(f => ({ ...f, price: +e.target.value }))}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white" />
          </div>
          <div className="flex gap-2">
            <button onClick={submitTrade} className="btn-primary flex-1">確認儲存</button>
            <button onClick={() => setAddingTrade(false)} className="btn-outline flex-1">取消</button>
          </div>
        </div>
      )}
    </div>
  )
}

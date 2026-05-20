import { useNavigate } from 'react-router-dom'

const signalMap = {
  strong_buy: { label: '強力買進', cls: 'tag-buy' },
  buy: { label: '買進', cls: 'tag-buy' },
  watch: { label: '觀察', cls: 'tag-watch' },
  hold: { label: '持有', cls: 'tag-hold' },
  sell: { label: '賣出', cls: 'tag-sell' },
}

const strategyMap = {
  day_trade: '當沖',
  short_term: '短線',
  swing: '波段',
  observe: '觀察',
}

export default function StockCard({ stock }) {
  const nav = useNavigate()
  const sig = signalMap[stock.signal] || signalMap.hold
  const strategies = (stock.strategy || []).map(s => strategyMap[s] || s).join('・')

  return (
    <div className="card cursor-pointer active:opacity-80 transition-opacity" onClick={() => nav(`/stock/${stock.symbol}`)}>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg">{stock.name}</span>
            <span className="text-slate-400 text-sm">{stock.symbol}</span>
          </div>
          <div className="flex gap-1.5 mt-1 flex-wrap">
            <span className={sig.cls}>{sig.label}</span>
            {strategies && <span className="tag-watch">{strategies}</span>}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-brand-500">{stock.score?.toFixed(0)}</div>
          <div className="text-xs text-slate-400">/ 100分</div>
        </div>
      </div>

      {stock.entry_price && (
        <div className="grid grid-cols-3 gap-2 text-center text-xs mt-2">
          <div className="bg-slate-700/50 rounded-lg p-2">
            <div className="text-slate-400">進場</div>
            <div className="font-semibold text-slate-200">{stock.entry_price}</div>
          </div>
          <div className="bg-red-900/30 rounded-lg p-2">
            <div className="text-red-400">停損</div>
            <div className="font-semibold text-red-300">{stock.stop_loss}</div>
          </div>
          <div className="bg-green-900/30 rounded-lg p-2">
            <div className="text-green-400">目標①</div>
            <div className="font-semibold text-green-300">{stock.target1}</div>
          </div>
        </div>
      )}

      {stock.reasoning && stock.reasoning.length > 0 && (
        <div className="mt-3 text-xs text-slate-400 border-t border-slate-700 pt-2">
          {stock.reasoning.slice(0, 2).join('・')}
        </div>
      )}
    </div>
  )
}

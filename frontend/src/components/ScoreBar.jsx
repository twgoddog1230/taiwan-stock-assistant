export default function ScoreBar({ label, score, max = 20, color = 'blue' }) {
  const pct = Math.min(100, (score / max) * 100)
  const colors = {
    blue: 'bg-blue-500', green: 'bg-green-500', yellow: 'bg-yellow-500',
    purple: 'bg-purple-500', orange: 'bg-orange-500',
  }
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{label}</span>
        <span className="font-semibold text-slate-200">{score.toFixed(1)} / {max}</span>
      </div>
      <div className="score-bar">
        <div className={`h-full ${colors[color] || colors.blue} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

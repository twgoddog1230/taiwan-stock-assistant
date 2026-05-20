import { NavLink } from 'react-router-dom'

const tabs = [
  { to: '/', icon: '🏠', label: '首頁' },
  { to: '/portfolio', icon: '💼', label: '持倉' },
  { to: '/backtest', icon: '📊', label: '回測' },
  { to: '/settings', icon: '⚙️', label: '設定' },
]

export default function Navbar() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-slate-800/95 backdrop-blur border-t border-slate-700 z-50">
      <div className="flex justify-around items-center h-16 max-w-lg mx-auto px-4">
        {tabs.map(t => (
          <NavLink key={t.to} to={t.to} end={t.to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 py-1 px-3 rounded-lg transition-colors ${isActive ? 'text-brand-500' : 'text-slate-400 hover:text-slate-200'}`
            }>
            <span className="text-xl">{t.icon}</span>
            <span className="text-xs font-medium">{t.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

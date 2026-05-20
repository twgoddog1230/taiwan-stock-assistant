import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 30000 })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const auth = {
  login: (email, password) => api.post('/auth/login', null, { params: {}, data: new URLSearchParams({ username: email, password }), headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }),
  register: (email, password, display_name) => api.post('/auth/register', { email, password, display_name }),
  me: () => api.get('/auth/me'),
  updateSettings: (data) => api.put('/auth/settings', data),
}

export const market = {
  today: () => api.get('/market/today'),
  picks: (date) => api.get('/market/picks', { params: date ? { trade_date: date } : {} }),
}

export const stocks = {
  search: (q) => api.get('/stocks/search', { params: { q } }),
  analysis: (symbol) => api.get(`/stock/${symbol}/analysis`),
  prices: (symbol, days = 180) => api.get(`/stock/${symbol}/prices`, { params: { days } }),
  backtest: (symbol, years = 5) => api.get(`/stock/${symbol}/backtest`, { params: { years } }),
}

export const watchlist = {
  get: () => api.get('/watchlist'),
  add: (symbol, note = '') => api.post('/watchlist', { symbol, note }),
  remove: (symbol) => api.delete(`/watchlist/${symbol}`),
}

export const trades = {
  get: () => api.get('/trades'),
  add: (data) => api.post('/trades', data),
  stats: () => api.get('/trades/stats'),
}

export const push = {
  getPublicKey: () => api.get('/push/vapid-public-key'),
  subscribe: (sub) => api.post('/push/subscribe', { endpoint: sub.endpoint, p256dh: sub.keys?.p256dh || sub.getKey?.('p256dh'), auth: sub.keys?.auth || sub.getKey?.('auth') }),
}

export const admin = {
  runAnalysis: () => api.post('/admin/run-analysis'),
  runPreMarket: () => api.post('/admin/run-pre-market'),
}

export default api

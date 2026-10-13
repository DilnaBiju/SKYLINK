const BASE = import.meta.env.VITE_API_URL || ''
const TOKEN_KEY = 'skylink_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

function message(data, status) {
  if (data && typeof data.detail === 'string') return data.detail
  if (data && Array.isArray(data.detail) && data.detail.length) {
    const d = data.detail[0]
    const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : ''
    return `${String(field).replace(/_/g, ' ')}: ${String(d.msg).replace(/^Value error, /, '')}`
  }
  return status ? `Something went wrong (${status}). Please try again.` : 'Cannot reach the SkyLink server. Is the backend running?'
}

async function request(path, { method = 'GET', body, params, raw } = {}) {
  const url = new URL(BASE + path, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && v !== '' && url.searchParams.set(k, v))
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  const t = tokenStore.get()
  if (t) headers.Authorization = `Bearer ${t}`
  let res
  try {
    res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(message(null, 0), 0)
  }
  if (raw && res.ok) return res
  if (res.status === 204) return null
  let data = null
  try { data = await res.json() } catch { /* empty */ }
  if (!res.ok) {
    if (res.status === 401 && t) window.dispatchEvent(new Event('skylink:unauthorized'))
    throw new ApiError(message(data, res.status), res.status)
  }
  return data
}

export class ApiError extends Error {
  constructor(msg, status) { super(msg); this.status = status }
}

export const api = {
  register: (b) => request('/api/auth/register', { method: 'POST', body: b }),
  login: (b) => request('/api/auth/login', { method: 'POST', body: b }),
  forgot: (b) => request('/api/auth/forgot', { method: 'POST', body: b }),
  reset: (b) => request('/api/auth/reset', { method: 'POST', body: b }),
  me: () => request('/api/me'),
  updateMe: (b) => request('/api/me', { method: 'PUT', body: b }),
  changePassword: (b) => request('/api/me/password', { method: 'POST', body: b }),

  airports: () => request('/api/airports'),
  search: (params) => request('/api/flights/search', { params }),
  popular: () => request('/api/flights/popular'),
  flight: (id) => request(`/api/flights/${id}`),
  seats: (id) => request(`/api/flights/${id}/seats`),
  fareHistory: (id) => request(`/api/flights/${id}/fare-history`),

  validatePromo: (b) => request('/api/promos/validate', { method: 'POST', body: b }),
  createBooking: (b) => request('/api/bookings', { method: 'POST', body: b }),
  bookings: () => request('/api/bookings'),
  booking: (pnr) => request(`/api/bookings/${pnr}`),
  cancelBooking: (pnr) => request(`/api/bookings/${pnr}/cancel`, { method: 'POST' }),
  async downloadTicket(pnr) {
    const res = await request(`/api/bookings/${pnr}/ticket.pdf`, { raw: true })
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `SkyLink-${pnr}.pdf`
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 2000)
  },

  banks: () => request('/api/payments/banks'),
  startPayment: (b) => request('/api/payments/start', { method: 'POST', body: b }),
  paymentStatus: (id) => request(`/api/payments/${id}`),
  resolvePayment: (id, outcome) => request(`/api/payments/${id}/sandbox-resolve`, { method: 'POST', body: { outcome } }),

  alerts: () => request('/api/alerts'),
  createAlert: (b) => request('/api/alerts', { method: 'POST', body: b }),
  deleteAlert: (id) => request(`/api/alerts/${id}`, { method: 'DELETE' }),
  toggleAlert: (id) => request(`/api/alerts/${id}/toggle`, { method: 'POST' }),
  simulateDrop: (id) => request(`/api/alerts/${id}/simulate-drop`, { method: 'POST' }),
}

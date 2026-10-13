export const inr = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(n) || 0)

export const hm = (iso) => (iso ? iso.slice(11, 16) : '')

export const dur = (min) => `${Math.floor(min / 60)}h ${String(min % 60).padStart(2, '0')}m`

export function longDate(iso) {
  const d = new Date(iso.slice(0, 10) + 'T00:00:00')
  return d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
}

export function shortDate(iso) {
  const d = new Date(iso.slice(0, 10) + 'T00:00:00')
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export const todayISO = () => {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 10)
}

export const addDays = (n) => {
  const d = new Date()
  d.setDate(d.getDate() + n)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 10)
}

export const maskUpi = (u) => (u ? u.replace(/^(.{2}).*(@.*)$/, '$1•••$2') : '')

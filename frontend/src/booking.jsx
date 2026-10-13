// Keeps the seat choice between the Seats -> Passengers pages (survives a refresh).
const KEY = 'skylink_draft'

export const draft = {
  get(flightId) {
    try {
      const d = JSON.parse(sessionStorage.getItem(KEY))
      return d && String(d.flightId) === String(flightId) ? d : null
    } catch { return null }
  },
  set(d) { sessionStorage.setItem(KEY, JSON.stringify(d)) },
  clear() { sessionStorage.removeItem(KEY) },
}

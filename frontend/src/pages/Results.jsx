import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { PlaneTakeoff, SearchX } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { useToast } from '../toast.jsx'
import SearchForm from '../components/SearchForm.jsx'
import FlightCard from '../components/FlightCard.jsx'
import { Empty, ErrorBox } from '../components/ui.jsx'
import { addDays, longDate, todayISO } from '../utils.js'

const SORTS = [['fare', 'Cheapest'], ['duration', 'Fastest'], ['departure', 'Earliest']]

export default function Results() {
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const from = sp.get('from') || 'DEL', to = sp.get('to') || 'BOM'
  const date = sp.get('date') || addDays(14), pax = Number(sp.get('pax')) || 1

  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [sort, setSort] = useState('fare')
  const [nonstop, setNonstop] = useState(false)
  const [tracked, setTracked] = useState(new Set())
  const [going, setGoing] = useState(null)

  useEffect(() => {
    let live = true
    setData(null); setError('')
    api.search({ origin: from, destination: to, date, pax })
      .then((d) => live && setData(d))
      .catch((e) => live && setError(e.message))
    return () => { live = false }
  }, [from, to, date, pax])

  const list = useMemo(() => {
    if (!data) return []
    const l = data.flights.filter((f) => !nonstop || f.stops === 0)
    const key = { fare: (f) => f.fare, duration: (f) => f.duration_min, departure: (f) => f.departure }[sort]
    return [...l].sort((a, b) => (key(a) > key(b) ? 1 : -1))
  }, [data, sort, nonstop])

  const first = data?.flights?.[0]
  const days = [-3, -2, -1, 0, 1, 2, 3].map((n) => {
    const d = new Date(date + 'T00:00:00'); d.setDate(d.getDate() + n)
    const iso = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
    return { iso, label: d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }) }
  }).filter((d) => d.iso >= todayISO())

  function select(f) {
    const target = `/book/${f.id}/seats?pax=${pax}`
    setGoing(f.id)
    if (!user) nav('/login', { state: { from: target, notice: 'Sign in to choose seats and book.' } })
    else nav(target)
  }

  async function track(f) {
    if (!user) return nav('/login', { state: { from: `/flights?${sp}`, notice: 'Sign in to follow this fare.' } })
    try {
      await api.createAlert({ origin: f.origin, destination: f.destination, travel_date: f.departure.slice(0, 10), flight_id: f.id })
      setTracked((s) => new Set(s).add(f.id))
      toast.success(`Following ${f.flight_number}. We will email ${user.email} when the fare drops.`)
    } catch (e) {
      if (e.status === 409) setTracked((s) => new Set(s).add(f.id))
      toast[e.status === 409 ? 'info' : 'error'](e.message)
    }
  }

  return (
    <div className="container">
      <div className="results-search"><SearchForm compact initial={{ from, to, date, pax }} /></div>

      <div className="datestrip" role="tablist" aria-label="Nearby dates">
        {days.map((d) => (
          <button key={d.iso} role="tab" aria-selected={d.iso === date} className={d.iso === date ? 'on' : ''}
            onClick={() => nav(`/flights?${new URLSearchParams({ from, to, date: d.iso, pax })}`)}>{d.label}</button>
        ))}
      </div>

      {error && <ErrorBox>{error}</ErrorBox>}

      {!error && (
        <div className="results-head">
          <div>
            <h1>{first ? `${first.origin_city} to ${first.destination_city}` : `${from} to ${to}`}</h1>
            <p>{longDate(date)} · {pax} traveller{pax > 1 ? 's' : ''}{data ? ` · ${list.length} flight${list.length === 1 ? '' : 's'}` : ''}</p>
          </div>
          <div className="results-tools">
            <div className="seg">{SORTS.map(([k, l]) => <button key={k} className={sort === k ? 'on' : ''} onClick={() => setSort(k)}>{l}</button>)}</div>
            <label className="check"><input type="checkbox" checked={nonstop} onChange={(e) => setNonstop(e.target.checked)} /> Non-stop only</label>
          </div>
        </div>
      )}

      {!data && !error && (
        <div className="flight-skeletons" role="status" aria-label="Searching flights">
          <p className="searching"><PlaneTakeoff size={18} /> Searching airlines for {from} to {to}…</p>
          {[0, 1, 2, 3].map((i) => <div key={i} className="flightcard skeleton" />)}
        </div>
      )}

      {data && list.length === 0 && (
        <Empty icon={<SearchX size={32} />} title="No flights match"
          text={data.flights.length ? 'Turn off the non-stop filter or pick another date.' : 'No flights are left on this day. Try another date.'} />
      )}

      <div className="flight-list">
        <AnimatePresence>
          {list.map((f, i) => (
            <FlightCard key={f.id} f={f} pax={pax} index={i} onSelect={select} onTrack={track}
              tracking={tracked.has(f.id)} busy={going === f.id} />
          ))}
        </AnimatePresence>
      </div>
      {data && <p className="fine">Fares include base fare only; taxes, seat fees and offers are shown at checkout. Schedules and fares are simulated for this project.</p>}
    </div>
  )
}

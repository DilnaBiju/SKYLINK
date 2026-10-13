import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeftRight, CalendarDays, Minus, Plus, Search, Users } from 'lucide-react'
import { api } from '../api.js'
import { addDays, todayISO } from '../utils.js'
import AirportPicker from './AirportPicker.jsx'
import { Button } from './ui.jsx'

let airportCache = null
export function useAirports() {
  const [list, setList] = useState(airportCache || [])
  useEffect(() => {
    if (airportCache) return
    api.airports().then((a) => { airportCache = a; setList(a) }).catch(() => {})
  }, [])
  return list
}

export default function SearchForm({ initial = {}, compact = false }) {
  const nav = useNavigate()
  const airports = useAirports()
  const [from, setFrom] = useState(initial.from || 'DEL')
  const [to, setTo] = useState(initial.to || 'BOM')
  const [date, setDate] = useState(initial.date || addDays(14))
  const [pax, setPax] = useState(Number(initial.pax) || 1)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (initial.from) setFrom(initial.from)
    if (initial.to) setTo(initial.to)
    if (initial.date) setDate(initial.date)
    if (initial.pax) setPax(Number(initial.pax))
  }, [initial.from, initial.to, initial.date, initial.pax])

  const intl = (() => {
    const a = airports.find((x) => x.code === from), b = airports.find((x) => x.code === to)
    return a && b ? !(a.domestic && b.domestic) : null
  })()

  function submit(e) {
    e.preventDefault()
    if (from === to) return setErr('Departure and arrival cities must be different.')
    if (!date || date < todayISO()) return setErr('Choose today or a future date.')
    setErr(''); setBusy(true)
    nav(`/flights?${new URLSearchParams({ from, to, date, pax })}`)
  }
  useEffect(() => setBusy(false), [initial.from, initial.to, initial.date, initial.pax])

  return (
    <form className={`searchcard ${compact ? 'compact' : ''}`} onSubmit={submit}>
      <div className="search-grid">
        <AirportPicker id={`from-${compact ? 'c' : 'h'}`} label="From" value={from} onChange={setFrom} airports={airports} />
        <button type="button" className="swap" onClick={() => { setFrom(to); setTo(from) }} aria-label="Swap airports">
          <ArrowLeftRight size={18} />
        </button>
        <AirportPicker id={`to-${compact ? 'c' : 'h'}`} label="To" value={to} onChange={setTo} airports={airports} />
        <div className="dategroup">
          <label htmlFor={`d-${compact ? 'c' : 'h'}`} className="picker-label">Departure</label>
          <div className="date-box"><CalendarDays size={17} />
            <input id={`d-${compact ? 'c' : 'h'}`} type="date" min={todayISO()} max={addDays(330)} value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <small className="picker-sub">One way</small>
        </div>
        <div className="paxgroup">
          <span className="picker-label">Travellers</span>
          <div className="pax-box"><Users size={17} />
            <button type="button" onClick={() => setPax(Math.max(1, pax - 1))} aria-label="Fewer travellers"><Minus size={14} /></button>
            <b>{pax}</b>
            <button type="button" onClick={() => setPax(Math.min(9, pax + 1))} aria-label="More travellers"><Plus size={14} /></button>
          </div>
          <small className="picker-sub">Economy or business</small>
        </div>
        <Button type="submit" loading={busy} className="search-go"><Search size={18} /> Search flights</Button>
      </div>
      <div className="search-foot">
        {intl !== null && <span className={`chip ${intl ? 'intl' : 'dom'}`}>{intl ? 'International route · passport needed' : 'Domestic route'}</span>}
        {err && <span className="form-err" role="alert">{err}</span>}
      </div>
    </form>
  )
}

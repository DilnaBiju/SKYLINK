import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowRight, Plane } from 'lucide-react'
import { api } from '../api.js'
import { draft } from '../booking.jsx'
import Stepper from '../components/Stepper.jsx'
import { Button, ErrorBox, Loading } from '../components/ui.jsx'
import { dur, hm, inr, longDate } from '../utils.js'

const COLS = ['A', 'B', 'C', null, 'D', 'E', 'F']

export default function Seats() {
  const { flightId } = useParams()
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const pax = Math.min(9, Math.max(1, Number(sp.get('pax')) || draft.get(flightId)?.pax || 1))
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [picked, setPicked] = useState(() => draft.get(flightId)?.seats || [])
  const [hint, setHint] = useState('')

  useEffect(() => {
    api.seats(flightId).then((d) => {
      setData(d)
      const free = new Set(d.rows.flatMap((r) => r.seats.filter((s) => s.available).map((s) => s.seat_no)))
      setPicked((p) => p.filter((s) => free.has(s)).slice(0, pax))
    }).catch((e) => setError(e.message))
  }, [flightId, pax])

  const seatInfo = useMemo(() => {
    const m = {}
    data?.rows.forEach((r) => r.seats.forEach((s) => { m[s.seat_no] = s }))
    return m
  }, [data])

  function toggle(s) {
    setHint('')
    if (picked.includes(s.seat_no)) return setPicked(picked.filter((x) => x !== s.seat_no))
    if (picked.length >= pax) {
      if (pax === 1) return setPicked([s.seat_no])
      return setHint(`You are booking ${pax} seats. Tap a selected seat to release it first.`)
    }
    setPicked([...picked, s.seat_no])
  }

  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox><Link className="btn btn-ghost" to="/">Back to search</Link></div>
  if (!data) return <Loading label="Opening the seat map" />
  const f = data.flight
  const extra = picked.reduce((n, s) => n + (seatInfo[s]?.price_add || 0), 0)
  const rowsOut = []
  let lastCabin = null
  data.rows.forEach((r) => {
    if (r.cabin !== lastCabin) { rowsOut.push({ divider: r.cabin }); lastCabin = r.cabin }
    rowsOut.push(r)
  })

  function next() {
    if (picked.length !== pax) return setHint(`Choose ${pax - picked.length} more seat${pax - picked.length > 1 ? 's' : ''} to continue.`)
    draft.set({ flightId, pax, seats: picked })
    nav(`/book/${flightId}/passengers`)
  }

  return (
    <div className="container">
      <Stepper current={1} />
      <div className="booking-grid">
        <section>
          <h1 className="h1s">Choose your seats</h1>
          <p className="lead">{pax === 1 ? 'Pick one seat.' : `Pick ${pax} seats, one for each traveller.`} Seats are held for you once you continue.</p>
          <ul className="legend">
            <li><i className="seat free" /> Free</li>
            <li><i className="seat legroom" /> Extra legroom</li>
            <li><i className="seat business" /> Business</li>
            <li><i className="seat mine" /> Yours</li>
            <li><i className="seat taken" /> Taken</li>
          </ul>
          <div className="cabin" role="group" aria-label="Seat map">
            <div className="nose"><Plane size={26} /></div>
            <div className="colhead">{COLS.map((c, i) => <span key={i}>{c}</span>)}</div>
            {rowsOut.map((r, i) => r.divider ? (
              <div className="cabin-divider" key={`d${i}`}><span>{r.divider === 'BUSINESS' ? 'Business class' : 'Economy'}</span></div>
            ) : (
              <div className="seat-row" key={r.row}>
                {COLS.map((c, j) => {
                  if (c === null) return <span key={j} className="rownum">{r.row}</span>
                  const s = r.seats.find((x) => x.col === c)
                  if (!s) return <span key={j} className="seat-gap" />
                  const mine = picked.includes(s.seat_no)
                  return (
                    <button key={j} type="button" disabled={!s.available}
                      className={`seat ${!s.available ? 'taken' : mine ? 'mine' : s.kind === 'business' ? 'business' : s.kind === 'legroom' ? 'legroom' : 'free'}`}
                      aria-label={`Seat ${s.seat_no}${s.price_add ? `, ${inr(s.price_add)} extra` : ''}${!s.available ? ', taken' : ''}`}
                      aria-pressed={mine} onClick={() => toggle(s)}>{mine ? s.seat_no : ''}</button>
                  )
                })}
              </div>
            ))}
          </div>
        </section>

        <aside className="summary sticky">
          <div className="sum-route"><b>{f.origin}</b><span className="sum-line"><Plane size={16} /></span><b>{f.destination}</b></div>
          <p className="sum-sub">{f.airline} {f.flight_number}</p>
          <p className="sum-sub">{longDate(f.departure)}</p>
          <p className="sum-sub">{hm(f.departure)} → {hm(f.arrival)} · {dur(f.duration_min)}</p>
          <hr />
          <div className="sum-seats">
            {Array.from({ length: pax }).map((_, i) => (
              <div key={i} className={`sum-seat ${picked[i] ? 'filled' : ''}`}>
                <span>Traveller {i + 1}</span>
                <b>{picked[i] || 'Not chosen'}</b>
                {picked[i] && <em>{seatInfo[picked[i]]?.price_add ? `+${inr(seatInfo[picked[i]].price_add)}` : 'Free'}</em>}
              </div>
            ))}
          </div>
          <hr />
          <div className="sum-line-item"><span>Fare × {pax}</span><b>{inr(f.fare * pax)}</b></div>
          <div className="sum-line-item"><span>Seat fees</span><b>{inr(extra)}</b></div>
          <p className="fine">Taxes and offers are added at checkout.</p>
          {hint && <div className="notice warn" role="alert">{hint}</div>}
          <Button className="full" onClick={next}>Continue to passengers <ArrowRight size={17} /></Button>
        </aside>
      </div>
    </div>
  )
}

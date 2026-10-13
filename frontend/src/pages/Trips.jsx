import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Plane, Ticket } from 'lucide-react'
import { api } from '../api.js'
import { Empty, ErrorBox, Loading, PageHead } from '../components/ui.jsx'
import { hm, inr, longDate } from '../utils.js'

const TABS = [['upcoming', 'Upcoming'], ['past', 'Past'], ['cancelled', 'Cancelled']]

export default function Trips() {
  const [list, setList] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('upcoming')
  useEffect(() => { api.bookings().then(setList).catch((e) => setError(e.message)) }, [])

  const groups = useMemo(() => {
    const now = new Date().toISOString().slice(0, 16)
    const g = { upcoming: [], past: [], cancelled: [] }
    ;(list || []).forEach((b) => {
      if (b.status === 'CANCELLED') g.cancelled.push(b)
      else if (b.flight.departure < now) g.past.push(b)
      else g.upcoming.push(b)
    })
    return g
  }, [list])

  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox></div>
  if (!list) return <Loading label="Finding your trips" />

  const shown = groups[tab]
  return (
    <div className="container narrow-ish">
      <PageHead title="My trips" sub="Open a trip to view the e-ticket, download it or cancel." />
      <div className="seg wide" role="tablist">
        {TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l} <i>{groups[k].length}</i></button>)}
      </div>
      {shown.length === 0 ? (
        <Empty icon={<Ticket size={34} />} title={tab === 'upcoming' ? 'No upcoming trips' : `No ${tab} trips`}
          text={tab === 'upcoming' ? 'Search a route to book your next flight.' : 'Nothing to show here yet.'}
          action={tab === 'upcoming' ? <Link to="/" className="btn btn-gold">Search flights</Link> : null} />
      ) : (
        <div className="trip-list">
          {shown.map((b) => (
            <Link key={b.pnr} to={b.status === 'PENDING_PAYMENT' ? `/checkout/${b.pnr}` : `/trips/${b.pnr}`} className="trip">
              <span className="trip-route"><b>{b.flight.origin}</b><Plane size={15} /><b>{b.flight.destination}</b></span>
              <span className="trip-meta">
                <span>{b.flight.origin_city} to {b.flight.destination_city}</span>
                <small>{longDate(b.flight.departure)} · {hm(b.flight.departure)} · {b.flight.flight_number} · {b.pax_count} traveller{b.pax_count > 1 ? 's' : ''}</small>
              </span>
              <span className="trip-end">
                <span className={`status ${b.status}`}>{b.status === 'PENDING_PAYMENT' ? 'Payment pending' : b.status.toLowerCase()}</span>
                <b>{inr(b.total)}</b>
              </span>
              <ChevronRight size={18} className="chev" />
              <small className="pnr">PNR {b.pnr}</small>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

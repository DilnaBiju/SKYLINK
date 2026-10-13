import { motion } from 'framer-motion'
import { Armchair, Bell, TrendingDown } from 'lucide-react'
import { dur, hm, inr } from '../utils.js'
import { Button } from './ui.jsx'

export default function FlightCard({ f, pax, index, onSelect, onTrack, tracking, busy }) {
  const dropped = f.fare < f.prev_fare
  const pct = dropped ? Math.round((1 - f.fare / f.prev_fare) * 100) : 0
  return (
    <motion.article className="flightcard" layout
      initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.05, 0.4) }}>
      <div className="fc-airline">
        <span className={`logo-tile code-${f.airline_code}`}>{f.airline_code}</span>
        <div>
          <b>{f.airline}</b>
          <small>{f.flight_number} · {f.aircraft}</small>
        </div>
      </div>
      <div className="fc-times">
        <div><strong>{hm(f.departure)}</strong><small>{f.origin}</small></div>
        <div className="fc-path">
          <small>{dur(f.duration_min)}</small>
          <span className="fc-line"><i />{f.stops > 0 && <u />}</span>
          <small className={f.stops ? 'stop' : 'nonstop'}>{f.stops === 0 ? 'Non-stop' : `1 stop · ${f.via_city}`}</small>
        </div>
        <div><strong>{hm(f.arrival)}{f.arrives_next_day && <sup>+1</sup>}</strong><small>{f.destination}</small></div>
      </div>
      <div className="fc-price">
        {dropped && <span className="drop-chip"><TrendingDown size={13} /> {pct}% lower</span>}
        <strong>{inr(f.fare)}</strong>
        <small>per traveller{pax > 1 ? ` · ${inr(f.fare * pax)} for ${pax}` : ''}</small>
        <div className="fc-actions">
          <Button size="sm" onClick={() => onSelect(f)} loading={busy}><Armchair size={16} /> Select seats</Button>
          <button className={`icon-btn ${tracking ? 'on' : ''}`} onClick={() => onTrack(f)} aria-label={tracking ? 'Tracking this fare' : 'Track this fare'} title={tracking ? 'Tracking this fare' : 'Email me if this fare drops'}>
            <Bell size={16} />
          </button>
        </div>
        <small className={`seats-left ${f.available_seats < 15 ? 'low' : ''}`}>{f.available_seats} seats left</small>
      </div>
    </motion.article>
  )
}

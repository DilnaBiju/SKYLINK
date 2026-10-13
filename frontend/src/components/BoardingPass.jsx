import { QRCodeSVG } from 'qrcode.react'
import { Plane } from 'lucide-react'
import { dur, hm, inr, longDate } from '../utils.js'

export default function BoardingPass({ b }) {
  const f = b.flight
  return (
    <article className="pass">
      <div className="pass-main">
        <header className="pass-head">
          <span className="brand small"><span className="brand-mark"><Plane size={14} /></span> SkyLink</span>
          <span className="pass-class">{f.airline} · {f.flight_number}</span>
        </header>
        <div className="pass-route">
          <div><strong>{f.origin}</strong><span>{f.origin_city}</span><small>{hm(f.departure)}</small></div>
          <div className="pass-mid">
            <span className="pass-trail"><Plane size={20} /></span>
            <small>{dur(f.duration_min)} · {f.stops === 0 ? 'Non-stop' : `via ${f.via}`}</small>
          </div>
          <div className="r"><strong>{f.destination}</strong><span>{f.destination_city}</span><small>{hm(f.arrival)}{f.arrives_next_day ? ' +1' : ''}</small></div>
        </div>
        <dl className="pass-meta">
          <div><dt>Date</dt><dd>{longDate(f.departure)}</dd></div>
          <div><dt>Booking ref (PNR)</dt><dd className="mono">{b.pnr}</dd></div>
          <div><dt>Status</dt><dd><span className={`status ${b.status}`}>{b.status.replace('_', ' ')}</span></dd></div>
          <div><dt>Paid</dt><dd>{inr(b.total)}{b.payment ? ` · ${b.payment.method === 'NETBANKING' ? 'Net banking' : b.payment.method === 'CARD' ? `Card •••• ${b.payment.card_last4}` : 'UPI'}` : ''}</dd></div>
        </dl>
        <table className="pass-pax">
          <thead><tr><th>Passenger</th><th>Seat</th><th>Ticket number</th></tr></thead>
          <tbody>{b.passengers.map((p) => <tr key={p.seat_no}><td>{p.full_name}</td><td className="mono">{p.seat_no}</td><td className="mono">{p.ticket_number || '—'}</td></tr>)}</tbody>
        </table>
      </div>
      <div className="pass-stub">
        <QRCodeSVG value={`SKYLINK|${b.pnr}|${f.flight_number}|${f.departure.slice(0, 10)}`} size={118} bgColor="transparent" fgColor="#0d1b3e" />
        <span className="barcode" aria-hidden />
        <small>Present at check-in</small>
      </div>
    </article>
  )
}

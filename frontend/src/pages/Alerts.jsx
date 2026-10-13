import { useEffect, useState } from 'react'
import { Bell, BellOff, FlaskConical, Mail, Trash2, TrendingDown } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { useToast } from '../toast.jsx'
import AirportPicker from '../components/AirportPicker.jsx'
import { useAirports } from '../components/SearchForm.jsx'
import { Button, Empty, ErrorBox, Field, Loading, PageHead } from '../components/ui.jsx'
import { addDays, inr, longDate, todayISO } from '../utils.js'

export default function Alerts() {
  const { user } = useAuth()
  const toast = useToast()
  const airports = useAirports()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [from, setFrom] = useState('DEL')
  const [to, setTo] = useState('BOM')
  const [date, setDate] = useState(addDays(21))
  const [target, setTarget] = useState('')
  const [email, setEmail] = useState(user.email)
  const [busy, setBusy] = useState(false)
  const [working, setWorking] = useState(null)

  const load = () => api.alerts().then(setData).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  async function add(e) {
    e.preventDefault()
    if (from === to) return toast.error('Choose two different airports.')
    setBusy(true)
    try {
      await api.createAlert({ origin: from, destination: to, travel_date: date, email, target_price: target ? Number(target) : null })
      toast.success('Fare alert saved. We will email you when the fare drops.')
      setTarget(''); await load()
    } catch (x) { toast.error(x.message) } finally { setBusy(false) }
  }

  async function act(id, fn, ok) {
    setWorking(id)
    try { const r = await fn(); if (ok) toast.success(typeof ok === 'function' ? ok(r) : ok); await load() }
    catch (x) { toast.error(x.message) } finally { setWorking(null) }
  }

  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox></div>
  if (!data) return <Loading label="Loading your alerts" />

  return (
    <div className="container narrow-ish">
      <PageHead title="Fare alerts" sub="Follow a route or a single flight. When the price falls we email you with the new fare and a discount code." />

      <form className="card" onSubmit={add}>
        <h2><Bell size={19} /> Follow a route</h2>
        <div className="alert-grid">
          <AirportPicker id="al-from" label="From" value={from} onChange={setFrom} airports={airports} />
          <AirportPicker id="al-to" label="To" value={to} onChange={setTo} airports={airports} />
          <Field label="Travel date"><input type="date" min={todayISO()} max={addDays(330)} value={date} onChange={(e) => setDate(e.target.value)} required /></Field>
          <Field label="Target price (optional)" hint="Only email me at or below this fare"><input type="number" min="500" step="50" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="e.g. 4500" /></Field>
          <Field label="Send alerts to"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
        </div>
        <Button type="submit" loading={busy}><Bell size={16} /> Start watching</Button>
        <p className="fine">To follow one specific flight, tap the bell on that flight in the search results.</p>
      </form>

      <div className="notice info">
        <Mail size={18} />
        <span>{data.email_mode === 'smtp'
          ? 'Email delivery is on. Alerts go to the address you set above.'
          : 'No email server is configured yet, so alert emails are saved as HTML files in backend/outbox. Add SMTP details in backend/.env to send them for real.'}</span>
      </div>

      <h2 className="subhead">Your alerts</h2>
      {data.alerts.length === 0 ? (
        <Empty icon={<BellOff size={32} />} title="No alerts yet" text="Follow a route above, or tap the bell on any flight in your search results." />
      ) : (
        <div className="alert-list">
          {data.alerts.map((a) => {
            const cur = a.current_price
            const diff = cur != null ? cur - a.baseline_price : 0
            return (
              <article key={a.id} className={`alert-item ${a.active ? '' : 'off'}`}>
                <div className="ai-main">
                  <b>{a.origin_city} to {a.destination_city}</b>
                  <small>{longDate(a.travel_date)} · {a.flight_label ? `Flight ${a.flight_label}` : 'Cheapest flight on the day'}</small>
                  <small>Emails to {a.email}{a.target_price ? ` · target ${inr(a.target_price)}` : ''}{a.notify_count ? ` · ${a.notify_count} sent` : ''}</small>
                </div>
                <div className="ai-price">
                  <small>Now</small>
                  <b>{cur != null ? inr(cur) : '—'}</b>
                  {cur != null && <em className={diff < 0 ? 'down' : diff > 0 ? 'up' : ''}>{diff < 0 ? <TrendingDown size={13} /> : null}{diff === 0 ? 'unchanged' : `${diff < 0 ? '' : '+'}${inr(diff)} since you started`}</em>}
                </div>
                <div className="ai-actions">
                  {data.dev_tools && a.active && (
                    <Button size="sm" variant="ghost" loading={working === a.id} onClick={() => act(a.id, () => api.simulateDrop(a.id), (r) => `Fare dropped to ${inr(r.new)}. Alert email ${r.mode === 'smtp' ? 'sent' : 'saved in backend/outbox'}.`)} title="Demo tool: lowers this fare about 10% and runs the real alert check">
                      <FlaskConical size={15} /> Simulate fare drop
                    </Button>
                  )}
                  <button className="btn btn-ghost btn-sm" disabled={working === a.id} onClick={() => act(a.id, () => api.toggleAlert(a.id), a.active ? 'Alert paused.' : 'Alert resumed.')}>{a.active ? 'Pause' : 'Resume'}</button>
                  <button className="icon-btn danger" aria-label="Delete alert" onClick={() => act(a.id, () => api.deleteAlert(a.id), 'Alert deleted.')}><Trash2 size={16} /></button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}

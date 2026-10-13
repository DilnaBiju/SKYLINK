import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { Building2, CheckCircle2, CreditCard, Smartphone, Timer, XCircle } from 'lucide-react'
import { api } from '../api.js'
import { draft } from '../booking.jsx'
import { useToast } from '../toast.jsx'
import Stepper from '../components/Stepper.jsx'
import { Button, ErrorBox, Field, Loading } from '../components/ui.jsx'
import { hm, inr, longDate } from '../utils.js'

const METHODS = [['UPI', 'UPI', Smartphone], ['CARD', 'Card', CreditCard], ['NETBANKING', 'Net banking', Building2]]

function useCountdown(iso) {
  const [left, setLeft] = useState(null)
  useEffect(() => {
    if (!iso) return
    const end = new Date(iso).getTime()
    const tick = () => setLeft(Math.max(0, Math.floor((end - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [iso])
  return left
}

export default function Checkout() {
  const { pnr } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const [b, setB] = useState(null)
  const [error, setError] = useState('')
  const [method, setMethod] = useState('UPI')
  const [upi, setUpi] = useState('')
  const [card, setCard] = useState({ number: '', name: '', expiry: '', cvv: '' })
  const [bank, setBank] = useState('')
  const [banks, setBanks] = useState([])
  const [busy, setBusy] = useState(false)
  const [pay, setPay] = useState(null)          // pending UPI payment
  const [failure, setFailure] = useState('')
  const poll = useRef(null)
  const left = useCountdown(b?.status === 'PENDING_PAYMENT' ? b.hold_until : null)

  useEffect(() => {
    api.booking(pnr).then((x) => {
      if (x.status === 'CONFIRMED') nav(`/ticket/${pnr}`, { replace: true })
      else setB(x)
    }).catch((e) => setError(e.message))
    api.banks().then(setBanks).catch(() => {})
    return () => clearInterval(poll.current)
  }, [pnr])  // eslint-disable-line

  useEffect(() => {
    if (left === 0 && b?.status === 'PENDING_PAYMENT') { clearInterval(poll.current); setB((x) => ({ ...x, status: 'EXPIRED' })) }
  }, [left])  // eslint-disable-line

  function done() { draft.clear(); nav(`/ticket/${pnr}`) }

  function watch(id) {
    clearInterval(poll.current)
    poll.current = setInterval(async () => {
      try {
        const s = await api.paymentStatus(id)
        if (s.status === 'SUCCESS') { clearInterval(poll.current); done() }
        if (s.status === 'FAILED') { clearInterval(poll.current); setPay(null); setFailure(s.failure_reason || 'Payment failed.') }
      } catch { /* keep polling */ }
    }, 2000)
  }

  async function start(e) {
    e.preventDefault()
    setFailure(''); setBusy(true)
    try {
      const body = { pnr, method }
      if (method === 'UPI') body.upi_id = upi.trim()
      if (method === 'CARD') Object.assign(body, { card_number: card.number, card_name: card.name, card_expiry: card.expiry, card_cvv: card.cvv })
      if (method === 'NETBANKING') body.bank = bank
      const r = await api.startPayment(body)
      if (r.status === 'SUCCESS') return done()
      if (r.status === 'FAILED') setFailure(r.failure_reason)
      else { setPay(r); watch(r.payment_id) }
    } catch (err) {
      setFailure(err.message)
      if (err.status === 409) setB((x) => ({ ...x, status: 'EXPIRED' }))
    } finally { setBusy(false) }
  }

  async function resolve(outcome) {
    setBusy(true)
    try {
      const r = await api.resolvePayment(pay.payment_id, outcome)
      clearInterval(poll.current)
      if (r.status === 'SUCCESS') done()
      else { setPay(null); setFailure(r.failure_reason || 'Payment failed.') }
    } catch (err) { toast.error(err.message); setPay(null) } finally { setBusy(false) }
  }

  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox></div>
  if (!b) return <Loading label="Loading your booking" />

  if (b.status === 'EXPIRED' || b.status === 'CANCELLED') {
    return (
      <div className="container narrow">
        <div className="empty">
          <Timer size={34} />
          <h3>Your seat hold ended</h3>
          <p>Seats are held for 10 minutes while you pay. Nothing was charged. Pick your seats again to continue.</p>
          <button className="btn btn-gold" onClick={() => nav(`/book/${b.flight.id}/seats?pax=${b.pax_count}`)}>Choose seats again</button>
        </div>
      </div>
    )
  }

  const f = b.flight
  const mm = left != null ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` : '--:--'

  return (
    <div className="container">
      <Stepper current={3} />
      <div className="booking-grid">
        <section>
          <div className="pay-top">
            <div><h1 className="h1s">Pay {inr(b.total)}</h1><p className="lead">Booking {b.pnr}</p></div>
            <div className={`timer ${left != null && left < 120 ? 'urgent' : ''}`}><Timer size={16} /> Seats held for {mm}</div>
          </div>

          {!pay && (
            <form className="card" onSubmit={start} noValidate>
              <div className="methods" role="tablist">
                {METHODS.map(([k, l, I]) => (
                  <button type="button" key={k} role="tab" aria-selected={method === k} className={method === k ? 'on' : ''} onClick={() => { setMethod(k); setFailure('') }}>
                    <I size={20} /> {l}
                  </button>
                ))}
              </div>
              <ErrorBox>{failure}</ErrorBox>

              {method === 'UPI' && (
                <div className="method-body">
                  <Field label="Your UPI ID" hint="A payment request is sent to this ID. You approve it in your UPI app.">
                    <input value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="yourname@okaxis" autoComplete="off" inputMode="email" />
                  </Field>
                  <div className="upi-apps"><span>Works with</span><b>GPay</b><b>PhonePe</b><b>Paytm</b><b>BHIM</b></div>
                </div>
              )}
              {method === 'CARD' && (
                <div className="method-body form-grid">
                  <Field label="Card number" hint="Sandbox: use 4242 4242 4242 4242. 4000 0000 0000 0002 simulates a decline.">
                    <input inputMode="numeric" autoComplete="cc-number" value={card.number} maxLength={23}
                      onChange={(e) => setCard({ ...card, number: e.target.value.replace(/[^\d ]/g, '').replace(/(\d{4})(?=\d)/g, '$1 ') })} placeholder="4242 4242 4242 4242" />
                  </Field>
                  <Field label="Name on card"><input autoComplete="cc-name" value={card.name} onChange={(e) => setCard({ ...card, name: e.target.value })} /></Field>
                  <Field label="Expiry (MM/YY)"><input autoComplete="cc-exp" placeholder="12/30" maxLength={5} value={card.expiry}
                    onChange={(e) => { let v = e.target.value.replace(/[^\d/]/g, ''); if (/^\d{2}$/.test(v) && e.nativeEvent.inputType !== 'deleteContentBackward') v += '/'; setCard({ ...card, expiry: v }) }} /></Field>
                  <Field label="CVV"><input type="password" inputMode="numeric" autoComplete="cc-csc" maxLength={4} value={card.cvv} onChange={(e) => setCard({ ...card, cvv: e.target.value.replace(/\D/g, '') })} /></Field>
                </div>
              )}
              {method === 'NETBANKING' && (
                <div className="method-body">
                  <Field label="Choose your bank">
                    <select value={bank} onChange={(e) => setBank(e.target.value)}><option value="">Select a bank</option>{banks.map((x) => <option key={x}>{x}</option>)}</select>
                  </Field>
                </div>
              )}
              <p className="sandbox-note"><b>Sandbox payments.</b> No money is taken and no bank is contacted. This works like a real gateway so one can be connected later.</p>
              <Button type="submit" className="full" loading={busy}>{method === 'UPI' ? `Send request for ${inr(b.total)}` : `Pay ${inr(b.total)}`}</Button>
            </form>
          )}

          {pay && (
            <div className="card upi-wait" aria-live="polite">
              <div className="upi-wait-head"><span className="pulse" /><h2>Waiting for your approval</h2></div>
              <p>We sent a request for <b>{inr(pay.amount)}</b> to <b>{upi}</b>. Open your UPI app and approve it. This page moves on by itself once the payment goes through.</p>
              <div className="upi-qr">
                <QRCodeSVG value={pay.upi_link} size={150} bgColor="transparent" fgColor="#0d1b3e" />
                <small>Or scan with any UPI app<br />Ref {pay.txn_ref}</small>
              </div>
              {pay.sandbox && (
                <div className="sandbox-panel">
                  <b>Sandbox UPI app</b>
                  <p>No real UPI app is connected here, so choose what the customer does:</p>
                  <div className="row">
                    <Button loading={busy} onClick={() => resolve('approve')}><CheckCircle2 size={16} /> Approve payment</Button>
                    <Button variant="ghost" loading={busy} onClick={() => resolve('decline')}><XCircle size={16} /> Decline</Button>
                  </div>
                </div>
              )}
              <button className="linklike" onClick={() => { clearInterval(poll.current); setPay(null) }}>Use a different payment method</button>
            </div>
          )}
        </section>

        <aside className="summary sticky">
          <div className="sum-route"><b>{f.origin}</b><span className="sum-line">→</span><b>{f.destination}</b></div>
          <p className="sum-sub">{f.airline} {f.flight_number} · {longDate(f.departure)}</p>
          <p className="sum-sub">{hm(f.departure)} → {hm(f.arrival)}</p>
          <hr />
          {b.passengers.map((p) => <div className="sum-line-item" key={p.seat_no}><span>{p.full_name}</span><b>Seat {p.seat_no}</b></div>)}
          <hr />
          <div className="sum-line-item"><span>Fare × {b.pax_count}</span><b>{inr(b.base_amount)}</b></div>
          <div className="sum-line-item"><span>Seat fees</span><b>{inr(b.seat_amount)}</b></div>
          {b.discount > 0 && <div className="sum-line-item good"><span>Offer {b.promo_code}</span><b>− {inr(b.discount)}</b></div>}
          <div className="sum-line-item"><span>Taxes and airport fees</span><b>{inr(b.taxes)}</b></div>
          <div className="sum-total"><span>Total</span><b>{inr(b.total)}</b></div>
        </aside>
      </div>
    </div>
  )
}

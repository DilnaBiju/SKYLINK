import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Plane, Tag } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { draft } from '../booking.jsx'
import { useToast } from '../toast.jsx'
import Stepper from '../components/Stepper.jsx'
import { Button, ErrorBox, Field, Loading } from '../components/ui.jsx'
import { hm, inr, longDate } from '../utils.js'

export default function Passengers() {
  const { flightId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const d = draft.get(flightId)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [pax, setPax] = useState(() => (d?.seats || []).map((seat, i) => ({
    full_name: i === 0 ? user.full_name : '', age: '', gender: i === 0 ? user.gender || '' : '',
    passport_no: i === 0 ? user.passport_no || '' : '', seat_no: seat,
  })))
  const [email, setEmail] = useState(user.email)
  const [phone, setPhone] = useState(user.phone || '')
  const [promo, setPromo] = useState('')
  const [applied, setApplied] = useState(null)
  const [promoErr, setPromoErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [errs, setErrs] = useState({})

  useEffect(() => {
    if (!d || !d.seats?.length) { nav(`/book/${flightId}/seats`, { replace: true }); return }
    api.seats(flightId).then(setData).catch((e) => setError(e.message))
  }, [flightId])  // eslint-disable-line

  if (!d?.seats?.length) return null
  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox></div>
  if (!data) return <Loading label="Preparing passenger details" />

  const f = data.flight
  const price = {}
  data.rows.forEach((r) => r.seats.forEach((s) => { price[s.seat_no] = s.price_add }))
  const seatFees = d.seats.reduce((n, s) => n + (price[s] || 0), 0)
  const subtotal = f.fare * d.seats.length + seatFees
  const discount = applied?.discount || 0
  const taxes = Math.round((subtotal - discount) * (f.international ? 0.12 : 0.08))
  const total = subtotal - discount + taxes

  const set = (i, k, v) => setPax((p) => p.map((x, j) => (j === i ? { ...x, [k]: v } : x)))

  async function applyPromo() {
    setPromoErr('')
    if (!promo.trim()) return
    try {
      const r = await api.validatePromo({ code: promo.trim(), flight_id: f.id, seat_nos: d.seats })
      setApplied(r); toast.success(`${r.code} applied: ${inr(r.discount)} off`)
    } catch (e) { setApplied(null); setPromoErr(e.message) }
  }

  function validate() {
    const e = {}
    pax.forEach((p, i) => {
      if (p.full_name.trim().length < 2) e[`n${i}`] = 'Enter the name as on the ID'
      const age = Number(p.age)
      if (!age || age < 2 || age > 120) e[`a${i}`] = 'Age 2–120'
      if (f.international && !/^[A-Za-z0-9]{6,9}$/.test(p.passport_no || '')) e[`p${i}`] = '6–9 letters or digits'
    })
    if (!/^\+?[0-9 \-]{8,16}$/.test(phone)) e.phone = 'Enter a valid phone number'
    return e
  }

  async function submit(ev) {
    ev.preventDefault()
    const e = validate()
    setErrs(e)
    if (Object.keys(e).length) return toast.error('Please fix the highlighted fields.')
    setBusy(true)
    try {
      const b = await api.createBooking({
        flight_id: f.id, contact_email: email, contact_phone: phone,
        promo_code: applied?.code || null,
        passengers: pax.map((p) => ({ full_name: p.full_name.trim(), age: Number(p.age), gender: p.gender || null, passport_no: p.passport_no || null, seat_no: p.seat_no })),
      })
      nav(`/checkout/${b.pnr}`)
    } catch (err) {
      toast.error(err.message)
      if (err.status === 409) nav(`/book/${flightId}/seats?pax=${d.pax}`)
      setBusy(false)
    }
  }

  return (
    <div className="container">
      <Stepper current={2} />
      <form className="booking-grid" onSubmit={submit} noValidate>
        <section>
          <h1 className="h1s">Who is travelling?</h1>
          <p className="lead">Enter names exactly as they appear on the ID{f.international ? ' or passport' : ''}.</p>
          {pax.map((p, i) => (
            <fieldset className="card pax-card" key={i}>
              <legend>Traveller {i + 1} <span className="seat-pill">Seat {p.seat_no}</span></legend>
              <div className="form-grid">
                <Field label="Full name" error={errs[`n${i}`]}><input value={p.full_name} onChange={(e) => set(i, 'full_name', e.target.value)} autoComplete="name" /></Field>
                <Field label="Age" error={errs[`a${i}`]}><input type="number" min="2" max="120" value={p.age} onChange={(e) => set(i, 'age', e.target.value)} /></Field>
                <Field label="Gender"><select value={p.gender} onChange={(e) => set(i, 'gender', e.target.value)}><option value="">Prefer not to say</option><option>Female</option><option>Male</option><option>Other</option></select></Field>
                {f.international && <Field label="Passport number" error={errs[`p${i}`]}><input value={p.passport_no} onChange={(e) => set(i, 'passport_no', e.target.value.toUpperCase())} maxLength={9} /></Field>}
              </div>
            </fieldset>
          ))}
          <fieldset className="card pax-card">
            <legend>Where should we send the ticket?</legend>
            <div className="form-grid">
              <Field label="Email"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
              <Field label="Mobile number" error={errs.phone}><input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="tel" /></Field>
            </div>
          </fieldset>
          <div className="nav-row">
            <Link to={`/book/${flightId}/seats?pax=${d.pax}`} className="btn btn-ghost"><ArrowLeft size={16} /> Change seats</Link>
          </div>
        </section>

        <aside className="summary sticky">
          <div className="sum-route"><b>{f.origin}</b><span className="sum-line"><Plane size={16} /></span><b>{f.destination}</b></div>
          <p className="sum-sub">{f.airline} {f.flight_number} · {longDate(f.departure)}</p>
          <p className="sum-sub">{hm(f.departure)} → {hm(f.arrival)}</p>
          <hr />
          <div className="sum-line-item"><span>Fare × {d.seats.length}</span><b>{inr(f.fare * d.seats.length)}</b></div>
          <div className="sum-line-item"><span>Seat fees</span><b>{inr(seatFees)}</b></div>
          {discount > 0 && <div className="sum-line-item good"><span>Offer {applied.code}</span><b>− {inr(discount)}</b></div>}
          <div className="sum-line-item"><span>Taxes and airport fees</span><b>{inr(taxes)}</b></div>
          <div className="sum-total"><span>Total</span><b>{inr(total)}</b></div>
          <div className="promo">
            <div className="promo-row">
              <Tag size={16} />
              <input value={promo} onChange={(e) => setPromo(e.target.value.toUpperCase())} placeholder="Promo code" aria-label="Promo code" />
              <button type="button" className="btn btn-ghost btn-sm" onClick={applyPromo}>{applied ? <Check size={14} /> : 'Apply'}</button>
            </div>
            {promoErr && <small className="field-error">{promoErr}</small>}
            {!applied && !promoErr && <small className="field-hint">Try SKYDROP, WELCOME300 or INTL1000.</small>}
          </div>
          <Button type="submit" className="full" loading={busy}>Continue to payment <ArrowRight size={17} /></Button>
        </aside>
      </form>
    </div>
  )
}

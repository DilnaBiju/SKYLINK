import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { Plane } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Button, ErrorBox, Field } from '../components/ui.jsx'

function Shell({ title, sub, children, foot }) {
  return (
    <div className="auth">
      <aside className="auth-art" aria-hidden>
        <div className="auth-sky"><Plane size={46} /></div>
        <h2>Your trips, tickets and fare alerts in one place.</h2>
        <ul><li>Manage and cancel bookings</li><li>Download e-tickets as PDF</li><li>Get emailed when a fare drops</li></ul>
      </aside>
      <section className="auth-form">
        <h1>{title}</h1>
        <p className="lead">{sub}</p>
        {children}
        <p className="auth-foot">{foot}</p>
      </section>
    </div>
  )
}

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const from = loc.state?.from || '/'
  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await login(email, password); nav(from, { replace: true }) } catch (x) { setErr(x.message); setBusy(false) }
  }
  return (
    <Shell title="Welcome back" sub={loc.state?.notice || 'Sign in to book flights and manage your trips.'}
      foot={<>New to SkyLink? <Link to="/register" state={loc.state}>Create an account</Link></>}>
      <form onSubmit={submit} className="stack">
        <ErrorBox>{err}</ErrorBox>
        <Field label="Email"><input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
        <Field label="Password"><input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></Field>
        <Link to="/forgot-password" className="small-link">Forgot password?</Link>
        <Button type="submit" className="full" loading={busy}>Sign in</Button>
      </form>
    </Shell>
  )
}

export function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [f, setF] = useState({ full_name: '', email: '', phone: '', password: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await register({ ...f, phone: f.phone || null }); nav(loc.state?.from || '/', { replace: true }) } catch (x) { setErr(x.message); setBusy(false) }
  }
  return (
    <Shell title="Create your account" sub="It takes a minute and saves you retyping details."
      foot={<>Already have an account? <Link to="/login" state={loc.state}>Sign in</Link></>}>
      <form onSubmit={submit} className="stack">
        <ErrorBox>{err}</ErrorBox>
        <Field label="Full name"><input value={f.full_name} onChange={set('full_name')} required minLength={2} autoComplete="name" autoFocus /></Field>
        <Field label="Email"><input type="email" value={f.email} onChange={set('email')} required autoComplete="email" /></Field>
        <Field label="Mobile number" hint="Optional"><input value={f.phone} onChange={set('phone')} inputMode="tel" autoComplete="tel" /></Field>
        <Field label="Password" hint="At least 8 characters"><input type="password" value={f.password} onChange={set('password')} required minLength={8} autoComplete="new-password" /></Field>
        <Button type="submit" className="full" loading={busy}>Create account</Button>
      </form>
    </Shell>
  )
}

export function Forgot() {
  const [email, setEmail] = useState('')
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true)
    try { setMsg((await api.forgot({ email })).message) } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  return (
    <Shell title="Reset your password" sub="Enter your email and we will send a reset link." foot={<Link to="/login">Back to sign in</Link>}>
      {msg ? <div className="notice ok">{msg}</div> : (
        <form onSubmit={submit} className="stack">
          <ErrorBox>{err}</ErrorBox>
          <Field label="Email"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
          <Button type="submit" className="full" loading={busy}>Send reset link</Button>
        </form>
      )}
    </Shell>
  )
}

export function Reset() {
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true)
    try { await api.reset({ token: sp.get('token') || '', password }); setDone(true); setTimeout(() => nav('/login'), 1500) } catch (x) { setErr(x.message); setBusy(false) }
  }
  return (
    <Shell title="Choose a new password" sub="Use at least 8 characters." foot={<Link to="/login">Back to sign in</Link>}>
      {done ? <div className="notice ok">Password updated. Taking you to sign in…</div> : (
        <form onSubmit={submit} className="stack">
          <ErrorBox>{err}</ErrorBox>
          <Field label="New password"><input type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required autoFocus /></Field>
          <Button type="submit" className="full" loading={busy}>Update password</Button>
        </form>
      )}
    </Shell>
  )
}

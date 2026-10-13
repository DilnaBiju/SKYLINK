import { useState } from 'react'
import { KeyRound, UserRound } from 'lucide-react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { useToast } from '../toast.jsx'
import { Button, ErrorBox, Field, PageHead } from '../components/ui.jsx'

export default function Account() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const [f, setF] = useState({
    full_name: user.full_name || '', phone: user.phone || '', dob: user.dob || '',
    gender: user.gender || '', nationality: user.nationality || '', passport_no: user.passport_no || '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [pw, setPw] = useState({ current_password: '', new_password: '' })
  const [pwBusy, setPwBusy] = useState(false)
  const [pwErr, setPwErr] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function save(e) {
    e.preventDefault(); setErr(''); setBusy(true)
    try {
      const u = await api.updateMe({ ...f, dob: f.dob || null, phone: f.phone || null, gender: f.gender || null })
      setUser(u); toast.success('Profile saved.')
    } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  async function changePw(e) {
    e.preventDefault(); setPwErr(''); setPwBusy(true)
    try {
      await api.changePassword(pw)
      setPw({ current_password: '', new_password: '' }); toast.success('Password changed.')
    } catch (x) { setPwErr(x.message) } finally { setPwBusy(false) }
  }

  return (
    <div className="container narrow-ish">
      <PageHead title="Your profile" sub="Saved details fill in faster when you book." />
      <div className="profile-hero">
        <span className="avatar">{user.full_name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()}</span>
        <div><b>{user.full_name}</b><small>{user.email} · member since {new Date(user.created_at).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</small></div>
      </div>

      <form className="card" onSubmit={save}>
        <h2><UserRound size={19} /> Personal details</h2>
        <ErrorBox>{err}</ErrorBox>
        <div className="form-grid">
          <Field label="Full name"><input value={f.full_name} onChange={set('full_name')} required minLength={2} /></Field>
          <Field label="Email" hint="Your sign-in email cannot be changed."><input value={user.email} disabled /></Field>
          <Field label="Mobile number"><input value={f.phone} onChange={set('phone')} inputMode="tel" placeholder="+91 98765 43210" /></Field>
          <Field label="Date of birth"><input type="date" value={f.dob} onChange={set('dob')} max={new Date().toISOString().slice(0, 10)} /></Field>
          <Field label="Gender"><select value={f.gender} onChange={set('gender')}><option value="">Prefer not to say</option><option>Female</option><option>Male</option><option>Other</option></select></Field>
          <Field label="Nationality"><input value={f.nationality} onChange={set('nationality')} placeholder="Indian" /></Field>
          <Field label="Passport number" hint="Optional. Used to fill international bookings."><input value={f.passport_no} onChange={(e) => setF({ ...f, passport_no: e.target.value.toUpperCase() })} maxLength={9} /></Field>
        </div>
        <Button type="submit" loading={busy}>Save changes</Button>
      </form>

      <form className="card" onSubmit={changePw}>
        <h2><KeyRound size={19} /> Password</h2>
        <ErrorBox>{pwErr}</ErrorBox>
        <div className="form-grid">
          <Field label="Current password"><input type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} required /></Field>
          <Field label="New password" hint="At least 8 characters."><input type="password" autoComplete="new-password" minLength={8} value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} required /></Field>
        </div>
        <Button type="submit" variant="ghost" loading={pwBusy}>Change password</Button>
      </form>
    </div>
  )
}

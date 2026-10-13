import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Bell, LogOut, Menu, Plane, Ticket, UserRound, X } from 'lucide-react'
import { useAuth } from '../auth.jsx'

export default function Header() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [loc.pathname])

  return (
    <header className="header">
      <Link to="/" className="brand" aria-label="SkyLink home">
        <span className="brand-mark"><Plane size={18} /></span>
        <span>Sky<b>Link</b></span>
      </Link>
      <button className="menu-btn" onClick={() => setOpen(!open)} aria-label="Menu" aria-expanded={open}>
        {open ? <X /> : <Menu />}
      </button>
      <nav className={open ? 'nav open' : 'nav'}>
        <NavLink to="/" end>Flights</NavLink>
        <NavLink to="/trips"><Ticket size={15} /> My trips</NavLink>
        <NavLink to="/alerts"><Bell size={15} /> Fare alerts</NavLink>
        <span className="nav-spacer" />
        {user ? (
          <>
            <NavLink to="/account" className="nav-user"><UserRound size={15} /> {user.full_name.split(' ')[0]}</NavLink>
            <button className="nav-out" onClick={() => { logout(); nav('/') }}><LogOut size={15} /> Sign out</button>
          </>
        ) : (
          <>
            <NavLink to="/login">Sign in</NavLink>
            <Link to="/register" className="btn btn-gold btn-sm">Create account</Link>
          </>
        )}
      </nav>
    </header>
  )
}

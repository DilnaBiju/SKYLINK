import { Plane } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-in">
        <span className="brand small"><span className="brand-mark"><Plane size={14} /></span> SkyLink</span>
        <nav>
          <Link to="/">Search flights</Link>
          <Link to="/trips">My trips</Link>
          <Link to="/alerts">Fare alerts</Link>
          <Link to="/account">Account</Link>
        </nav>
        <p>Academic project. Fares and schedules are simulated and payments run in a sandbox, so no real tickets are issued and no money moves.</p>
      </div>
    </footer>
  )
}

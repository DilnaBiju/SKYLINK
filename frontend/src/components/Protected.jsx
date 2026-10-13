import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { Loading } from './ui.jsx'

export default function Protected({ children }) {
  const { user, ready } = useAuth()
  const loc = useLocation()
  if (!ready) return <Loading label="Checking your session" />
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />
  return children
}

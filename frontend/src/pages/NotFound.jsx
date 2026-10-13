import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { Empty } from '../components/ui.jsx'

export default function NotFound() {
  return (
    <div className="container narrow">
      <Empty icon={<Compass size={34} />} title="This page is off the route map"
        text="The address may be mistyped or the page was moved."
        action={<Link to="/" className="btn btn-gold">Back to flight search</Link>} />
    </div>
  )
}

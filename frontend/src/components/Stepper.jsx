import { Check } from 'lucide-react'

const STEPS = ['Search', 'Seats', 'Passengers', 'Payment', 'Ticket']

export default function Stepper({ current }) {
  return (
    <ol className="stepper" aria-label="Booking progress">
      {STEPS.map((s, i) => (
        <li key={s} className={i < current ? 'done' : i === current ? 'now' : ''} aria-current={i === current ? 'step' : undefined}>
          <span className="dot">{i < current ? <Check size={13} /> : i + 1}</span>
          <span className="lbl">{s}</span>
        </li>
      ))}
    </ol>
  )
}

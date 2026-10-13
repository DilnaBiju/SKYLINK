import { useEffect, useRef, useState } from 'react'
import { inr } from '../utils.js'

const SCRAMBLE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
const reduce = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function Flap({ text, width }) {
  const target = text.toUpperCase().padEnd(width, ' ').slice(0, width)
  const [shown, setShown] = useState(reduce() ? target : ' '.repeat(width))
  const tick = useRef(0)

  useEffect(() => {
    if (reduce()) { setShown(target); return }
    tick.current = 0
    const id = setInterval(() => {
      tick.current += 1
      const t = tick.current
      setShown((prev) => {
        let out = ''
        for (let i = 0; i < width; i++) {
          const settleAt = 6 + i * 2
          if (t >= settleAt || target[i] === ' ') out += target[i]
          else out += SCRAMBLE[Math.floor(Math.random() * SCRAMBLE.length)]
        }
        return out === prev ? prev : out
      })
      if (t > 6 + width * 2) clearInterval(id)
    }, 55)
    return () => clearInterval(id)
  }, [target, width])

  return (
    <span className="flaps" aria-label={text}>
      {shown.split('').map((c, i) => (
        <span key={`${i}-${c}`} className={`flap ${c === target[i] ? 'set' : 'spin'}`} aria-hidden>{c === ' ' ? '\u00a0' : c}</span>
      ))}
    </span>
  )
}

const FALLBACK = [
  { departure: '06:40', destination_city: 'Mumbai', flight_number: '6E 204', from_fare: 3890 },
  { departure: '08:15', destination_city: 'Dubai', flight_number: 'EK 511', from_fare: 17450 },
  { departure: '09:55', destination_city: 'Singapore', flight_number: 'SQ 423', from_fare: 24310 },
  { departure: '11:30', destination_city: 'London', flight_number: 'BA 142', from_fare: 41200 },
  { departure: '13:05', destination_city: 'Bengaluru', flight_number: 'AI 807', from_fare: 4620 },
]

export default function DepartureBoard({ routes }) {
  const rows = routes && routes.length >= 3 ? routes : FALLBACK
  const pageSize = 4
  const pages = Math.ceil(rows.length / pageSize)
  const [page, setPage] = useState(0)
  useEffect(() => {
    if (pages < 2 || reduce()) return
    const id = setInterval(() => setPage((p) => (p + 1) % pages), 7000)
    return () => clearInterval(id)
  }, [pages])
  const view = rows.slice(page * pageSize, page * pageSize + pageSize)

  return (
    <div className="board" aria-label="Popular departures">
      <div className="board-head"><span>Popular departures</span><span className="board-live"><i /> fares update through the day</span></div>
      <div className="board-cols"><span>Time</span><span>To</span><span>Flight</span><span>From</span></div>
      {view.map((r, i) => (
        <div className="board-row" key={`${page}-${i}`}>
          <Flap text={r.departure} width={5} />
          <Flap text={r.destination_city} width={11} />
          <Flap text={r.flight_number} width={7} />
          <Flap text={inr(r.from_fare).replace(/\s/g, '')} width={8} />
        </div>
      ))}
      <div className="board-dots">{Array.from({ length: pages }).map((_, i) => <i key={i} className={i === page ? 'on' : ''} />)}</div>
    </div>
  )
}

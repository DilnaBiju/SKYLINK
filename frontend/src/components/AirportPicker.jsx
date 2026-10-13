import { useEffect, useMemo, useRef, useState } from 'react'
import { MapPin } from 'lucide-react'

export default function AirportPicker({ label, value, onChange, airports, id }) {
  const current = airports.find((a) => a.code === value)
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [hi, setHi] = useState(0)
  const box = useRef(null)

  const list = useMemo(() => {
    const s = q.trim().toLowerCase()
    const f = airports.filter((a) => !s || `${a.city} ${a.code} ${a.name} ${a.country}`.toLowerCase().includes(s))
    return f.slice(0, 40)
  }, [q, airports])

  useEffect(() => {
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const pick = (a) => { onChange(a.code); setOpen(false); setQ('') }
  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setHi((h) => Math.min(h + 1, list.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)) }
    else if (e.key === 'Enter' && open && list[hi]) { e.preventDefault(); pick(list[hi]) }
    else if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div className="picker" ref={box}>
      <label htmlFor={id} className="picker-label">{label}</label>
      <div className="picker-box" onClick={() => { setOpen(true); document.getElementById(id)?.focus() }}>
        <span className="picker-code">{current?.code || '---'}</span>
        <input id={id} autoComplete="off" role="combobox" aria-expanded={open} aria-controls={`${id}-list`}
          value={open ? q : current ? current.city : ''} placeholder="City or airport"
          onFocus={() => { setOpen(true); setQ(''); setHi(0) }}
          onChange={(e) => { setQ(e.target.value); setHi(0); setOpen(true) }} onKeyDown={onKey} />
      </div>
      <small className="picker-sub">{current ? current.name : 'Choose an airport'}</small>
      {open && (
        <ul className="picker-list" id={`${id}-list`} role="listbox">
          {list.length === 0 && <li className="picker-none">No airport matches “{q}”</li>}
          {list.map((a, i) => (
            <li key={a.code} role="option" aria-selected={a.code === value} className={i === hi ? 'hi' : ''}
              onMouseEnter={() => setHi(i)} onMouseDown={(e) => { e.preventDefault(); pick(a) }}>
              <MapPin size={15} />
              <span><b>{a.city}</b> <em>{a.country}</em><small>{a.name}</small></span>
              <code>{a.code}</code>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

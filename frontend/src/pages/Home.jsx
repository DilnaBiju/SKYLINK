import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Armchair, BellRing, FileText, Search, Smartphone } from 'lucide-react'
import { api } from '../api.js'
import SearchForm from '../components/SearchForm.jsx'
import DepartureBoard from '../components/DepartureBoard.jsx'
import { inr, shortDate } from '../utils.js'

const STEPS = [
  { icon: Search, t: 'Search any route', d: 'Domestic and international, with fares sorted for you.' },
  { icon: Armchair, t: 'Pick your seats', d: 'See the cabin and choose a seat for every traveller.' },
  { icon: Smartphone, t: 'Pay with UPI', d: 'Approve the request in your UPI app. Cards and net banking work too.' },
  { icon: FileText, t: 'Get your ticket', d: 'Download the e-ticket as PDF and find it in My trips.' },
]

export default function Home() {
  const nav = useNavigate()
  const [popular, setPopular] = useState(null)
  useEffect(() => { api.popular().then(setPopular).catch(() => setPopular([])) }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-in">
          <div className="hero-copy">
            <h1>Every route on the board, one booking away.</h1>
            <p>Compare domestic and international flights, choose your seat, pay with UPI and carry your ticket in your pocket.</p>
            <ul className="hero-points">
              <li>Seats held for 10 minutes while you pay</li>
              <li>Email alerts when a fare you follow drops</li>
            </ul>
          </div>
          <DepartureBoard routes={popular} />
        </div>
        <svg className="hero-arc" viewBox="0 0 1200 160" preserveAspectRatio="none" aria-hidden>
          <path id="arc" d="M0,150 C300,10 700,10 1200,120" fill="none" stroke="rgba(255,200,61,.35)" strokeWidth="2" strokeDasharray="4 9" />
          <g className="arc-plane"><path d="M-10 6l22-8-6 12-5-3-6 4z" fill="#ffc83d" /><animateMotion dur="14s" repeatCount="indefinite" rotate="auto"><mpath href="#arc" /></animateMotion></g>
        </svg>
      </section>

      <section className="container search-wrap">
        <SearchForm />
      </section>

      <section className="container section">
        <div className="section-head">
          <h2>Popular routes this fortnight</h2>
          <p>Lowest fare found for travel on {popular?.[0] ? shortDate(popular[0].date) : 'the date shown'}.</p>
        </div>
        <div className="route-grid">
          {(popular || Array.from({ length: 8 })).map((r, i) => r ? (
            <button key={i} className="route-ticket" onClick={() => nav(`/flights?${new URLSearchParams({ from: r.origin, to: r.destination, date: r.date, pax: 1 })}`)}>
              <span className="rt-codes"><b>{r.origin}</b><i /><b>{r.destination}</b></span>
              <span className="rt-cities">{r.origin_city} to {r.destination_city}</span>
              <span className="rt-foot"><em className={r.international ? 'intl' : 'dom'}>{r.international ? 'International' : 'Domestic'}</em><strong>{inr(r.from_fare)}</strong></span>
            </button>
          ) : <div key={i} className="route-ticket skeleton" />)}
        </div>
      </section>

      <section className="container section how">
        <div className="section-head"><h2>From search to ticket</h2></div>
        <ol className="how-list">
          {STEPS.map((s, i) => (
            <li key={s.t}>
              <span className="how-n">{i + 1}</span>
              <s.icon size={22} />
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="container section">
        <div className="alert-band">
          <BellRing size={30} />
          <div>
            <h2>Waiting for a lower fare?</h2>
            <p>Follow any flight and we email you when its price falls, along with a discount code you can use on that booking.</p>
          </div>
          <Link to="/alerts" className="btn btn-gold">Set a fare alert</Link>
        </div>
      </section>
    </>
  )
}

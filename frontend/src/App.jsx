import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Header from './components/Header.jsx'
import Footer from './components/Footer.jsx'
import Protected from './components/Protected.jsx'
import Home from './pages/Home.jsx'
import Results from './pages/Results.jsx'
import Seats from './pages/Seats.jsx'
import Passengers from './pages/Passengers.jsx'
import Checkout from './pages/Checkout.jsx'
import Ticket from './pages/Ticket.jsx'
import { Login, Register, Forgot, Reset } from './pages/AuthPages.jsx'
import Account from './pages/Account.jsx'
import Trips from './pages/Trips.jsx'
import TripDetail from './pages/TripDetail.jsx'
import Alerts from './pages/Alerts.jsx'
import NotFound from './pages/NotFound.jsx'

const guard = (el) => <Protected>{el}</Protected>

export default function App() {
  const loc = useLocation()
  useEffect(() => { window.scrollTo({ top: 0 }) }, [loc.pathname])
  return (
    <div className="app">
      <a href="#main" className="skip">Skip to content</a>
      <Header />
      <main id="main">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={loc.pathname} className="page"
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}>
            <Routes location={loc}>
              <Route path="/" element={<Home />} />
              <Route path="/flights" element={<Results />} />
              <Route path="/book/:flightId/seats" element={guard(<Seats />)} />
              <Route path="/book/:flightId/passengers" element={guard(<Passengers />)} />
              <Route path="/checkout/:pnr" element={guard(<Checkout />)} />
              <Route path="/ticket/:pnr" element={guard(<Ticket />)} />
              <Route path="/trips" element={guard(<Trips />)} />
              <Route path="/trips/:pnr" element={guard(<TripDetail />)} />
              <Route path="/account" element={guard(<Account />)} />
              <Route path="/alerts" element={guard(<Alerts />)} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<Forgot />} />
              <Route path="/reset-password" element={<Reset />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      <Footer />
    </div>
  )
}

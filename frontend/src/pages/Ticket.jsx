import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, Download, Printer } from 'lucide-react'
import { api } from '../api.js'
import { useToast } from '../toast.jsx'
import Stepper from '../components/Stepper.jsx'
import BoardingPass from '../components/BoardingPass.jsx'
import { Button, ErrorBox, Loading } from '../components/ui.jsx'

export default function Ticket() {
  const { pnr } = useParams()
  const toast = useToast()
  const [b, setB] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.booking(pnr).then(setB).catch((e) => setError(e.message)) }, [pnr])

  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox></div>
  if (!b) return <Loading label="Issuing your ticket" />

  async function pdf() {
    setBusy(true)
    try { await api.downloadTicket(pnr) } catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="container narrow-ish">
      <div className="no-print"><Stepper current={4} /></div>
      <div className="confirmed no-print">
        <motion.span className="tick" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 16 }}><Check size={30} strokeWidth={3} /></motion.span>
        <h1>You're booked.</h1>
        <p>A confirmation with your e-ticket was sent to <b>{b.contact_email}</b>.</p>
      </div>
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <BoardingPass b={b} />
      </motion.div>
      <div className="row center no-print">
        <Button loading={busy} onClick={pdf}><Download size={17} /> Download PDF ticket</Button>
        <button className="btn btn-ghost" onClick={() => window.print()}><Printer size={17} /> Print</button>
        <Link to="/trips" className="btn btn-ghost">Go to My trips</Link>
      </div>
      <p className="fine center no-print">Sandbox project: this ticket is a simulation and is not valid for air travel.</p>
    </div>
  )
}

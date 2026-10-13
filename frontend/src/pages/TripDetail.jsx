import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Printer, XCircle } from 'lucide-react'
import { api } from '../api.js'
import { useToast } from '../toast.jsx'
import BoardingPass from '../components/BoardingPass.jsx'
import { Button, ErrorBox, Loading } from '../components/ui.jsx'
import { inr } from '../utils.js'

export default function TripDetail() {
  const { pnr } = useParams()
  const toast = useToast()
  const [b, setB] = useState(null)
  const [error, setError] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.booking(pnr).then(setB).catch((e) => setError(e.message)) }, [pnr])

  if (error) return <div className="container narrow"><ErrorBox>{error}</ErrorBox><Link to="/trips" className="btn btn-ghost">Back to My trips</Link></div>
  if (!b) return <Loading label="Opening your trip" />

  async function cancel() {
    setBusy(true)
    try {
      const nb = await api.cancelBooking(pnr)
      setB(nb); setConfirm(false)
      toast.success(nb.refund_amount ? `Cancelled. ${inr(nb.refund_amount)} will be refunded.` : 'Booking cancelled.')
    } catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  async function pdf() {
    try { await api.downloadTicket(pnr) } catch (e) { toast.error(e.message) }
  }
  const q = b.cancel_quote

  return (
    <div className="container narrow-ish">
      <Link to="/trips" className="back no-print"><ArrowLeft size={16} /> My trips</Link>
      <BoardingPass b={b} />

      {b.status === 'CONFIRMED' && (
        <>
          <div className="row center no-print">
            <Button onClick={pdf}><Download size={17} /> Download PDF ticket</Button>
            <button className="btn btn-ghost" onClick={() => window.print()}><Printer size={17} /> Print</button>
          </div>
          <section className="card cancel-card no-print">
            <h2>Need to cancel?</h2>
            {q?.allowed ? (
              <>
                <p>If you cancel now you get <b>{inr(q.refund)}</b> back ({q.percent}% of {inr(b.total)}). Refunds go to the original payment method in 5–7 working days.</p>
                <p className="fine">{q.policy}</p>
                {!confirm ? (
                  <button className="btn btn-danger" onClick={() => setConfirm(true)}><XCircle size={17} /> Cancel this booking</button>
                ) : (
                  <div className="confirm-box" role="alertdialog">
                    <p><b>Cancel booking {b.pnr}?</b> Your seats will be released and this cannot be undone.</p>
                    <div className="row">
                      <Button variant="danger" loading={busy} onClick={cancel}>Yes, cancel and refund {inr(q.refund)}</Button>
                      <button className="btn btn-ghost" onClick={() => setConfirm(false)}>Keep my booking</button>
                    </div>
                  </div>
                )}
              </>
            ) : <p>{q?.reason || 'This booking can no longer be cancelled online.'}</p>}
          </section>
        </>
      )}
      {b.status === 'CANCELLED' && (
        <section className="card cancel-card"><h2>This booking was cancelled</h2>
          <p>{b.refund_amount ? <>A refund of <b>{inr(b.refund_amount)}</b> ({b.refund_percent}%) was issued to your original payment method.</> : 'No refund applied.'}</p></section>
      )}
    </div>
  )
}

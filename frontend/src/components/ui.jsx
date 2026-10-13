import { Loader2 } from 'lucide-react'

export function Spinner({ size = 18 }) {
  return <Loader2 size={size} className="spin" aria-hidden />
}

export function Loading({ label = 'Loading' }) {
  return (
    <div className="loading-page" role="status">
      <div className="runway"><span /><span /><span /><span /><span /></div>
      <p>{label}…</p>
    </div>
  )
}

export function Button({ loading, children, variant = 'gold', size, className = '', ...rest }) {
  return (
    <button className={`btn btn-${variant} ${size ? 'btn-' + size : ''} ${className}`} disabled={loading || rest.disabled} {...rest}>
      {loading && <Spinner size={16} />}
      {children}
    </button>
  )
}

export function Field({ label, hint, error, children }) {
  return (
    <label className={`field ${error ? 'has-error' : ''}`}>
      <span className="field-label">{label}</span>
      {children}
      {error ? <small className="field-error">{error}</small> : hint ? <small className="field-hint">{hint}</small> : null}
    </label>
  )
}

export function PageHead({ title, sub, children }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      {children}
    </div>
  )
}

export function Empty({ icon, title, text, action }) {
  return (
    <div className="empty">
      {icon}
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  )
}

export function ErrorBox({ children }) {
  return children ? <div className="notice error" role="alert">{children}</div> : null
}

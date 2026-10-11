import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

export function Stat({
  label,
  value,
  hint,
}: {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
}) {
  return (
    <div className="fp-stat">
      <span className="fp-stat__label">{label}</span>
      <span className="fp-stat__value">{value}</span>
      {hint ? <span className="fp-stat__hint">{hint}</span> : null}
    </div>
  )
}

export function KeyValue({ items }: { items: { label: ReactNode; value: ReactNode }[] }) {
  return (
    <dl className="fp-kv">
      {items.map((item, index) => (
        <div key={index} style={{ display: 'contents' }}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function EmptyState({
  icon,
  title,
  message,
  actions,
}: {
  icon?: ReactNode
  title: ReactNode
  message?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="fp-empty">
      <span className="fp-empty__icon" aria-hidden="true">
        {icon ?? <Inbox size={28} />}
      </span>
      <span className="fp-empty__title">{title}</span>
      {message ? <span className="fp-empty__message">{message}</span> : null}
      {actions ? <div className="fp-empty__actions">{actions}</div> : null}
    </div>
  )
}

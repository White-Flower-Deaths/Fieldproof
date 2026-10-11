import type { ReactNode } from 'react'

export function Card({
  raised = false,
  hero = false,
  className,
  children,
}: {
  raised?: boolean
  hero?: boolean
  className?: string
  children: ReactNode
}) {
  const classes = [
    'fp-card',
    raised ? 'fp-card--raised' : '',
    hero ? 'fp-card--hero' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ')
  return <section className={classes}>{children}</section>
}

export function CardHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="fp-card__header">
      <div className="fp-card__titles">
        <div className="fp-card__title">{title}</div>
        {subtitle ? <div className="fp-card__subtitle">{subtitle}</div> : null}
      </div>
      {actions ? <div className="fp-page-header__actions">{actions}</div> : null}
    </header>
  )
}

export function CardBody({
  flush = false,
  children,
}: {
  flush?: boolean
  children: ReactNode
}) {
  return (
    <div className={flush ? 'fp-card__body fp-card__body--flush' : 'fp-card__body'}>
      {children}
    </div>
  )
}

export function CardFooter({ children }: { children: ReactNode }) {
  return <footer className="fp-card__footer">{children}</footer>
}

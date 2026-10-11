import type { ReactNode } from 'react'

export type BadgeTone =
  | 'neutral'
  | 'info'
  | 'success'
  | 'deepgreen'
  | 'warning'
  | 'danger'
  | 'orange'
  | 'navy'

export type BadgeProps = {
  tone?: BadgeTone
  size?: 'sm' | 'lg'
  mono?: boolean
  dot?: boolean
  icon?: ReactNode
  title?: string
  className?: string
  children: ReactNode
}

export function Badge({
  tone = 'neutral',
  size = 'sm',
  mono = false,
  dot = false,
  icon,
  title,
  className,
  children,
}: BadgeProps) {
  const classes = [
    'fp-badge',
    `fp-badge--${tone}`,
    size === 'lg' ? 'fp-badge--lg' : '',
    mono ? 'fp-badge--mono' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span className={classes} title={title}>
      {icon ? (
        <span className="fp-badge__icon" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      {dot ? <span className="fp-badge__dot" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}

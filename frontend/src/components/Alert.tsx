import type { ReactNode } from 'react'
import { CircleAlert, CircleCheck, CircleX, Info, Minus } from 'lucide-react'

export type AlertTone = 'info' | 'success' | 'warning' | 'danger' | 'neutral'

const ICONS: Record<AlertTone, ReactNode> = {
  info: <Info size={18} />,
  success: <CircleCheck size={18} />,
  warning: <CircleAlert size={18} />,
  danger: <CircleX size={18} />,
  neutral: <Minus size={18} />,
}

export type AlertProps = {
  tone?: AlertTone
  title?: ReactNode
  children?: ReactNode
  className?: string
  icon?: ReactNode
}

export function Alert({ tone = 'info', title, children, className, icon }: AlertProps) {
  const classes = ['fp-alert', `fp-alert--${tone}`, className ?? '']
    .filter(Boolean)
    .join(' ')
  return (
    <div className={classes} role={tone === 'danger' ? 'alert' : 'status'}>
      <span className="fp-alert__icon" aria-hidden="true">
        {icon ?? ICONS[tone]}
      </span>
      <div className="fp-alert__content">
        {title ? <span className="fp-alert__title">{title}</span> : null}
        {children ? <div>{children}</div> : null}
      </div>
    </div>
  )
}

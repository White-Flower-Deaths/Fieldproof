import { statusMeta } from '../lib/status'
import { Badge } from './Badge'

/** Result status chip: always icon + text (spec: never colour alone). */
export function StatusPill({
  status,
  size = 'sm',
  mono = false,
}: {
  status: string
  size?: 'sm' | 'lg'
  mono?: boolean
}) {
  const meta = statusMeta(status)
  const Icon = meta.icon
  return (
    <Badge tone={meta.tone} size={size} mono={mono} icon={<Icon size={14} />} title={meta.description}>
      {meta.label}
    </Badge>
  )
}

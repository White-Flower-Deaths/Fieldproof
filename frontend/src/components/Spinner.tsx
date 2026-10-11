export type SpinnerSize = 'sm' | 'lg'

export function Spinner({ size = 'sm', label }: { size?: SpinnerSize; label?: string }) {
  return (
    <span
      className={size === 'lg' ? 'fp-spinner fp-spinner--lg' : 'fp-spinner'}
      role="status"
      aria-label={label ?? 'Loading'}
    />
  )
}

export function Skeleton({
  width,
  height,
  radius,
  className,
}: {
  width?: string | number
  height?: string | number
  radius?: string
  className?: string
}) {
  return (
    <span
      className={['fp-skeleton', className ?? ''].filter(Boolean).join(' ')}
      aria-hidden="true"
      style={{ width, height, borderRadius: radius }}
    />
  )
}

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div
      style={{
        display: 'grid',
        justifyItems: 'center',
        gap: 'var(--sp-3)',
        padding: 'var(--sp-10)',
        color: 'var(--color-text-muted)',
      }}
    >
      <Spinner size="lg" label={label} />
      <span style={{ fontSize: 'var(--fs-sm)' }}>{label}</span>
    </div>
  )
}

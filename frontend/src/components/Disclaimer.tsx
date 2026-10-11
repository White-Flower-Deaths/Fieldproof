import type { ReactNode } from 'react'
import { CONCENTRATION_NOTE, DISCLAIMER } from '../lib/constants'

/**
 * The mandatory disclaimer block. Every screen, export and stored record that
 * shows a field result must render this (hard rule).
 */
export function Disclaimer({
  compact = false,
  showConcentration = true,
  children,
}: {
  compact?: boolean
  showConcentration?: boolean
  children?: ReactNode
}) {
  return (
    <aside
      className={compact ? 'fp-disclaimer fp-disclaimer--compact' : 'fp-disclaimer'}
      aria-label="Presumptive result disclaimer"
    >
      <span className="fp-disclaimer__label">Presumptive field result only</span>
      <span>{DISCLAIMER}</span>
      {showConcentration ? (
        <span className="fp-disclaimer__concentration">{CONCENTRATION_NOTE}</span>
      ) : null}
      {children}
    </aside>
  )
}

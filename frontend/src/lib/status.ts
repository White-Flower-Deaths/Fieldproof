import type { LucideIcon } from 'lucide-react'
import {
  BadgeCheck,
  CircleCheck,
  CircleMinus,
  Scale,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react'
import type { BadgeTone } from '../components/Badge'
import type { ResultStatus } from './constants'

export type StatusMeta = {
  label: string
  tone: BadgeTone
  icon: LucideIcon
  order: number
  description: string
}

/** Display metadata for every status in the result ladder.
 *  Chips always render icon + text (never colour alone). */
export const STATUS_META: Record<ResultStatus, StatusMeta> = {
  NO_MATCH: {
    label: 'No match',
    tone: 'neutral',
    icon: CircleMinus,
    order: 0,
    description: 'No candidate substance is consistent with the observed results.',
  },
  WEAK_PRESUMPTIVE: {
    label: 'Weak presumptive',
    tone: 'warning',
    icon: TriangleAlert,
    order: 1,
    description: 'Limited evidence - treat with extra caution, repeat or extend testing.',
  },
  PRESUMPTIVE: {
    label: 'Presumptive',
    tone: 'success',
    icon: CircleCheck,
    order: 2,
    description: 'One or more presumptive tests support a candidate substance.',
  },
  STRONG_PRESUMPTIVE: {
    label: 'Strong presumptive',
    tone: 'deepgreen',
    icon: BadgeCheck,
    order: 3,
    description: 'Multiple independent presumptive tests agree. Still NOT confirmed.',
  },
  INCONCLUSIVE: {
    label: 'Inconclusive',
    tone: 'orange',
    icon: Scale,
    order: 4,
    description: 'Results conflict or are unusable - refer to the laboratory.',
  },
  CONFIRMED_BY_LAB: {
    label: 'Confirmed by lab',
    tone: 'navy',
    icon: ShieldCheck,
    order: 5,
    description: 'Set only from a LAB_CONFIRMATORY result entered by a LAB user.',
  },
}

export function statusMeta(status: string): StatusMeta {
  return (
    STATUS_META[status as ResultStatus] ?? {
      label: status,
      tone: 'neutral',
      icon: CircleMinus,
      order: -1,
      description: 'Unknown status.',
    }
  )
}

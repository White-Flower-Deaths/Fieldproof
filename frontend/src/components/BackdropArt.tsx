import type { ReactNode } from 'react'

/**
 * Decorative gutter backdrop — lab/field line-art figures pinned in the wide
 * left/right page margins. Purely decorative (aria-hidden, pointer-events:
 * none), hidden below 1200 px where the gutters disappear, and clipped to the
 * viewport so it can never cause horizontal overflow.
 */

type FigDef = {
  id: string
  art: ReactNode
  tone: 'teal' | 'sky' | 'violet'
  rot: number
  size: number
}

function SyringeArt() {
  return (
    <svg viewBox="0 0 64 64" focusable="false">
      <g transform="rotate(-45 32 32)">
        <rect x="20" y="27" width="24" height="10" rx="1.5" />
        <path d="M44 32 h13" />
        <path d="M44 29.5 v5" />
        <path d="M20 32 h-9" />
        <rect x="6.5" y="27.5" width="4" height="9" rx="1" />
        <path d="M25 27 v3.5 M29 27 v3.5 M33 27 v3.5 M37 27 v3.5 M41 27 v3.5" />
      </g>
    </svg>
  )
}

function ReagentBottleArt() {
  return (
    <svg viewBox="0 0 64 64" focusable="false">
      <rect x="25" y="6" width="14" height="7" rx="1.5" />
      <path d="M28.5 13 v5 c0 4 -8.5 7 -8.5 14 v13 a4 4 0 0 0 4 4 h16 a4 4 0 0 0 4 -4 v-13 c0 -7 -8.5 -10 -8.5 -14 v-5" />
      <rect x="21" y="35" width="22" height="11" rx="1.5" />
      <path d="M25 40.5 h14" />
    </svg>
  )
}

function CannabisLeafArt() {
  const leaflet = (
    <path d="M0 -7 C4 -20 4 -36 0 -48 C-4 -36 -4 -20 0 -7 Z" />
  )
  const midrib = <path d="M0 -11 v-30" />
  return (
    <svg viewBox="0 0 64 64" focusable="false">
      <g transform="translate(32 55)">
        <path d="M0 0 v7" />
        <g transform="rotate(0)">
          {leaflet}
          {midrib}
        </g>
        <g transform="rotate(-30) scale(0.85)">
          {leaflet}
          {midrib}
        </g>
        <g transform="rotate(30) scale(0.85)">
          {leaflet}
          {midrib}
        </g>
        <g transform="rotate(-58) scale(0.62)">
          {leaflet}
          {midrib}
        </g>
        <g transform="rotate(58) scale(0.62)">
          {leaflet}
          {midrib}
        </g>
      </g>
    </svg>
  )
}

function StashPouchArt() {
  return (
    <svg viewBox="0 0 64 64" focusable="false">
      <path d="M17 21 h30 v27 a5 5 0 0 1 -5 5 h-20 a5 5 0 0 1 -5 -5 z" />
      <path d="M17 27 h30" />
      <path d="M20 24 h24" />
      <path d="M23 21 v-3 c0 -3 3 -5 6 -5" />
      <path d="M41 21 v-3 c0 -3 -3 -5 -6 -5" />
      <path d="M23 39 c3.5 -4 6.5 4 10 0 s6.5 -4 9 0" />
    </svg>
  )
}

function TestTubeArt() {
  return (
    <svg viewBox="0 0 64 64" focusable="false">
      <rect x="24" y="4" width="16" height="6" rx="2" />
      <path d="M27 10 v36 a5 5 0 0 0 10 0 v-36" />
      <path d="M27 32 c3 2.5 7 2.5 10 0 v14 a5 5 0 0 1 -10 0 z" />
      <path d="M30.5 15 v4 M30.5 22 v4 M30.5 29 v4" />
    </svg>
  )
}

function TabletsArt() {
  return (
    <svg viewBox="0 0 64 64" focusable="false">
      <circle cx="22" cy="42" r="11" />
      <path d="M14.5 42 h15" />
      <g transform="rotate(24 41 21)">
        <rect x="29" y="14" width="24" height="14" rx="7" />
        <path d="M41 14 v14" />
      </g>
    </svg>
  )
}

const LEFT_FIGS: FigDef[] = [
  { id: 'l-syringe', art: <SyringeArt />, tone: 'teal', rot: -12, size: 104 },
  { id: 'l-leaf', art: <CannabisLeafArt />, tone: 'violet', rot: 6, size: 96 },
  { id: 'l-bottle', art: <ReagentBottleArt />, tone: 'sky', rot: -6, size: 100 },
  { id: 'l-pouch', art: <StashPouchArt />, tone: 'teal', rot: 9, size: 92 },
  { id: 'l-tablets', art: <TabletsArt />, tone: 'sky', rot: -5, size: 96 },
]

const RIGHT_FIGS: FigDef[] = [
  { id: 'r-tube', art: <TestTubeArt />, tone: 'sky', rot: 8, size: 96 },
  { id: 'r-syringe', art: <SyringeArt />, tone: 'violet', rot: 14, size: 100 },
  { id: 'r-leaf', art: <CannabisLeafArt />, tone: 'teal', rot: -7, size: 104 },
  { id: 'r-bottle', art: <ReagentBottleArt />, tone: 'violet', rot: 5, size: 92 },
  { id: 'r-pouch', art: <StashPouchArt />, tone: 'sky', rot: -10, size: 96 },
]

function Side({ side, figs }: { side: 'left' | 'right'; figs: FigDef[] }) {
  return (
    <div className={`fp-backdrop__side fp-backdrop__side--${side}`}>
      {figs.map((fig) => (
        <span
          key={fig.id}
          className={`fp-backdrop__fig fp-backdrop__fig--${fig.tone}`}
          style={{ rotate: `${fig.rot}deg`, width: fig.size, height: fig.size }}
        >
          {fig.art}
        </span>
      ))}
    </div>
  )
}

export function BackdropArt() {
  return (
    <div className="fp-backdrop" aria-hidden="true">
      <Side side="left" figs={LEFT_FIGS} />
      <Side side="right" figs={RIGHT_FIGS} />
    </div>
  )
}

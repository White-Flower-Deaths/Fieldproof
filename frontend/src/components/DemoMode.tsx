import { useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'
import {
  BadgeCheck,
  ChartNoAxesColumn,
  Plus,
  Presentation,
  ScrollText,
  ShieldCheck,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { getStoredDemoMode, storeDemoMode } from '../lib/demoMode'

type Step = {
  title: string
  body: string
  action: string
  to: string
  Icon: LucideIcon
}

/**
 * Demo-mode ribbon (always visible, toggleable) plus a short, dismissible,
 * keyboard-accessible walkthrough. Non-blocking: the tour card is fixed in a
 * corner with no scrim, so the app stays fully interactive while it is open.
 */
export function DemoMode() {
  const navigate = useNavigate()
  const [demoMode, setDemoMode] = useState<boolean>(() => getStoredDemoMode())
  const [tourOpen, setTourOpen] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [exampleLink, setExampleLink] = useState<string | null>(null)
  const tourButtonRef = useRef<HTMLButtonElement>(null)
  const switchRef = useRef<HTMLButtonElement>(null)
  const cardRef = useRef<HTMLDivElement>(null)
  const lookupStarted = useRef(false)

  const openTour = () => {
    setStepIndex(0)
    setTourOpen(true)
    if (!lookupStarted.current) {
      lookupStarted.current = true
      void api.listSamples(50).then(
        (samples) => {
          const signed = samples.find((s) => s.status === 'SIGNED')
          setExampleLink(signed ? `/samples/${signed.id}/analysis` : '')
        },
        () => setExampleLink(''),
      )
    }
    window.requestAnimationFrame(() => cardRef.current?.focus())
  }

  const closeTour = (restoreFocus = true) => {
    setTourOpen(false)
    if (restoreFocus) {
      const trigger = tourButtonRef.current ?? switchRef.current
      trigger?.focus()
    }
  }

  const toggleDemo = () => {
    const next = !demoMode
    storeDemoMode(next)
    setDemoMode(next)
    if (!next) setTourOpen(false)
  }

  const hasExample = Boolean(exampleLink)
  const exampleTarget = exampleLink || '/new-test'

  const steps: Step[] = [
    {
      title: 'New test',
      body: 'Five guided steps: sample details, kit, result, review, sign. The draft autosaves on this device.',
      action: 'Open New test',
      to: '/new-test',
      Icon: Plus,
    },
    {
      title: 'Result',
      body: hasExample
        ? 'Explainable analysis: status chip, confidence gauge, evidence with supports or contradicts, and a “why this result” panel.'
        : 'Each test ends on an explainable result: status, confidence and the evidence behind it.',
      action: hasExample ? 'Open a demo result' : 'Start a test',
      to: exampleTarget,
      Icon: ChartNoAxesColumn,
    },
    {
      title: 'Signed record',
      body: 'Signing writes a SHA-256 hash chain plus an ECDSA P-256 signature you can copy or download as JSON.',
      action: hasExample ? 'See a signed record' : 'Start a test',
      to: exampleTarget,
      Icon: BadgeCheck,
    },
    {
      title: 'Log',
      body: 'Every signed record: search, status and date filters, CSV export and a verification checklist per record.',
      action: 'Open Log',
      to: '/log',
      Icon: ScrollText,
    },
    {
      title: 'Verify',
      body: 'Load any record bundle to re-check it. Press “Try a tampered example” to watch verification fail.',
      action: 'Open Verify',
      to: '/verify',
      Icon: ShieldCheck,
    },
  ]

  const step = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1

  const next = () => {
    if (isLast) closeTour()
    else setStepIndex(stepIndex + 1)
  }

  const back = () => setStepIndex(Math.max(0, stepIndex - 1))

  const onCardKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation()
      closeTour()
    }
  }

  return (
    <>
      <aside
        className={`fp-demobar fp-demobar--${demoMode ? 'on' : 'off'}`}
        aria-label="Demo mode"
      >
        <span className="fp-demobar__chip">
          <Presentation size={14} aria-hidden="true" />
          {demoMode ? 'Demo mode' : 'Demo off'}
        </span>
        {demoMode ? null : (
          <span className="fp-demobar__text">Demo labelling hidden on this device.</span>
        )}
        {demoMode ? (
          <button
            type="button"
            ref={tourButtonRef}
            className="fp-btn fp-btn--sm fp-btn--secondary"
            onClick={openTour}
          >
            <Presentation size={16} aria-hidden="true" />
            Take the tour
          </button>
        ) : null}
        <button
          type="button"
          ref={switchRef}
          role="switch"
          aria-checked={demoMode}
          className="fp-demobar__switch"
          onClick={toggleDemo}
        >
          <span className="fp-switch__track" aria-hidden="true">
            <span className="fp-switch__thumb" />
          </span>
          <span>{demoMode ? 'On' : 'Off'}</span>
        </button>
      </aside>
      {tourOpen ? (
        <div
          ref={cardRef}
          className="fp-tour"
          role="dialog"
          aria-label="Demo tour"
          tabIndex={-1}
          onKeyDown={onCardKeyDown}
        >
          <div className="fp-tour__head">
            <span className="fp-tour__counter">
              Step {stepIndex + 1} of {steps.length}
            </span>
            <button
              type="button"
              className="fp-icon-btn fp-tour__close"
              onClick={() => closeTour()}
              aria-label="Close tour"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
          <div aria-live="polite">
            <p className="fp-tour__title">
              <step.Icon size={18} aria-hidden="true" />
              {step.title}
            </p>
            <p className="fp-tour__body">{step.body}</p>
          </div>
          <button
            type="button"
            className="fp-btn fp-btn--sm fp-btn--secondary fp-tour__action"
            onClick={() => navigate(step.to)}
          >
            <step.Icon size={16} aria-hidden="true" />
            {step.action}
          </button>
          <div className="fp-tour__footer">
            <button
              type="button"
              className="fp-btn fp-btn--sm fp-btn--secondary"
              onClick={back}
              disabled={stepIndex === 0}
            >
              Back
            </button>
            <button
              type="button"
              className="fp-btn fp-btn--sm fp-btn--ghost"
              onClick={() => closeTour()}
            >
              Skip
            </button>
            <button
              type="button"
              className="fp-btn fp-btn--sm fp-btn--primary fp-tour__next"
              onClick={next}
            >
              {isLast ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>
      ) : null}
    </>
  )
}

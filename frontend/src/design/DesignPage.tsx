import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Checkbox,
  DataTable,
  Dialog,
  Disclaimer,
  EmptyState,
  KeyValue,
  Logo,
  PageHeader,
  SegmentedControl,
  SelectField,
  Skeleton,
  Spinner,
  Stat,
  StatusPill,
  TextAreaField,
  TextField,
} from '../components'
import { RESULT_STATUSES } from '../lib/constants'
import { applyTheme, getStoredTheme } from '../lib/theme'
import type { Theme } from '../lib/theme'
import './DesignPage.css'

/* ------------------------------------------------------------------ data */

const COLOR_GROUPS: { title: string; tokens: string[] }[] = [
  {
    title: 'Surfaces',
    tokens: ['--color-bg', '--color-surface', '--color-surface-2', '--color-surface-inverse'],
  },
  {
    title: 'Text',
    tokens: ['--color-text', '--color-text-muted', '--color-text-inverse', '--color-text-on-brand'],
  },
  {
    title: 'Brand & borders',
    tokens: [
      '--color-navy',
      '--color-primary',
      '--color-primary-hover',
      '--color-primary-soft',
      '--color-border',
      '--color-border-strong',
    ],
  },
  {
    title: 'Semantic',
    tokens: [
      '--color-success',
      '--color-deep-green',
      '--color-warning',
      '--color-danger',
      '--color-info',
      '--color-orange',
    ],
  },
  {
    title: 'Semantic (soft)',
    tokens: [
      '--color-success-soft',
      '--color-deep-green-soft',
      '--color-warning-soft',
      '--color-danger-soft',
      '--color-info-soft',
      '--color-orange-soft',
    ],
  },
]

const TYPE_SCALE: { token: string; use: string; sample: string }[] = [
  { token: '--fs-2xl', use: 'Hero / key figure', sample: '93.3%' },
  { token: '--fs-xl', use: 'Page title', sample: 'Analysis result' },
  { token: '--fs-lg', use: 'Section title', sample: 'Presumptive outcome' },
  { token: '--fs-md', use: 'Card title', sample: 'Marquis reagent' },
  { token: '--fs-base', use: 'Body text', sample: 'Purple turning black after 60 s.' },
  { token: '--fs-sm', use: 'Labels, table cells', sample: 'Kit · MARQUIS · lot 4471' },
  { token: '--fs-xs', use: 'Meta, captions', sample: 'Record a1b2c3… signed 14:02 UTC' },
]

const SPACING: { token: string; value: string }[] = [
  { token: '--sp-1', value: '0.5rem' },
  { token: '--sp-2', value: '1rem' },
  { token: '--sp-3', value: '1.5rem' },
  { token: '--sp-4', value: '2rem' },
  { token: '--sp-6', value: '3rem' },
  { token: '--sp-8', value: '4rem' },
  { token: '--sp-12', value: '6rem' },
]

const DEMO_ROWS = [
  { id: 'S-1041', status: 'STRONG_PRESUMPTIVE', kit: 'MARQUIS', time: '14:02' },
  { id: 'S-1042', status: 'INCONCLUSIVE', kit: 'MECKE', time: '14:18' },
  { id: 'S-1043', status: 'CONFIRMED_BY_LAB', kit: 'GC-MS', time: '09:41' },
]

/* -------------------------------------------------------------- sections */

function Section({
  id,
  title,
  kicker,
  children,
}: {
  id: string
  title: string
  kicker?: string
  children: ReactNode
}) {
  return (
    <section className="dp-section" id={id}>
      <div className="dp-section__head">
        <h2>{title}</h2>
        {kicker ? <p className="dp-kicker">{kicker}</p> : null}
      </div>
      {children}
    </section>
  )
}

function Example({
  label,
  notes,
  children,
}: {
  label: string
  notes?: string
  children: ReactNode
}) {
  return (
    <div className="dp-example">
      <span className="dp-example__label">{label}</span>
      <div className="dp-example__row">{children}</div>
      {notes ? <p className="dp-example__notes">{notes}</p> : null}
    </div>
  )
}

function Swatch({ token }: { token: string }) {
  // Safe to read during render (client-only app); parent re-renders on theme
  // change, which re-reads the resolved value for the active theme.
  const value =
    getComputedStyle(document.documentElement).getPropertyValue(token).trim() || '—'

  return (
    <div className="dp-swatch">
      <div className="dp-swatch__chip" style={{ background: `var(${token})` }} />
      <code>{token}</code>
      <span className="dp-swatch__value">{value}</span>
    </div>
  )
}

/* ------------------------------------------------------------- the page */

export default function DesignPage() {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme())
  const [dialogOpen, setDialogOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')
  const [confirmed, setConfirmed] = useState(true)

  const onThemeChange = (next: Theme) => {
    applyTheme(next)
    setTheme(next)
  }

  const startLoading = () => {
    setLoading(true)
    window.setTimeout(() => setLoading(false), 1600)
  }

  return (
    <div className="dp-page">
      <header className="dp-topbar">
        <div className="dp-topbar__inner">
          <Logo tagline="design system v1" />
          <nav className="dp-nav" aria-label="Sections">
            <a href="#foundations">Foundations</a>
            <a href="#components">Components</a>
            <a href="#patterns">Patterns</a>
          </nav>
          <SegmentedControl<Theme>
            ariaLabel="Color theme"
            options={[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
            ]}
            value={theme}
            onChange={onThemeChange}
          />
        </div>
      </header>

      <main className="fp-container dp-main">
        <PageHeader
          title="FieldProof design system"
          subtitle="Mobile-first tokens and components for field officers: high contrast, large
          tap targets, and every result wrapped in the mandatory presumptive-result
          disclaimer. Use these primitives for all screens from step 6 onwards."
        />

        {/* ------------------------------------------------- foundations */}
        <Section
          id="foundations"
          title="Foundations"
          kicker="Design tokens live in src/styles/tokens.css. Never hard-code colours or sizes."
        >
          <div className="dp-swatches">
            {COLOR_GROUPS.flatMap((group) =>
              group.tokens.map((token) => <Swatch key={token} token={token} />),
            )}
          </div>

          <div className="dp-example">
            <span className="dp-example__label">Type scale</span>
            {TYPE_SCALE.map((row) => (
              <div className="dp-type-row" key={row.token}>
                <code>{row.token}</code>
                <span style={{ fontSize: `var(${row.token})` }}>{row.sample}</span>
              </div>
            ))}
            <p className="dp-example__notes">{`Use: ${TYPE_SCALE.map((r) => `${r.token} → ${r.use}`).join(' · ')}`}</p>
          </div>

          <div className="dp-example">
            <span className="dp-example__label">Spacing scale (8 px grid)</span>
            {SPACING.map((row) => (
              <div className="dp-space-row" key={row.token}>
                <code>
                  {row.token} · {row.value}
                </code>
                <span className="dp-space-bar" style={{ width: `var(${row.token})` }} />
              </div>
            ))}
          </div>

          <div className="dp-example">
            <span className="dp-example__label">Radii & elevation</span>
            <div className="dp-example__row">
              <div className="dp-box" style={{ borderRadius: 'var(--radius-sm)' }}>
                radius-sm
              </div>
              <div className="dp-box" style={{ borderRadius: 'var(--radius-md)' }}>
                radius-md
              </div>
              <div className="dp-box" style={{ borderRadius: 'var(--radius-lg)' }}>
                radius-lg
              </div>
              <div className="dp-box" style={{ boxShadow: 'var(--shadow-md)' }}>
                shadow-md
              </div>
              <div className="dp-box" style={{ boxShadow: 'var(--shadow-lg)' }}>
                shadow-lg
              </div>
            </div>
          </div>
        </Section>

        {/* -------------------------------------------------- components */}
        <Section
          id="components"
          title="Components"
          kicker="Import from src/components — one barrel, consistent props, no one-off CSS."
        >
          <div className="dp-grid-2">
            <Example
              label="Button · variants & sizes"
              notes="primary = one per screen; danger only for destructive/abort actions; loading disables and swaps the icon for a spinner."
            >
              <Button>Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button size="sm">Small</Button>
              <Button size="lg">Large</Button>
              <Button disabled>Disabled</Button>
              <Button loading={loading} onClick={startLoading}>
                {loading ? 'Working…' : 'Click to load'}
              </Button>
            </Example>

            <Example
              label="Badge · tones"
              notes="Tones: neutral, info, success, deepgreen, warning, danger, orange, navy. No purple, no colour-only meaning."
            >
              <Badge tone="neutral">neutral</Badge>
              <Badge tone="info">info</Badge>
              <Badge tone="success">success · green</Badge>
              <Badge tone="deepgreen">deepgreen</Badge>
              <Badge tone="warning">warning · amber</Badge>
              <Badge tone="danger">danger · red</Badge>
              <Badge tone="orange">orange</Badge>
              <Badge tone="navy">navy</Badge>
              <Badge tone="info" mono dot>
                monospace + dot
              </Badge>
            </Example>

            <Example
              label="StatusPill · result ladder"
              notes="Always icon + text (never colour alone); tooltip shows the meaning. CONFIRMED_BY_LAB is navy with a shield-check and may only appear from a real LAB_CONFIRMATORY result."
            >
              {RESULT_STATUSES.map((status) => (
                <span key={status} className="dp-stack-inline">
                  <StatusPill status={status} />
                </span>
              ))}
            </Example>

            <Example label="SegmentedControl & Stat">
              <SegmentedControl
                ariaLabel="Demo units"
                options={[
                  { value: 'sec', label: 'Seconds' },
                  { value: 'ms', label: 'Milliseconds' },
                ]}
                value="sec"
                onChange={() => undefined}
              />
              <Stat label="Top candidate" value="93.3%" hint="demo data · MDMA" />
              <Stat label="ΔE to reference" value="0.41" hint="limit 15.0" />
            </Example>
          </div>

          <Card raised>
            <CardHeader
              title="Card"
              subtitle="Header, body (optionally flush), footer — the shell for every screen."
              actions={<Badge tone="info">demo</Badge>}
            />
            <CardBody>
              <p>
                Cards hold forms, results and detail views. Footers align actions to the
                end on wide screens and wrap on phones.
              </p>
            </CardBody>
            <CardFooter>
              <Button variant="secondary" size="sm">
                Cancel
              </Button>
              <Button size="sm">Continue</Button>
            </CardFooter>
          </Card>

          <div className="dp-grid-2">
            <Example
              label="Forms"
              notes="48 px fields, visible labels, hint or error below (never placeholder-only), error uses aria-invalid + role=alert."
            >
              <div className="dp-form-demo">
                <TextField
                  label="Sample ID"
                  placeholder="S-1041"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  error={name === '' ? 'Sample ID is required.' : undefined}
                  required
                />
                <SelectField label="Kit" defaultValue="MARQUIS">
                  <option value="MARQUIS">Marquis</option>
                  <option value="MECKE">Mecke</option>
                  <option value="MANDELIN">Mandelin</option>
                </SelectField>
                <TextAreaField label="Observations" placeholder="Colour change, timing, notes…" />
                <Checkbox
                  label="Photo attached"
                  hint="Required for COLOUR_REAGENT kits before finalize."
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />
              </div>
            </Example>

            <Example
              label="Feedback · Alert"
              notes="info / success / warning / danger / neutral. danger uses role=alert."
            >
              <div className="dp-form-demo">
                <Alert tone="info" title="Heads up">
                  The reaction needs 60 s before you read the colour.
                </Alert>
                <Alert tone="success" title="Saved">
                  Sample S-1041 stored locally — will sync when online.
                </Alert>
                <Alert tone="warning" title="Weak signal">
                  Only one informative test so far — status is capped at weak presumptive.
                </Alert>
                <Alert tone="danger" title="Verification failed">
                  The record hash does not match its canonical JSON.
                </Alert>
                <Alert tone="neutral">Neutral notices: tips, metadata, hints.</Alert>
              </div>
            </Example>

            <Example
              label="Data table"
              notes="Responsive: wraps in a horizontal scroller; numeric columns right-align with tabular figures."
            >
              <DataTable
                caption="Demo records"
                rows={DEMO_ROWS}
                getRowKey={(row) => row.id}
                columns={[
                  { key: 'id', header: 'Sample' },
                  {
                    key: 'status',
                    header: 'Status',
                    render: (row) => <StatusPill status={row.status} />,
                  },
                  { key: 'kit', header: 'Kit' },
                  { key: 'time', header: 'Time', numeric: true },
                ]}
              />
            </Example>

            <Example
              label="Loading & empty states"
              notes="Skeletons for content that will arrive; LoadingBlock for full-page waits; EmptyState always offers the next action."
            >
              <div className="dp-form-demo">
                <div style={{ display: 'grid', gap: 'var(--sp-2)' }}>
                  <Skeleton width="60%" />
                  <Skeleton width="90%" />
                  <Skeleton width="40%" height="2rem" />
                </div>
                <div className="dp-example__row">
                  <Spinner />
                  <Spinner size="lg" />
                </div>
                <EmptyState
                  title="No records yet"
                  message="Finalize a test to create the first signed record."
                  actions={<Button size="sm">New sample</Button>}
                />
              </div>
            </Example>

            <Example
              label="Dialog & KeyValue"
              notes="Esc or backdrop click closes; focus is managed by role=dialog + aria-modal."
            >
              <Button variant="secondary" onClick={() => setDialogOpen(true)}>
                Open dialog
              </Button>
              <Dialog
                open={dialogOpen}
                onClose={() => setDialogOpen(false)}
                title="Finalize test?"
                footer={
                  <>
                    <Button variant="secondary" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => setDialogOpen(false)}>Sign record</Button>
                  </>
                }
              >
                <p>
                  This creates an append-only, hash-chained record. It cannot be edited
                  afterwards — corrections must be new linked records.
                </p>
              </Dialog>
              <KeyValue
                items={[
                  { label: 'Record', value: 'a1b2c3d4e5f6…' },
                  { label: 'Status', value: <StatusPill status="PRESUMPTIVE" /> },
                  { label: 'Signature', value: 'ECDSA P-256 · valid' },
                ]}
              />
            </Example>

            <Example label="Brand · Logo">
              <Logo />
              <Logo tagline="verified field records" />
            </Example>
          </div>
        </Section>

        {/* --------------------------------------------------- patterns */}
        <Section
          id="patterns"
          title="Patterns & hard rules"
          kicker="Non-negotiable product rules — violations are bugs, not style choices."
        >
          <div className="dp-grid-2">
            <div className="dp-example">
              <span className="dp-example__label">Every result screen ends with this</span>
              <Disclaimer />
              <p className="dp-example__notes">
                The disclaimer and the concentration line are rendered from
                <code> src/lib/constants.ts</code>, which mirrors
                <code> backend/app/enums.py</code> byte for byte.
              </p>
            </div>

            <div className="dp-example">
              <span className="dp-example__label">Compact variant (tables, exports)</span>
              <Disclaimer compact />
            </div>

            <div className="dp-example">
              <span className="dp-example__label">Do</span>
              <ul className="dp-checklist">
                <li>Show StatusPill + explanation next to every result.</li>
                <li>Use the exact concentration string — never a number.</li>
                <li>Label reference data — per-row published citations, not placeholders.</li>
                <li>Keep tap targets ≥ 48 px; primary actions full-width on phones.</li>
                <li>Errors: what failed + what to do next.</li>
              </ul>
            </div>

            <div className="dp-example">
              <span className="dp-example__label">Don't</span>
              <ul className="dp-checklist dp-dont">
                <li>
                  Never write “confirmed” unless status is <code>CONFIRMED_BY_LAB</code>.
                </li>
                <li>Never show a concentration/purity from colour tests.</li>
                <li>Never hard-code colours — add a token instead.</li>
                <li>Never hide the disclaimer behind a link or tooltip.</li>
                <li>Never rely on colour alone: pair tone with text/icon.</li>
              </ul>
            </div>
          </div>

          <Alert tone="info" title="Accessibility baseline">
            Keyboard-reachable controls, visible <code>:focus-visible</code> ring, labelled
            inputs, <code>role=alert</code> for errors, and AA contrast in both themes.
          </Alert>
        </Section>
      </main>

      <footer className="dp-footer">
        <div className="fp-container">
          FieldProof design system · step 6 of 9 ·{' '}
          <a href="http://127.0.0.1:8000/docs">API docs</a>
        </div>
      </footer>
    </div>
  )
}

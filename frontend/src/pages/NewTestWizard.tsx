import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  Camera,
  Check,
  Eye,
  FileSignature,
  Flame,
  MapPin,
  Plus,
  RotateCcw,
  ShieldCheck,
  Timer,
  TriangleAlert,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Checkbox,
  Disclaimer,
  KeyValue,
  LoadingBlock,
  PageHeader,
  SegmentedControl,
  SelectField,
  SignedRecordCard,
  StatusPill,
  TextAreaField,
  TextField,
} from '../components'
import { api, ApiError } from '../lib/api'
import type { Analysis, Kit, Meta, Sample, TestCreateOut } from '../lib/api'
import CaptureFlow from './CaptureFlow'
import './pages.css'

const DRAFT_KEY = 'fieldproof.draft.newtest.v1'

const STEPS = ['Sample', 'Kit', 'Result', 'Review', 'Sign'] as const

/** Seconds offered for the reaction-time reading (8 px-friendly list). */
const TIME_OPTIONS = [15, 30, 45, 60, 90, 120, 180, 300, 600, 900, 1800]

type SignedRecord = {
  id: string
  hash: string
  status: string
  signature: string | null
  server_timestamp: string | null
  public_key_id?: string | null
}

type GpsFix = { lat: number; lon: number; acc: number | null }

type GpsState = 'idle' | 'pending' | 'denied' | 'unavailable'

type Draft = {
  step: number
  appearance: string
  colour: string
  weight: string
  notes: string
  sampleId: string | null
  sampleCode: string | null
  kitCode: string | null
  outcomeCode: string | null
  timeSeconds: number
  kitBatch: string
  testDone: boolean
  acknowledged: boolean
  analysis: Analysis | null
  record: SignedRecord | null
  mode: 'manual' | 'camera'
  gps: GpsFix | null
  gpsState: GpsState
}

const EMPTY_DRAFT: Draft = {
  step: 0,
  appearance: 'POWDER',
  colour: '',
  weight: '',
  notes: '',
  sampleId: null,
  sampleCode: null,
  kitCode: null,
  outcomeCode: null,
  timeSeconds: 60,
  kitBatch: '',
  testDone: false,
  acknowledged: false,
  analysis: null,
  record: null,
  mode: 'manual',
  gps: null,
  gpsState: 'pending',
}

function loadDraft(): Draft {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return { ...EMPTY_DRAFT }
    const parsed = JSON.parse(raw) as Partial<Draft>
    return { ...EMPTY_DRAFT, ...parsed, record: null }
  } catch {
    return { ...EMPTY_DRAFT }
  }
}

function clearStoredDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY)
  } catch {
    /* storage unavailable */
  }
}

function formatTime(seconds: number): string {
  if (seconds % 60 === 0 && seconds >= 60) {
    const min = seconds / 60
    // Non-breaking spaces keep "60 s (1 min)" from splitting mid-parenthesis.
    return `${seconds}\u00A0s (${min}\u00A0min)`
  }
  return `${seconds}\u00A0s`
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return 'Something went wrong.'
}

export default function NewTestWizard() {
  const navigate = useNavigate()
  const [draft, setDraft] = useState<Draft>(() => loadDraft())
  const [meta, setMeta] = useState<Meta | null>(null)
  const [kits, setKits] = useState<Kit[] | null>(null)
  const [refError, setRefError] = useState<string | null>(null)
  const [refLoading, setRefLoading] = useState(true)
  const [stepError, setStepError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [savedAt, setSavedAt] = useState<number | null>(null)

  const step = Math.min(Math.max(draft.step, 0), STEPS.length - 1)
  // Sample is locked once ANY test exists — including while entering another
  // one (testDone is reset per test, the analysis count is not).
  const hasRecordedTests =
    draft.testDone || (draft.analysis?.counts.tests_entered ?? 0) > 0

  const loadReference = useCallback(
    () =>
      Promise.all([api.meta(), api.kits()])
        .then(([metaRes, kitRes]) => {
          setMeta(metaRes)
          setKits(kitRes)
          setRefError(null)
        })
        .catch((err: unknown) => setRefError(errorMessage(err)))
        .finally(() => setRefLoading(false)),
    [],
  )

  const retryReference = () => {
    setRefLoading(true)
    setRefError(null)
    void loadReference()
  }

  useEffect(() => {
    void loadReference()
  }, [loadReference])

  // Auto-save the draft locally (debounced); never persist after signing.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        if (draft.record) {
          clearStoredDraft()
        } else {
          localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
        }
        setSavedAt(Date.now())
      } catch {
        /* storage unavailable */
      }
    }, 300)
    return () => window.clearTimeout(timer)
  }, [draft])

  const kit = useMemo(
    () => (kits ? (kits.find((k) => k.code === draft.kitCode) ?? null) : null),
    [kits, draft.kitCode],
  )

  // ---------------------------------------------------------------- gps
  // Browser geolocation (with accuracy) for the record. One automatic
  // request when the wizard opens, and a bounded retry when Continue is
  // pressed before a fix arrives. Denial / timeout is handled gracefully
  // and shown on the sample step and on the signed record screen.
  const geoRequestedRef = useRef(false)

  const requestGps = useCallback(
    (): Promise<{ gps: GpsFix | null; denied: boolean }> =>
      new Promise((resolve) => {
        if (typeof navigator === 'undefined' || !navigator.geolocation) {
          resolve({ gps: null, denied: false })
          return
        }
        let settled = false
        const finish = (result: { gps: GpsFix | null; denied: boolean }) => {
          if (!settled) {
            settled = true
            resolve(result)
          }
        }
        // Failsafe: never hang on a permission prompt (9 s worst case).
        const failsafe = window.setTimeout(() => finish({ gps: null, denied: false }), 9000)
        navigator.geolocation.getCurrentPosition(
          (position) => {
            window.clearTimeout(failsafe)
            finish({
              gps: {
                lat: position.coords.latitude,
                lon: position.coords.longitude,
                acc:
                  typeof position.coords.accuracy === 'number'
                    ? position.coords.accuracy
                    : null,
              },
              denied: false,
            })
          },
          (error) => {
            window.clearTimeout(failsafe)
            finish({
              gps: null,
              denied: error.code === error.PERMISSION_DENIED,
            })
          },
          { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 },
        )
      }),
    [],
  )

  /** Request (or wait for) a fix and store the outcome in the draft. */
  const applyGps = useCallback(async (): Promise<GpsFix | null> => {
    setDraft((d) => (d.gps ? d : { ...d, gpsState: 'pending' }))
    const result = await requestGps()
    setDraft((d) => {
      if (d.gps) return d
      if (result.gps) return { ...d, gps: result.gps, gpsState: 'idle' }
      if (d.gpsState !== 'pending') return d
      return { ...d, gpsState: result.denied ? 'denied' : 'unavailable' }
    })
    return result.gps
  }, [requestGps])

  const retryGps = () => {
    geoRequestedRef.current = false
    void applyGps()
  }

  // Kick off the first request from an async callback (oxlint
  // react/set-state-in-effect forbids direct setState in the effect body).
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (geoRequestedRef.current) return
      geoRequestedRef.current = true
      void applyGps()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [applyGps])

  const gpsState: GpsState = draft.gps ? 'idle' : draft.gpsState
  const gpsNote = draft.gps
    ? null
    : draft.gpsState === 'denied'
      ? 'GPS: permission denied — not included in this record.'
      : draft.gpsState === 'unavailable'
        ? 'GPS: unavailable — not included in this record.'
        : draft.gpsState === 'pending'
          ? 'GPS: still acquiring — not included in this record.'
          : 'GPS: not recorded.'

  const appearanceOptions = meta?.appearance_options ?? []

  const update = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }))

  const createSample = async (fix: GpsFix | null): Promise<Sample> =>
    api.createSample({
      appearance: draft.appearance,
      colour: draft.colour.trim() || null,
      approximate_weight: draft.weight.trim() || null,
      notes: draft.notes.trim() || null,
      ...(fix
        ? {
            gps_lat: fix.lat,
            gps_lon: fix.lon,
            gps_accuracy_m: fix.acc,
          }
        : {}),
    })

  const canCapture = kit?.test_type === 'COLOUR_REAGENT'

  /** Camera flow finished: the test entry is stored server-side. */
  const handleCaptured = (out: TestCreateOut) => {
    update({
      testDone: true,
      analysis: out.analysis,
      outcomeCode: out.test.outcome_code,
      step: 3,
    })
  }

  const goNext = async () => {
    setStepError(null)
    setBusy(true)
    try {
      if (step === 0) {
        // Best-effort fix: use one already captured, otherwise wait (bounded)
        // so the signed record and the sample row agree on GPS.
        const fix = draft.gps ?? (await applyGps())
        let sample: Sample | null = null
        if (draft.sampleId) {
          try {
            sample = await api.getSample(draft.sampleId)
            if (sample.status === 'SIGNED') {
              setStepError('This sample is already signed. Start a new test.')
              return
            }
          } catch (err) {
            if (!(err instanceof ApiError && err.status === 404)) throw err
            sample = null // stale draft id - recreate below
          }
        }
        if (!sample) sample = await createSample(fix)
        update({ sampleId: sample.id, sampleCode: sample.sample_code, step: 1 })
      } else if (step === 1) {
        if (!draft.kitCode) {
          setStepError('Choose the test kit you are using.')
          return
        }
        update({ step: 2 })
      } else if (step === 2) {
        if (draft.testDone) {
          // Test already stored server-side - Continue returns to the review
          // without recording a second test.
          update({ step: 3 })
          return
        }
        if (draft.mode === 'camera' && canCapture) return // handled by CaptureFlow
        if (!draft.sampleId || !kit) return
        if (!draft.outcomeCode) {
          setStepError('Choose the outcome you observed.')
          return
        }
        const out = await api.addTest(draft.sampleId, {
          test_type: kit.test_type,
          kit_code: kit.code,
          outcome_code: draft.outcomeCode,
          ...(draft.kitBatch.trim() ? { kit_batch: draft.kitBatch.trim() } : {}),
          ...(draft.timeSeconds
            ? { time_since_reaction_seconds: draft.timeSeconds }
            : {}),
          input: {},
          source: 'MANUAL',
        })
        update({ testDone: true, analysis: out.analysis, step: 3 })
      } else if (step === 3) {
        update({ step: 4 })
      }
    } catch (err) {
      setStepError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const goBack = () => {
    setStepError(null)
    // Once a test is recorded the Sample step is read-only: allow
    // Review -> Result -> Kit so entries can be double-checked before
    // signing (or so another test can be chosen). Sample is server-owned
    // (no edit endpoint) — its Back button is disabled instead of dead-clicking.
    const minAllowed = hasRecordedTests ? STEPS.indexOf('Kit') : 0
    if (step > minAllowed) update({ step: step - 1 })
  }

  /** Unlock Kit/Result to record an additional test on the same sample. */
  const startAnotherTest = () => {
    setStepError(null)
    update({
      step: STEPS.indexOf('Kit'),
      testDone: false,
      outcomeCode: null,
      acknowledged: false,
    })
  }

  /** Abandon the in-progress extra test and return to the recorded state. */
  const cancelAnotherTest = () => {
    setStepError(null)
    update({ step: STEPS.indexOf('Review'), testDone: true })
  }

  const jumpTo = (index: number) => {
    // Recorded tests lock the Sample step; Kit/Result/Review stay reachable
    // (read-only while testDone, editable when starting another test).
    const minAllowed = hasRecordedTests ? STEPS.indexOf('Kit') : 0
    const allowed = index < step && index >= minAllowed
    if (!allowed) return
    setStepError(null)
    update({ step: index })
  }

  const finalize = async () => {
    if (!draft.sampleId || !draft.acknowledged) return
    setBusy(true)
    setStepError(null)
    try {
      const res = await api.finalize(draft.sampleId)
      clearStoredDraft()
      update({
        record: {
          id: res.record.id,
          hash: res.record.record_hash,
          status: res.record.status,
          signature: res.record.signature,
          server_timestamp: res.record.server_timestamp,
          public_key_id: res.record.public_key_id,
        },
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && draft.sampleCode) {
        // Already signed (e.g. signed elsewhere) - surface the stored record.
        try {
          const list = await api.listRecords(draft.sampleCode)
          const item = list.items.find((r) => r.sample_id === draft.sampleId)
          if (item) {
            clearStoredDraft()
            let signature: string | null = null
            try {
              const detail = await api.getRecord(item.id)
              signature = detail.bundle.signature ?? null
            } catch {
              /* signature shown as unavailable */
            }
            update({
              record: {
                id: item.id,
                hash: item.record_hash,
                status: item.status,
                signature,
                server_timestamp: item.server_timestamp,
                public_key_id: item.public_key_id,
              },
            })
            return
          }
        } catch {
          /* fall through to the generic error below */
        }
      }
      setStepError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const startOver = () => {
    if (
      !window.confirm(
        'Discard this draft and start a new test? The stored draft will be removed.',
      )
    )
      return
    clearStoredDraft()
    setStepError(null)
    setDraft({ ...EMPTY_DRAFT })
  }

  const onSubmitForm = (event: FormEvent) => {
    event.preventDefault()
    void goNext()
  }

  return (
    <>
      <PageHeader
        title="New field test"
        subtitle="Five steps: describe the sample, choose the kit, record the observed reaction, review the analysis, then sign the record. Drafts save locally as you go."
        actions={
          draft.record ? null : (
            <Button variant="ghost" onClick={startOver} iconBefore={<RotateCcw size={16} />}>
              Start over
            </Button>
          )
        }
      />

      <aside className="fp-rail fp-rail--session" aria-label="Field session">
        <span className="fp-rail__stripe" aria-hidden="true" />
        <div className="fp-rail__head">
          <span>Field session</span>
          <span className="fp-rail__led" aria-hidden="true" />
        </div>
        <div className="fp-rail__rows">
          <div className="fp-rail__row">
            <span className="fp-rail__label">Step</span>
            <span className="fp-rail__value">
              {step + 1} / {STEPS.length}
            </span>
          </div>
          <div className="fp-rail__row">
            <span className="fp-rail__label">Sample</span>
            <span
              className={`fp-rail__value${draft.sampleCode ? '' : ' fp-rail__value--pending'}`}
            >
              {draft.sampleCode ?? 'pending'}
            </span>
          </div>
          <div className="fp-rail__row">
            <span className="fp-rail__label">Kit</span>
            <span
              className={`fp-rail__value${draft.kitCode ? '' : ' fp-rail__value--pending'}`}
            >
              {draft.kitCode ?? 'pending'}
            </span>
          </div>
          <div className="fp-rail__row">
            <span className="fp-rail__label">Read time</span>
            <span className="fp-rail__value">{formatTime(draft.timeSeconds)}</span>
          </div>
          <div className="fp-rail__row">
            <span className="fp-rail__label">Record</span>
            <span
              className={`fp-rail__value${draft.record ? '' : ' fp-rail__value--pending'}`}
            >
              {draft.record ? 'signed' : 'draft'}
            </span>
          </div>
        </div>
        <p className="fp-rail__note">
          Draft autosaves on this device; nothing uploads until you sign.
        </p>
      </aside>

      <div className="fp-wizard">
        <div className="fp-wizard__autosave" aria-live="polite">
          <Check size={14} aria-hidden="true" />
          {draft.record
            ? 'Draft cleared - record signed.'
            : savedAt
              ? `Draft saved locally at ${new Date(savedAt).toLocaleTimeString()}`
              : 'Draft saves automatically on this device'}
        </div>

        <ol className="fp-stepper">
          {STEPS.map((label, index) => {
            const state =
              index === step ? 'is-current' : index < step ? 'is-done' : ''
            const clickable =
              index < step &&
              (!hasRecordedTests || index >= STEPS.indexOf('Kit'))
            return (
              <li key={label} className={`fp-stepper__item ${state}`}>
                <button
                  type="button"
                  className={`fp-stepper__btn${clickable ? ' is-clickable' : ''}`}
                  disabled={!clickable}
                  onClick={() => jumpTo(index)}
                  aria-current={index === step ? 'step' : undefined}
                >
                  <span className="fp-stepper__bullet">
                    {index < step ? <Check size={16} aria-hidden="true" /> : index + 1}
                  </span>
                  <span className="fp-stepper__label">{label}</span>
                </button>
              </li>
            )
          })}
        </ol>

        {refError ? (
          <Alert tone="danger" title="Reference data unavailable">
            {refError}{' '}
            <button type="button" className="fp-btn fp-btn--secondary fp-btn--sm" onClick={retryReference}>
              Retry
            </button>
          </Alert>
        ) : null}

        {stepError ? (
          <Alert tone="danger" title="Cannot continue">
            {stepError}
          </Alert>
        ) : null}

        {/* ------------------------------------------------------------ 1 */}
        {step === 0 ? (
          <Card>
            <CardHeader
              title="Sample details"
              subtitle="Describe what you seized, exactly as observed in the field."
            />
            <CardBody>
              <form className="fp-wizard__body" onSubmit={onSubmitForm}>
                <div className="fp-wizard__grid fp-wizard__grid--2">
                  <SelectField
                    label="Appearance"
                    required
                    value={draft.appearance}
                    onChange={(event) => update({ appearance: event.target.value })}
                    hint={meta ? 'From the API meta list.' : 'Loading options…'}
                  >
                    {appearanceOptions.map((option) => (
                      <option key={option} value={option}>
                        {option.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </SelectField>
                  <TextField
                    label="Colour"
                    placeholder="e.g. off-white"
                    maxLength={64}
                    value={draft.colour}
                    onChange={(event) => update({ colour: event.target.value })}
                  />
                  <TextField
                    label="Approximate weight"
                    placeholder="e.g. ~2 g"
                    maxLength={32}
                    value={draft.weight}
                    onChange={(event) => update({ weight: event.target.value })}
                  />
                </div>
                <TextAreaField
                  label="Notes"
                  placeholder="Packaging, location, observations…"
                  maxLength={4000}
                  value={draft.notes}
                  onChange={(event) => update({ notes: event.target.value })}
                />

                <div className={`fp-gps fp-gps--${gpsState}`}>
                  <span className="fp-gps__icon" aria-hidden="true">
                    <MapPin size={16} />
                  </span>
                  {draft.gps ? (
                    <span>
                      Location saved for this record:{' '}
                      <span className="fp-mono">
                        {draft.gps.lat.toFixed(5)}, {draft.gps.lon.toFixed(5)}
                        {draft.gps.acc !== null ? ` ±${Math.round(draft.gps.acc)} m` : ''}
                      </span>
                    </span>
                  ) : gpsState === 'pending' ? (
                    <span>Getting your location (browser GPS)…</span>
                  ) : gpsState === 'denied' ? (
                    <span>
                      Location permission denied — the record will be saved without GPS.
                    </span>
                  ) : gpsState === 'unavailable' ? (
                    <span>Location unavailable — the record will be saved without GPS.</span>
                  ) : (
                    <span>Location not requested.</span>
                  )}
                  {gpsState === 'denied' || gpsState === 'unavailable' ? (
                    <button
                      type="button"
                      className="fp-btn fp-btn--ghost fp-btn--sm"
                      onClick={retryGps}
                    >
                      Try again
                    </button>
                  ) : null}
                </div>

                <div className="fp-wizard__actions">
                  <span />
                  <button
                    type="submit"
                    className="fp-btn fp-btn--primary fp-btn--lg"
                    disabled={busy || refLoading}
                  >
                    {busy ? 'Saving…' : 'Continue'}
                    <ArrowRight size={18} aria-hidden="true" />
                  </button>
                </div>
              </form>
            </CardBody>
          </Card>
        ) : null}

        {/* ------------------------------------------------------------ 2 */}
        {step === 1 ? (
          <Card>
            <CardHeader
              title="Choose the kit"
              subtitle="Only kits stored in the API are shown - results come from the seeded reference data."
              actions={
                draft.sampleCode ? (
                  <Badge tone="neutral" mono>
                    {draft.sampleCode}
                  </Badge>
                ) : null
              }
            />
            <CardBody>
              <form className="fp-wizard__body" onSubmit={onSubmitForm}>
                {refLoading ? (
                  <LoadingBlock label="Loading kits…" />
                ) : kits && kits.length === 0 ? (
                  <Alert tone="warning" title="No active kits">
                    The API returned no kits. Re-seed the database.
                  </Alert>
                ) : (
                  <div className="fp-choices fp-choices--cards">
                    {kits?.map((option) => (
                      <label
                        key={option.code}
                        className={`fp-choice${draft.kitCode === option.code ? ' is-selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="kit"
                          className="fp-choice__radio"
                          checked={draft.kitCode === option.code}
                          disabled={draft.testDone}
                          onChange={() =>
                            update({
                              kitCode: option.code,
                              outcomeCode: null,
                              ...(option.reaction_time_seconds
                                ? { timeSeconds: option.reaction_time_seconds }
                                : {}),
                            })
                          }
                        />
                        <span className="fp-choice__body">
                          <span className="fp-choice__title">
                            {option.name}
                            <span className="fp-choice__code">{option.code}</span>
                          </span>
                          <span className="fp-choice__hint">
                            {option.test_type.replace(/_/g, ' ').toLowerCase()}
                            {option.reaction_time_seconds
                              ? ` · read at ${formatTime(option.reaction_time_seconds)}`
                              : ''}
                          </span>
                          {option.description ? (
                            <span className="fp-choice__hint">{option.description}</span>
                          ) : null}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
                <p className="fp-choice__hint">
                  {kits?.find((k) => k.code === draft.kitCode)?.source_citation ??
                    'Pick a kit to see the published method source used for its expected colours.'}
                </p>
                <div className="fp-wizard__actions">
                  {hasRecordedTests && !draft.testDone ? (
                    <button
                      type="button"
                      className="fp-btn fp-btn--secondary fp-btn--lg"
                      onClick={cancelAnotherTest}
                      disabled={busy}
                    >
                      <ArrowLeft size={18} aria-hidden="true" />
                      Cancel adding a test
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="fp-btn fp-btn--secondary fp-btn--lg"
                      onClick={goBack}
                      disabled={busy || hasRecordedTests}
                      title={
                        hasRecordedTests
                          ? 'Sample details are locked once a test is recorded.'
                          : undefined
                      }
                    >
                      <ArrowLeft size={18} aria-hidden="true" />
                      Back
                    </button>
                  )}
                  <button
                    type="submit"
                    className="fp-btn fp-btn--primary fp-btn--lg"
                    disabled={busy || !draft.kitCode}
                  >
                    Continue
                    <ArrowRight size={18} aria-hidden="true" />
                  </button>
                </div>
              </form>
            </CardBody>
          </Card>
        ) : null}

        {/* ------------------------------------------------------------ 3 */}
        {step === 2 ? (
          <Card>
            <CardHeader
              title="Record the outcome"
              subtitle={
                kit
                  ? draft.testDone
                    ? `${kit.name} - already recorded and locked.`
                    : `${kit.name} - enter it manually or read the colour from a photo.`
                  : 'Record the observed outcome.'
              }
            />
            <CardBody>
              <div className="fp-wizard__body">
                <div className="fp-wizard__grid fp-wizard__grid--2">
                  <SelectField
                    label="Time since reaction"
                    value={String(draft.timeSeconds)}
                    onChange={(event) => update({ timeSeconds: Number(event.target.value) })}
                    disabled={draft.testDone}
                    hint={
                      kit?.reaction_time_seconds
                        ? `Manufacturer reading time: ${formatTime(kit.reaction_time_seconds)}.`
                        : 'Seconds elapsed since mixing the sample with the reagent.'
                    }
                  >
                    {TIME_OPTIONS.map((seconds) => (
                      <option key={seconds} value={seconds}>
                        {formatTime(seconds)}
                      </option>
                    ))}
                  </SelectField>
                  <TextField
                    label="Kit batch number"
                    placeholder="e.g. 4471-A"
                    maxLength={48}
                    value={draft.kitBatch}
                    onChange={(event) => update({ kitBatch: event.target.value })}
                    disabled={draft.testDone}
                    hint="Printed on the kit - kept with the record."
                  />
                </div>

                {draft.testDone ? null : (
                  <SegmentedControl
                    ariaLabel="Entry mode"
                    options={
                      canCapture
                        ? ([
                            { value: 'manual', label: 'Manual entry' },
                            { value: 'camera', label: 'Camera capture' },
                          ] as const)
                        : ([{ value: 'manual', label: 'Manual entry' }] as const)
                    }
                    value={draft.mode === 'camera' && canCapture ? 'camera' : 'manual'}
                    onChange={(value) => update({ mode: value })}
                  />
                )}
                {canCapture || draft.testDone ? null : (
                  <p className="fp-field__hint">
                    Camera colour reading is only available for colour-reagent kits —
                    {' '}
                    {kit?.name ?? 'this kit'} uses manual entry.
                  </p>
                )}

                {draft.mode === 'camera' && canCapture && !draft.testDone && draft.sampleId && kit ? (
                  <CaptureFlow
                    kit={kit}
                    sampleId={draft.sampleId}
                    timeSeconds={draft.timeSeconds}
                    kitBatch={draft.kitBatch}
                    onBack={goBack}
                    onSaved={handleCaptured}
                  />
                ) : (
                  <form className="fp-wizard__body" onSubmit={onSubmitForm}>
                    <div className="fp-choices">
                      {kit?.outcomes.map((outcome) => (
                        <label
                          key={outcome.code}
                          className={`fp-choice${draft.outcomeCode === outcome.code ? ' is-selected' : ''}`}
                        >
                          <input
                            type="radio"
                            name="outcome"
                            className="fp-choice__radio"
                            checked={draft.outcomeCode === outcome.code}
                            disabled={draft.testDone}
                            onChange={() => update({ outcomeCode: outcome.code })}
                          />
                          <span className="fp-choice__swatch" aria-hidden="true"
                            style={{ background: outcome.hex ?? 'transparent' }}
                          />
                          <span className="fp-choice__body">
                            <span className="fp-choice__title">
                              {outcome.label}
                              <span className="fp-choice__code">{outcome.code}</span>
                            </span>
                            {outcome.interpretation ? (
                              <span className="fp-choice__hint">{outcome.interpretation}</span>
                            ) : null}
                          </span>
                        </label>
                      ))}
                    </div>

                    <div className="fp-wizard__actions">
                      <button
                        type="button"
                        className="fp-btn fp-btn--secondary fp-btn--lg"
                        onClick={goBack}
                        disabled={busy}
                      >
                        <ArrowLeft size={18} aria-hidden="true" />
                        Back
                      </button>
                      {draft.testDone ? (
                        <button
                          type="button"
                          className="fp-btn fp-btn--secondary fp-btn--lg"
                          onClick={startAnotherTest}
                          disabled={busy}
                        >
                          <Plus size={18} aria-hidden="true" />
                          Run another test
                        </button>
                      ) : null}
                      <button
                        type="submit"
                        className="fp-btn fp-btn--primary fp-btn--lg"
                        disabled={busy || (!draft.testDone && !draft.outcomeCode)}
                      >
                        {busy
                          ? 'Recording…'
                          : draft.testDone
                            ? 'Continue to review'
                            : 'Continue'}
                        <ArrowRight size={18} aria-hidden="true" />
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </CardBody>
          </Card>
        ) : null}

        {/* ------------------------------------------------------------ 4 */}
        {step === 3 ? (
          <Card>
            <CardHeader
              title="Review the analysis"
              subtitle="Computed by the scoring engine from your recorded reaction."
            />
            <CardBody>
              <div className="fp-wizard__body">
                <KeyValue
                  items={[
                    { label: 'Sample', value: draft.sampleCode ?? '—' },
                    {
                      label: 'Details',
                      value: [
                        draft.appearance.replace(/_/g, ' '),
                        draft.colour,
                        draft.weight,
                      ]
                        .filter(Boolean)
                        .join(' · '),
                    },
                    {
                      label:
                        (draft.analysis?.counts.tests_entered ?? 0) > 1
                          ? 'Tests'
                          : 'Test',
                      value: `${
                        (draft.analysis?.counts.tests_entered ?? 0) > 1
                          ? `${draft.analysis?.counts.tests_entered} recorded · `
                          : ''
                      }${kit?.name ?? draft.kitCode ?? '—'}${
                        draft.kitBatch ? ` · batch ${draft.kitBatch}` : ''
                      }`,
                    },
                    {
                      label: 'Observed',
                      value: `${
                        kit?.outcomes.find((o) => o.code === draft.outcomeCode)?.label ??
                        draft.outcomeCode ??
                        '—'
                      } at ${formatTime(draft.timeSeconds)}`,
                    },
                  ]}
                />

                {draft.analysis ? (
                  <Alert tone="neutral" title="Engine summary">
                    <div style={{ display: 'grid', gap: 'var(--sp-2)' }}>
                      <span style={{ display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap', alignItems: 'center' }}>
                        <StatusPill status={draft.analysis.status} size="lg" />
                        <span>
                          {draft.analysis.top_match
                            ? `Top match: ${draft.analysis.top_match.name} (${draft.analysis.top_match.percentage}%)`
                            : 'No candidate matches the evidence.'}
                        </span>
                      </span>
                      <span className="fp-counts">
                        <span className="fp-count">
                          tests <b>{draft.analysis.counts.tests_entered}</b>
                        </span>
                        <span className="fp-count">
                          informative <b>{draft.analysis.counts.informative}</b>
                        </span>
                        <span className="fp-count">
                          candidates <b>{draft.analysis.counts.candidates}</b>
                        </span>
                      </span>
                      {draft.analysis.flags.map((flag) => (
                        <span key={flag}>{flag}</span>
                      ))}
                    </div>
                  </Alert>
                ) : null}

                <Disclaimer />

                <div className="fp-wizard__actions">
                  <button
                    type="button"
                    className="fp-btn fp-btn--secondary fp-btn--lg"
                    onClick={goBack}
                    disabled={busy}
                  >
                    <ArrowLeft size={18} aria-hidden="true" />
                    Back
                  </button>
                  {draft.testDone ? (
                    <button
                      type="button"
                      className="fp-btn fp-btn--secondary fp-btn--lg"
                      onClick={startAnotherTest}
                      disabled={busy}
                    >
                      <Plus size={18} aria-hidden="true" />
                      Run another test
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="fp-btn fp-btn--primary fp-btn--lg"
                    onClick={goNext}
                    disabled={busy}
                  >
                    Continue to sign
                    <ArrowRight size={18} aria-hidden="true" />
                  </button>
                </div>
              </div>
            </CardBody>
          </Card>
        ) : null}

        {/* ------------------------------------------------------------ 5 */}
        {step === 4 ? (
          <Card>
            <CardHeader
              title="Sign the record"
              subtitle="Finalising creates an append-only, hash-chained, ECDSA-signed record. It cannot be edited afterwards."
            />
            <CardBody>
              <div className="fp-wizard__body">
                {draft.record ? (
                  <SignedRecordCard
                    record={draft.record}
                    gps={
                      draft.gps
                        ? { lat: draft.gps.lat, lon: draft.gps.lon, accuracy_m: draft.gps.acc }
                        : null
                    }
                    gpsNote={gpsNote}
                    sampleCode={draft.sampleCode}
                    actions={
                      <button
                        type="button"
                        className="fp-btn fp-btn--primary fp-btn--lg"
                        onClick={() =>
                          draft.sampleId &&
                          navigate(`/samples/${draft.sampleId}/analysis`)
                        }
                      >
                        View analysis
                        <ArrowRight size={18} aria-hidden="true" />
                      </button>
                    }
                  />
                ) : (
                  <>
                    <Disclaimer />
                    <Checkbox
                      label="I understand this is a presumptive field result."
                      hint="It is not a confirmed identification and not a substitute for laboratory analysis."
                      checked={draft.acknowledged}
                      onChange={(event) => update({ acknowledged: event.target.checked })}
                    />
                    <div className="fp-wizard__actions">
                      <button
                        type="button"
                        className="fp-btn fp-btn--secondary fp-btn--lg"
                        onClick={goBack}
                        disabled={busy}
                      >
                        <ArrowLeft size={18} aria-hidden="true" />
                        Back
                      </button>
                      <button
                        type="button"
                        className="fp-btn fp-btn--primary fp-btn--lg"
                        onClick={() => void finalize()}
                        disabled={busy || !draft.acknowledged}
                      >
                        {busy ? 'Signing…' : 'Finalize and sign record'}
                        <FileSignature size={18} aria-hidden="true" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            </CardBody>
          </Card>
        ) : null}
      </div>

      <aside className="fp-rail fp-rail--protocol" aria-label="Field protocol">
        <span className="fp-rail__stripe" aria-hidden="true" />
        <div className="fp-rail__head">
          <span>Field protocol</span>
        </div>
        <p className="fp-rail__warn">
          <TriangleAlert size={14} aria-hidden="true" />
          Presumptive only - laboratory confirmation required.
        </p>
        <ul className="fp-rail__list">
          <li>
            <ShieldCheck size={14} aria-hidden="true" />
            Gloves and eye protection; work in a ventilated area.
          </li>
          <li>
            <Flame size={14} aria-hidden="true" />
            No open flame near reagents.
          </li>
          <li>
            <Timer size={14} aria-hidden="true" />
            Time the read exactly; never extrapolate past the window.
          </li>
          <li>
            <Eye size={14} aria-hidden="true" />
            Match the colour to the chart before disposal.
          </li>
          <li>
            <Camera size={14} aria-hidden="true" />
            Photograph the result and kit lot before packing out.
          </li>
        </ul>
        <p className="fp-rail__note">
          Expected colours follow published method sources and manufacturer
          charts - per-kit citations appear in the kit step and on every
          evidence row of the result.
        </p>
      </aside>
    </>
  )
}

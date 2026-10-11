import { useCallback, useEffect, useState } from 'react'
import {
  ArrowRight,
  ChevronDown,
  CircleCheck,
  CircleX,
  FileSignature,
  FlaskConical,
  Info,
  Minus,
  ShieldCheck,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import {
  Alert,
  Badge,
  Card,
  CardBody,
  CardHeader,
  Disclaimer,
  EmptyState,
  KeyValue,
  LoadingBlock,
  PageHeader,
  SignedRecordCard,
  StatusPill,
} from '../components'
import type { SignedRecordData } from '../components'
import { api, ApiError } from '../lib/api'
import type { Analysis, Sample } from '../lib/api'
import './pages.css'

function firstSentence(text: string): string {
  const match = text.match(/^[^.!?]*[.!?]/)
  return match ? match[0].trim() : text
}

function formatTime(seconds: number): string {
  if (seconds % 60 === 0 && seconds >= 60) return `${seconds / 60} min`
  return `${seconds} s`
}

export default function AnalysisResultPage() {
  const { id = '' } = useParams()
  const [sample, setSample] = useState<Sample | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [record, setRecord] = useState<SignedRecordData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [signing, setSigning] = useState(false)
  const [signError, setSignError] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!id) return
    Promise.all([api.getSample(id), api.getAnalysis(id)])
      .then(async ([sampleRes, analysisRes]) => {
        setSample(sampleRes)
        setAnalysis(analysisRes)
        if (sampleRes.status === 'SIGNED') {
          try {
            const list = await api.listRecords(sampleRes.sample_code)
            const item = list.items.find((r) => r.sample_id === sampleRes.id)
            if (item) {
              let signature: string | null = null
              try {
                const detail = await api.getRecord(item.id)
                signature = detail.bundle.signature ?? null
              } catch {
                /* signature shown as unavailable */
              }
              setRecord({
                id: item.id,
                hash: item.record_hash,
                status: item.status,
                signature,
                server_timestamp: item.server_timestamp,
                public_key_id: item.public_key_id,
              })
            }
          } catch {
            /* record panel stays hidden; signing controls also stay hidden */
          }
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not load this analysis.')
      })
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const finalize = async () => {
    setSigning(true)
    setSignError(null)
    try {
      const res = await api.finalize(id)
      setRecord({
        id: res.record.id,
        hash: res.record.record_hash,
        status: res.record.status,
        signature: res.record.signature,
        server_timestamp: res.record.server_timestamp,
        public_key_id: res.record.public_key_id,
      })
      if (sample) setSample({ ...sample, status: 'SIGNED' })
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && sample) {
        try {
          const list = await api.listRecords(sample.sample_code)
          const item = list.items.find((r) => r.sample_id === sample.id)
          if (item) {
            let signature: string | null = null
            try {
              const detail = await api.getRecord(item.id)
              signature = detail.bundle.signature ?? null
            } catch {
              /* signature shown as unavailable */
            }
            setRecord({
              id: item.id,
              hash: item.record_hash,
              status: item.status,
              signature,
              server_timestamp: item.server_timestamp,
              public_key_id: item.public_key_id,
            })
            setSample({ ...sample, status: 'SIGNED' })
            return
          }
        } catch {
          /* fall through */
        }
      }
      setSignError(err instanceof ApiError ? err.message : 'Finalising failed.')
    } finally {
      setSigning(false)
    }
  }

  if (loading) return <LoadingBlock label="Loading analysis…" />

  if (error || !analysis || !sample) {
    return (
      <>
        <PageHeader title="Analysis result" />
        <Alert tone="danger" title="Could not load this result">
          {error ?? 'The API returned no analysis for this sample.'}
        </Alert>
        <div style={{ marginTop: 'var(--sp-3)' }}>
          <Link className="fp-btn fp-btn--secondary fp-btn--md" to="/">
            Back to dashboard
          </Link>
        </div>
      </>
    )
  }

  const top = analysis.top_match
  const percentage = top ? Math.max(0, Math.min(top.percentage, 100)) : 0
  const gaugeRadius = 64
  const circumference = 2 * Math.PI * gaugeRadius
  const maxAlternative = Math.max(
    1,
    ...analysis.alternatives.map((a) => a.percentage),
    top?.percentage ?? 1,
  )

  return (
    <>
      <PageHeader
        title={`Analysis · ${sample.sample_code}`}
        subtitle="Computed from the recorded reactions. Presumptive decision support only."
        actions={
          sample.status !== 'SIGNED' && !record ? (
            <Badge tone="neutral" icon={<Info size={14} />}>
              Not signed yet
            </Badge>
          ) : (
            <Badge tone="navy" icon={<ShieldCheck size={14} />}>
              Signed record
            </Badge>
          )
        }
      />

      <div className="fp-result">
        {/* --------------------------------------------------------- hero */}
        <Card hero>
          <CardBody>
            <div className="fp-result__hero">
              <div className="fp-gauge-wrap">
                <div
                  className="fp-gauge"
                  role="img"
                  aria-label={
                    top ? `Confidence ${percentage}% for ${top.name}` : 'No confidence score'
                  }
                >
                  <svg viewBox="0 0 144 144" aria-hidden="true">
                    <circle
                      className="fp-gauge__track"
                      cx="72"
                      cy="72"
                      r={gaugeRadius}
                      fill="none"
                      strokeWidth="12"
                    />
                    <circle
                      className="fp-gauge__fill"
                      cx="72"
                      cy="72"
                      r={gaugeRadius}
                      fill="none"
                      strokeWidth="12"
                      strokeDasharray={circumference}
                      strokeDashoffset={circumference * (1 - percentage / 100)}
                    />
                  </svg>
                  <span className="fp-gauge__label">
                    <span className="fp-gauge__value">{percentage}%</span>
                    <span className="fp-gauge__caption">
                      {top ? 'confidence' : 'no match'}
                    </span>
                  </span>
                </div>
                {analysis.confidence ? (
                  <div
                    className="fp-band"
                    title={`Heuristic uncertainty band - ${analysis.confidence.method}`}
                  >
                    <span className="fp-band__head">
                      <span className="fp-band__label">Uncertainty band</span>
                      <span className="fp-band__value">
                        {Math.round(analysis.confidence.low * 100)}–
                        {Math.round(analysis.confidence.high * 100)}% ·{' '}
                        {analysis.confidence.label}
                      </span>
                    </span>
                    <span className="fp-band__track" aria-hidden="true">
                      <span
                        className="fp-band__span"
                        style={{
                          left: `${analysis.confidence.low * 100}%`,
                          width: `${analysis.confidence.width * 100}%`,
                        }}
                      />
                      {top ? (
                        <span
                          className="fp-band__marker"
                          style={{ left: `${percentage}%` }}
                        />
                      ) : null}
                    </span>
                  </div>
                ) : null}
              </div>

              <div className="fp-result__summary">
                <StatusPill status={analysis.status} size="lg" />
                <span className="fp-result__topname">
                  {top ? top.name : 'No candidate substance'}
                </span>
                <span className="fp-choice__code" style={{ color: 'inherit', opacity: 0.7 }}>
                  {top ? top.code : `ranked ${analysis.counts.candidates} candidates`}
                </span>
                <p className="fp-result__one-liner">
                  {firstSentence(analysis.explanation)}
                </p>
              </div>
            </div>
          </CardBody>
        </Card>

        {analysis.flags.length > 0 ? (
          <Alert tone="warning" title="Engine flags">
            <ul style={{ paddingInlineStart: 'var(--sp-3)' }}>
              {analysis.flags.map((flag) => (
                <li key={flag}>{flag}</li>
              ))}
            </ul>
          </Alert>
        ) : null}

        {/* -------------------------------------------------- alternatives */}
        <Card>
          <CardHeader
            title="Ranked alternatives"
            subtitle="Posterior share of the candidate set after your observations."
          />
          <CardBody>
            {analysis.alternatives.length === 0 ? (
              <EmptyState
                title="No close alternatives"
                message={
                  top
                    ? 'No other candidate reached a 2% share of the ranking.'
                    : 'No candidate scored above the no-match threshold.'
                }
              />
            ) : (
              <div className="fp-alts">
                {analysis.alternatives.map((alt) => (
                  <div className="fp-alt" key={alt.substance_id}>
                    <span className="fp-alt__name" title={alt.name}>
                      {alt.name}
                    </span>
                    <span className="fp-alt__track">
                      <span
                        className="fp-alt__fill"
                        style={{
                          width: `${Math.max(2, (alt.percentage / maxAlternative) * 100)}%`,
                        }}
                      />
                    </span>
                    <span className="fp-alt__value">{alt.percentage}%</span>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        {/* ----------------------------------------------------- evidence */}
        <Card>
          <CardHeader
            title="Evidence"
            subtitle="Every recorded reaction, and how it relates to the top match."
            actions={
              <Badge tone="neutral" icon={<FlaskConical size={14} />}>
                {analysis.counts.tests_entered} test
                {analysis.counts.tests_entered === 1 ? '' : 's'}
              </Badge>
            }
          />
          <CardBody>
            {analysis.evidence.length === 0 ? (
              <EmptyState
                title="No tests recorded"
                message="Add at least one reaction in the wizard before analysing."
              />
            ) : (
              <ul className="fp-evidence">
                {analysis.evidence.map((row) => {
                  const supports = row.supports === true && row.informative
                  const contradicts = row.supports === false && row.informative
                  const Icon = supports ? CircleCheck : contradicts ? CircleX : Minus
                  const tone = supports
                    ? 'is-supports'
                    : contradicts
                      ? 'is-contradicts'
                      : 'is-neutral'
                  const verdict = !row.informative
                    ? 'not informative'
                    : supports
                      ? 'supports'
                      : contradicts
                        ? 'contradicts'
                        : 'not decisive'
                  return (
                    <li
                      key={row.ref}
                      className={`fp-evidence__item${row.informative ? '' : ' is-uninformative'}`}
                    >
                      <span className={`fp-evidence__icon ${tone}`} title={verdict}>
                        <Icon size={18} aria-hidden="true" />
                      </span>
                      <span className="fp-evidence__head">
                        {row.kit_name || row.kit_code}
                        <Badge tone="neutral">{row.outcome_label}</Badge>
                        <Badge tone={supports ? 'success' : contradicts ? 'danger' : 'neutral'}>
                          {verdict}
                        </Badge>
                        <span className="fp-evidence__ref" title={row.ref}>
                          {row.ref.length > 16 ? `${row.ref.slice(0, 8)}…` : row.ref}
                          {row.likelihood !== null
                            ? ` · p=${(row.likelihood * 100).toFixed(1)}%`
                            : ''}
                        </span>
                      </span>
                      <span className="fp-evidence__note">{row.note}</span>
                      {row.source_citation ? (
                        <span className="fp-evidence__cite">
                          Source: {row.source_citation}
                        </span>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            )}
          </CardBody>
        </Card>

        {/* -------------------------------------------- cross-reaction note */}
        {analysis.cross_reactions.length > 0 ? (
          <Alert tone="info" title="Cross-reaction note">
            {analysis.cross_reactions.map((cross) => (
              <div key={`${cross.kit_code}-${cross.outcome_label}`}>
                <strong>
                  {cross.kit_code} · {cross.outcome_label}
                </strong>{' '}
                can also be produced by: {cross.substances.join(', ')}.
              </div>
            ))}
          </Alert>
        ) : null}

        {/* --------------------------------------------------- why + notes */}
        <details className="fp-why">
          <summary>
            <ChevronDown size={16} aria-hidden="true" />
            Why this result
          </summary>
          <div className="fp-why__body">
            <p>{analysis.explanation}</p>
            {analysis.rule_notes.length > 0 ? (
              <ul className="fp-why__notes">
                {analysis.rule_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
            <div className="fp-counts">
              <span className="fp-count">
                candidates <b>{analysis.counts.candidates}</b>
              </span>
              <span className="fp-count">
                informative <b>{analysis.counts.informative}</b>
              </span>
              <span className="fp-count">
                presumptive <b>{analysis.counts.presumptive_informative}</b>
              </span>
              <span className="fp-count">
                inconclusive <b>{analysis.counts.inconclusive}</b>
              </span>
              <span className="fp-count">
                engine <b>{analysis.engine_version}</b>
              </span>
            </div>
          </div>
        </details>

        {/* ---------------------------------------------------- concentration */}
        <Card>
          <CardHeader title="Record details" />
          <CardBody>
            <KeyValue
              items={[
                { label: 'Sample', value: sample.sample_code },
                {
                  label: 'Operator',
                  value: sample.operator_username ?? sample.operator_id,
                },
                {
                  label: 'Tests',
                  value: sample.tests
                    .map(
                      (t) =>
                        `${t.kit_code ?? t.test_type}${
                          t.outcome_label ? `: ${t.outcome_label}` : ''
                        }${
                          t.time_since_reaction_seconds
                            ? ` @ ${formatTime(t.time_since_reaction_seconds)}`
                            : ''
                        }${t.kit_batch ? ` · batch ${t.kit_batch}` : ''}`,
                    )
                    .join(' | '),
                },
                {
                  label: 'Concentration',
                  value: <strong>{analysis.concentration}</strong>,
                },
                { label: 'Status', value: <StatusPill status={analysis.status} /> },
              ]}
            />
          </CardBody>
        </Card>

        {/* ------------------------------------------------------ finalize */}
        {record ? (
          <Card>
            <CardHeader
              title="Signed record"
              subtitle="Append-only, hash-chained and ECDSA-signed by the server."
              actions={
                <Badge tone="navy" icon={<ShieldCheck size={14} />}>
                  Signed
                </Badge>
              }
            />
            <CardBody>
              <SignedRecordCard
                record={record}
                gps={
                  sample.gps_lat !== null && sample.gps_lon !== null
                    ? {
                        lat: sample.gps_lat,
                        lon: sample.gps_lon,
                        accuracy_m: sample.gps_accuracy_m,
                      }
                    : null
                }
                gpsNote="GPS: not recorded for this sample."
                sampleCode={sample.sample_code}
              />
            </CardBody>
          </Card>
        ) : (
          <Card>
            <CardHeader
              title="Finalize and sign"
              subtitle="Creates the tamper-evident record for this sample. This cannot be undone."
            />
            <CardBody>
              <div className="fp-wizard__body">
                {signError ? (
                  <Alert tone="danger" title="Finalising failed">
                    {signError}
                  </Alert>
                ) : null}
                <Disclaimer />
                <button
                  type="button"
                  className="fp-btn fp-btn--primary fp-btn--lg"
                  onClick={() => void finalize()}
                  disabled={signing}
                >
                  {signing ? 'Signing…' : 'Finalize and sign record'}
                  <FileSignature size={18} aria-hidden="true" />
                </button>
              </div>
            </CardBody>
          </Card>
        )}

        <div style={{ display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
          <Link className="fp-btn fp-btn--secondary fp-btn--md" to="/new-test">
            New test
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <Link className="fp-btn fp-btn--ghost fp-btn--md" to="/">
            Dashboard
          </Link>
        </div>
      </div>
    </>
  )
}

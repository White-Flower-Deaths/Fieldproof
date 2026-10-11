import { useCallback, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import {
  CircleCheck,
  CircleDashed,
  CircleX,
  FileJson,
  Image as ImageIcon,
  Play,
  RefreshCw,
  ShieldCheck,
  ShieldX,
  Upload,
} from 'lucide-react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  Disclaimer,
  EmptyState,
  PageHeader,
} from '../components'
import { api } from '../lib/api'
import type { VerifyCheck, VerifyResult } from '../lib/api'
import { CONCENTRATION_NOTE } from '../lib/constants'
import './pages.css'

/** The checklist is always rendered in this order; checks the server did not
 *  return (e.g. early parse failure) show as "Not evaluated". */
const CHECK_ORDER = [
  { id: 'image_hash', label: 'Image hash (SHA-256)' },
  { id: 'record_hash', label: 'Record hash (SHA-256 of canonical JSON)' },
  { id: 'signature', label: 'Signature (ECDSA P-256)' },
  { id: 'chain', label: 'Chain integrity' },
  { id: 'registry', label: 'Server registry copy' },
] as const

type CheckState = VerifyCheck['status'] | 'NOT_EVALUATED'

function StatusIcon({ status }: { status: CheckState }) {
  if (status === 'PASS') return <CircleCheck size={20} aria-hidden="true" />
  if (status === 'FAIL') return <CircleX size={20} aria-hidden="true" />
  return <CircleDashed size={20} aria-hidden="true" />
}

function StatusWord({ status }: { status: CheckState }) {
  if (status === 'PASS') return <span className="fp-check__word is-pass">Passed</span>
  if (status === 'FAIL') return <span className="fp-check__word is-fail">Failed</span>
  if (status === 'SKIPPED') return <span className="fp-check__word is-skip">Skipped</span>
  return <span className="fp-check__word is-skip">Not evaluated</span>
}

function Dropzone({
  id,
  icon,
  title,
  hint,
  accept,
  fileName,
  onFile,
}: {
  id: string
  icon: ReactNode
  title: string
  hint: string
  accept: string
  fileName: string | null
  onFile: (file: File | null) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <div
      className={`fp-dropzone${dragging ? ' is-dragging' : ''}${fileName ? ' has-file' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        const file = event.dataTransfer.files.item(0)
        if (file) onFile(file)
      }}
    >
      <input
        ref={inputRef}
        id={id}
        type="file"
        className="fp-dropzone__input"
        accept={accept}
        onChange={(event) => onFile(event.target.files?.item(0) ?? null)}
      />
      <span className="fp-dropzone__icon" aria-hidden="true">
        {icon}
      </span>
      <span className="fp-dropzone__title">{title}</span>
      {fileName ? (
        <>
          <span className="fp-dropzone__file fp-hash">{fileName}</span>
          <span className="fp-dropzone__hint">{hint}</span>
          <span className="fp-dropzone__actions">
            <label className="fp-dropzone__link" htmlFor={id}>
              Choose another file
            </label>
            <button type="button" className="fp-dropzone__link" onClick={() => onFile(null)}>
              Remove
            </button>
          </span>
        </>
      ) : (
        <>
          <span className="fp-dropzone__hint">{hint}</span>
          <label className="fp-btn fp-btn--secondary fp-btn--sm fp-dropzone__cta" htmlFor={id}>
            <Upload size={16} aria-hidden="true" />
            Pick file
          </label>
          <span className="fp-dropzone__hint">or drop it here</span>
        </>
      )}
    </div>
  )
}

export default function VerifyPage() {
  const [recordFile, setRecordFile] = useState<File | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [demoNote, setDemoNote] = useState<string | null>(null)

  const runVerify = useCallback(async (record: File, image: File | null) => {
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const outcome = await api.verifyUpload(record, image)
      setResult(outcome)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification request failed.')
    } finally {
      setRunning(false)
    }
  }, [])

  const onSubmit = () => {
    if (!recordFile) return
    void runVerify(recordFile, imageFile)
  }

  /** Loads the latest signed record from the server; optionally tampers one
   *  field of the copy so the checklist can demonstrate a failure. */
  const loadExample = async (tampered: boolean) => {
    setError(null)
    setResult(null)
    setRunning(true)
    setDemoNote(null)
    try {
      const list = await api.listRecordsQuery({
        page_size: 1,
        sort_by: 'server_timestamp',
        sort_dir: 'desc',
      })
      if (list.items.length === 0) {
        throw new Error('No signed record exists yet - finalise a test first.')
      }
      const recordId = list.items[0].id
      // Exact server bytes: a JS JSON round-trip would reformat floats and
      // break the canonical hash even for an untampered record.
      const raw = await api.getRecordText(recordId)
      let text = raw
      if (tampered) {
        // Change only the first plain "status" field (the canonical_json copy
        // stores its quotes escaped, so it is never matched here).
        const tamperedText = raw.replace(
          /"status": "[^"]*"/,
          '"status": "CONFIRMED_BY_LAB"',
        )
        if (tamperedText === raw) {
          throw new Error('Could not modify the example record.')
        }
        text = tamperedText
      }
      const file = new File([text], 'record.json', { type: 'application/json' })
      setRecordFile(file)
      setImageFile(null)
      setDemoNote(
        tampered
          ? `Loaded record ${recordId} and deliberately changed one field (status → CONFIRMED_BY_LAB) in this copy; every other byte is unchanged.`
          : `Loaded record ${recordId} exactly as stored on the server.`,
      )
      const outcome = await api.verifyUpload(file, null)
      setResult(outcome)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not load the example record.')
    } finally {
      setRunning(false)
    }
  }

  const checksById = new Map((result?.checks ?? []).map((check) => [check.id, check]))
  const failedChecks = (result?.checks ?? []).filter((check) => check.status === 'FAIL')

  return (
    <>
      <PageHeader
        title="Verify a record"
        subtitle="Upload a signed record bundle (and, if available, its source image) to re-check the image hash, record hash, signature and chain integrity against this server."
        actions={
          <span className="fp-verify-actions">
            <Button
              variant="secondary"
              size="md"
              iconBefore={<ShieldCheck size={18} />}
              onClick={() => void loadExample(false)}
              disabled={running}
            >
              Try a valid example
            </Button>
            <Button
              variant="secondary"
              size="md"
              iconBefore={<ShieldX size={18} />}
              onClick={() => void loadExample(true)}
              disabled={running}
            >
              Try a tampered example
            </Button>
          </span>
        }
      />

      <div className="fp-verify-grid">
        <Card className="fp-verify-inputs">
          <CardBody>
            <div className="fp-verify-dropzones">
              <Dropzone
                id="verify-record-file"
                icon={<FileJson size={28} />}
                title="Record JSON"
                hint="Bundle exported from the log (JSON)"
                accept="application/json,.json"
                fileName={recordFile?.name ?? null}
                onFile={(file) => {
                  setRecordFile(file)
                  setResult(null)
                  setError(null)
                  setDemoNote(null)
                }}
              />
              <Dropzone
                id="verify-image-file"
                icon={<ImageIcon size={28} />}
                title="Source image (optional)"
                hint="JPEG/PNG captured for the test"
                accept="image/*"
                fileName={imageFile?.name ?? null}
                onFile={(file) => {
                  setImageFile(file)
                  setResult(null)
                  setError(null)
                  setDemoNote(null)
                }}
              />
            </div>

            <div className="fp-verify-run">
              <Button
                variant="primary"
                size="lg"
                iconBefore={<Play size={18} />}
                onClick={onSubmit}
                disabled={!recordFile}
                loading={running}
              >
                Run verification
              </Button>
              <span className="fp-verify-run__hint">
                {recordFile
                  ? imageFile
                    ? 'Record and image ready.'
                    : 'Record ready - image check will be skipped.'
                  : 'Add a record JSON file to start.'}
              </span>
            </div>

            {demoNote ? (
              <Alert tone="info" title="Demo loaded">
                {demoNote}
              </Alert>
            ) : null}
            {error ? (
              <Alert tone="danger" title="Verification could not run">
                {error}
              </Alert>
            ) : null}
          </CardBody>
        </Card>

        <Card className="fp-verify-result" aria-live="polite">
          <CardBody>
            {!result && !running ? (
              <EmptyState
                icon={<ShieldCheck size={36} />}
                title="No verification yet"
                message="Upload a record bundle or use one of the example buttons to run the checklist."
              />
            ) : running ? (
              <div className="fp-verify-running" role="status">
                <RefreshCw size={20} className="fp-spin" aria-hidden="true" />
                <span>Verifying record…</span>
              </div>
            ) : result ? (
              <>
                <div className="fp-verify-headline">
                  <Badge
                    tone={result.overall === 'PASS' ? 'success' : 'danger'}
                    size="lg"
                    icon={
                      result.overall === 'PASS' ? (
                        <ShieldCheck size={16} />
                      ) : (
                        <ShieldX size={16} />
                      )
                    }
                  >
                    {result.overall === 'PASS'
                      ? 'Verification passed'
                      : 'Verification failed'}
                  </Badge>
                  <span className="fp-verify-recordid fp-hash">{result.record_id ?? 'unknown record'}</span>
                  {result.sample_code ? (
                    <span className="fp-detail-muted">Sample {result.sample_code}</span>
                  ) : null}
                </div>

                {result.overall === 'FAIL' && failedChecks.length > 0 ? (
                  <Alert tone="danger" title="Checks failed">
                    <ul className="fp-verify-failed-list">
                      {failedChecks.map((check) => (
                        <li key={check.id}>
                          <strong>{check.label}</strong>: {check.detail}
                        </li>
                      ))}
                    </ul>
                  </Alert>
                ) : null}

                <ol className="fp-checks" aria-label="Verification checklist">
                  {CHECK_ORDER.map((row) => {
                    const check = checksById.get(row.id)
                    const status: CheckState = check?.status ?? 'NOT_EVALUATED'
                    return (
                      <li
                        key={row.id}
                        className={`fp-check${status === 'FAIL' ? ' is-fail' : ''}${status === 'PASS' ? ' is-pass' : ''}`}
                      >
                        <span className={`fp-check__icon fp-check__icon--${status === 'PASS' ? 'pass' : status === 'FAIL' ? 'fail' : 'skip'}`}>
                          <StatusIcon status={status} />
                        </span>
                        <span className="fp-check__body">
                          <span className="fp-check__label">{check?.label ?? row.label}</span>
                          <span className="fp-check__detail">
                            {check?.detail ?? 'Not evaluated in this run.'}
                          </span>
                        </span>
                        <StatusWord status={status} />
                      </li>
                    )
                  })}
                </ol>

                {result.warnings.length > 0 ? (
                  <Alert tone="warning" title="Warnings">
                    <ul className="fp-detail-warnings">
                      {result.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </Alert>
                ) : null}

                <p className="fp-verify-concentration" aria-label="Concentration">
                  {CONCENTRATION_NOTE}
                </p>
                <Disclaimer showConcentration={false} />
              </>
            ) : null}
          </CardBody>
        </Card>
      </div>
    </>
  )
}

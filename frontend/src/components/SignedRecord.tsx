import { useState } from 'react'
import type { ReactNode } from 'react'
import { Check, Copy, Download, ShieldCheck } from 'lucide-react'
import { Alert } from './Alert'
import { Badge } from './Badge'
import { Button } from './Button'
import { Disclaimer } from './Disclaimer'
import { KeyValue } from './Misc'
import { StatusPill } from './StatusPill'
import { api } from '../lib/api'

export type SignedRecordData = {
  id: string
  status: string
  hash: string
  signature: string | null
  server_timestamp: string | null
  public_key_id?: string | null
}

export type SignedRecordGps = {
  lat: number
  lon: number
  accuracy_m: number | null
} | null

function formatGps(gps: NonNullable<SignedRecordGps>): string {
  const acc =
    gps.accuracy_m !== null && gps.accuracy_m !== undefined
      ? ` ±${Math.round(gps.accuracy_m)} m`
      : ''
  return `${gps.lat.toFixed(5)}, ${gps.lon.toFixed(5)}${acc}`
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const [state, setState] = useState<'idle' | 'ok' | 'fail'>('idle')
  const copy = () => {
    const fallback = (): boolean => {
      try {
        const area = document.createElement('textarea')
        area.value = value
        area.setAttribute('readonly', '')
        area.style.position = 'fixed'
        area.style.opacity = '0'
        document.body.appendChild(area)
        area.select()
        const ok = document.execCommand('copy')
        area.remove()
        return ok
      } catch {
        return false
      }
    }
    void (async () => {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('no clipboard')
        await navigator.clipboard.writeText(value)
        setState('ok')
      } catch {
        setState(fallback() ? 'ok' : 'fail')
      }
      window.setTimeout(() => setState('idle'), 2500)
    })()
  }
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={copy}
      className="fp-copybtn"
      iconBefore={state === 'ok' ? <Check size={14} /> : <Copy size={14} />}
      aria-label={`Copy ${label}`}
    >
      {state === 'ok' ? 'Copied' : state === 'fail' ? 'Copy failed' : `Copy ${label}`}
    </Button>
  )
}

/**
 * The signed record screen shown after finalize: record ID, server timestamp,
 * GPS (browser geolocation, or a graceful note when it was denied), hash and
 * signature in monospace with copy buttons, and a record-JSON download.
 * Disclaimer + exact concentration line are mandatory here (hard rule).
 */
export function SignedRecordCard({
  record,
  gps = null,
  gpsNote,
  sampleCode,
  actions,
}: {
  record: SignedRecordData
  gps?: SignedRecordGps
  gpsNote?: string | null
  sampleCode?: string | null
  actions?: ReactNode
}) {
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const download = () => {
    setDownloading(true)
    setDownloadError(null)
    api
      .downloadRecordJson(record.id)
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : 'Could not download the record.'
        setDownloadError(message)
      })
      .finally(() => setDownloading(false))
  }

  return (
    <div className="fp-signed fp-signed-record" data-testid="signed-record">
      <Alert tone="success" title="Record signed">
        {sampleCode
          ? `Sample ${sampleCode} is now an append-only signed record.`
          : 'This sample is now an append-only signed record.'}
      </Alert>

      <KeyValue
        items={[
          { label: 'Record ID', value: <span className="fp-mono">{record.id}</span> },
          { label: 'Status', value: <StatusPill status={record.status} /> },
          {
            label: 'Server timestamp',
            value: (
              <span className="fp-mono fp-signed-record__time">
                {record.server_timestamp ?? '—'}
              </span>
            ),
          },
          {
            label: 'GPS',
            value: gps ? (
              <span className="fp-mono">{formatGps(gps)}</span>
            ) : (
              <span className="fp-detail-muted">
                {gpsNote ?? 'Not recorded'}
              </span>
            ),
          },
          { label: 'Algorithm', value: 'ECDSA P-256 · SHA-256' },
          ...(record.public_key_id
            ? [
                {
                  label: 'Public key',
                  value: <span className="fp-mono">{record.public_key_id}</span>,
                },
              ]
            : []),
        ]}
      />

      <div className="fp-copyrow">
        <div className="fp-copyrow__main">
          <div className="fp-stat__label">Record hash (SHA-256)</div>
          <div className="fp-hash">{record.hash}</div>
        </div>
        <CopyButton value={record.hash} label="record hash" />
      </div>

      <div className="fp-copyrow">
        <div className="fp-copyrow__main">
          <div className="fp-stat__label">Signature (ECDSA P-256, DER, base64)</div>
          <div className="fp-signature">
            {record.signature ?? 'Signature not available for this record.'}
          </div>
        </div>
        {record.signature ? <CopyButton value={record.signature} label="signature" /> : null}
      </div>

      <Disclaimer />

      {downloadError ? (
        <Alert tone="danger" title="Download failed">
          {downloadError}
        </Alert>
      ) : null}

      <div className="fp-wizard__actions">
        <span className="fp-signed-record__badges">
          <Badge tone="navy" icon={<ShieldCheck size={14} />}>
            Signed record
          </Badge>
        </span>
        <span className="fp-signed-record__btns">
          {actions}
          <Button
            variant="secondary"
            onClick={download}
            loading={downloading}
            iconBefore={<Download size={16} />}
          >
            Download record JSON
          </Button>
        </span>
      </div>
    </div>
  )
}

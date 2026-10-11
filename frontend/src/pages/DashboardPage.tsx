import { useEffect, useState } from 'react'
import { ClipboardList, FileCheck, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Card,
  CardBody,
  EmptyState,
  LoadingBlock,
  PageHeader,
} from '../components'
import { api } from '../lib/api'
import type { Sample } from '../lib/api'
import './pages.css'

function sampleStatusBadge(status: string) {
  if (status === 'SIGNED') {
    return (
      <Badge tone="navy" icon={<FileCheck size={14} />}>
        Signed record
      </Badge>
    )
  }
  return (
    <Badge tone="neutral" icon={<ClipboardList size={14} />}>
      Open
    </Badge>
  )
}

export default function DashboardPage() {
  const [samples, setSamples] = useState<Sample[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listSamples(15)
      .then((rows) => {
        if (!cancelled) setSamples(rows)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load samples.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <>
      <PageHeader
        title="Field dashboard"
        subtitle="Samples you can continue testing, or start a new field test. Every finalised result becomes an append-only, signed record."
        actions={
          <Link className="fp-btn fp-btn--primary fp-btn--md" to="/new-test">
            <Plus size={18} aria-hidden="true" />
            New test
          </Link>
        }
      />

      {error ? (
        <Alert tone="danger" title="Could not load samples">
          {error}
        </Alert>
      ) : null}

      <Card>
        <CardBody>
          {samples === null && !error ? (
            <LoadingBlock label="Loading samples…" />
          ) : samples && samples.length === 0 ? (
            <EmptyState
              title="No samples yet"
              message="Start your first field test to create a sample, record reactions and sign the result."
              actions={
                <Link className="fp-btn fp-btn--primary fp-btn--md" to="/new-test">
                  <Plus size={18} aria-hidden="true" />
                  New test
                </Link>
              }
            />
          ) : samples ? (
            <>
              <ul className="fp-dash-list">
                {samples.map((sample) => (
                  <li key={sample.id} className="fp-dash-item">
                    <span className="fp-dash-item__main">
                      <span className="fp-dash-item__code">{sample.sample_code}</span>
                      <span className="fp-dash-item__meta">
                        {sample.appearance}
                        {sample.colour ? ` · ${sample.colour}` : ''} ·{' '}
                        {sample.tests.length} test{sample.tests.length === 1 ? '' : 's'} ·{' '}
                        {new Date(
                          sample.created_at.endsWith('Z')
                            ? sample.created_at
                            : `${sample.created_at}Z`,
                        ).toLocaleString()}
                      </span>
                    </span>
                    <span className="fp-dash-actions">
                      {sampleStatusBadge(sample.status)}
                      <Link
                        className="fp-btn fp-btn--secondary fp-btn--sm"
                        to={`/samples/${sample.id}/analysis`}
                      >
                        Open
                      </Link>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </CardBody>
      </Card>
    </>
  )
}

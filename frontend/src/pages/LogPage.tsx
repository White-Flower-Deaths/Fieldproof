import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Download,
  FileCheck2,
  RefreshCw,
  Search,
  ShieldCheck,
  ShieldQuestion,
  TriangleAlert,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  Disclaimer,
  EmptyState,
  KeyValue,
  PageHeader,
  Skeleton,
  StatusPill,
} from '../components'
import { api } from '../lib/api'
import type { RecordDetail, RecordListResponse } from '../lib/api'
import { RESULT_STATUSES } from '../lib/constants'
import { statusMeta } from '../lib/status'
import './pages.css'

type SortBy = 'server_timestamp' | 'status' | 'sample_code' | 'record_hash'
type VerifState = 'checking' | 'PASS' | 'FAIL' | 'error'
type VerifMap = Record<string, VerifState>

const PAGE_SIZE = 10
const SORTABLE: { key: SortBy; label: string }[] = [
  { key: 'status', label: 'Status' },
  { key: 'sample_code', label: 'Sample' },
  { key: 'server_timestamp', label: 'Time' },
]

function fmtTime(iso: string): string {
  const value = iso.endsWith('Z') ? iso : `${iso}Z`
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return iso
  // Compact form keeps the five-column table inside the split pane.
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })}`
}

function VerifiedBadge({ state }: { state: VerifState | undefined }) {
  if (state === 'checking') {
    return (
      <Badge tone="neutral" icon={<ShieldQuestion size={14} />}>
        Checking…
      </Badge>
    )
  }
  if (state === 'PASS') {
    return (
      <Badge tone="success" icon={<ShieldCheck size={14} />}>
        Verified
      </Badge>
    )
  }
  if (state === 'FAIL') {
    return (
      <Badge tone="danger" icon={<TriangleAlert size={14} />}>
        Not verified
      </Badge>
    )
  }
  if (state === 'error') {
    return (
      <Badge tone="neutral" icon={<TriangleAlert size={14} />}>
        Check unavailable
      </Badge>
    )
  }
  return (
    <Badge tone="neutral" icon={<ShieldQuestion size={14} />}>
      Not checked
    </Badge>
  )
}

function VerifyChecks({ detail }: { detail: RecordDetail }) {
  const verification = detail.verification
  return (
    <section className="fp-detail-section" aria-label="Verification status">
      <h3 className="fp-detail-section__title">Verification status</h3>
      <div className="fp-detail-verify-head">
        <Badge
          tone={verification.overall === 'PASS' ? 'success' : 'danger'}
          size="lg"
          icon={
            verification.overall === 'PASS' ? (
              <ShieldCheck size={16} />
            ) : (
              <TriangleAlert size={16} />
            )
          }
        >
          {verification.overall === 'PASS' ? 'Verification passed' : 'Verification failed'}
        </Badge>
        <span className="fp-detail-muted">Checks run against this server's registry.</span>
      </div>
      <ul className="fp-checklist">
        {verification.checks.map((check) => (
          <li
            key={check.id}
            className={`fp-checklist__item is-${check.status === 'PASS' ? 'pass' : check.status === 'FAIL' ? 'fail' : 'skip'}`}
          >
            <span className="fp-checklist__icon" aria-hidden="true">
              {check.status === 'PASS' ? '✓' : check.status === 'FAIL' ? '✗' : '–'}
            </span>
            <span className="fp-checklist__body">
              <span className="fp-checklist__label">{check.label}</span>
              <span className="fp-checklist__detail">{check.detail}</span>
            </span>
            <Badge
              tone={check.status === 'PASS' ? 'success' : check.status === 'FAIL' ? 'danger' : 'neutral'}
              icon={
                check.status === 'PASS' ? (
                  <ShieldCheck size={14} />
                ) : check.status === 'FAIL' ? (
                  <TriangleAlert size={14} />
                ) : (
                  <ShieldQuestion size={14} />
                )
              }
            >
              {check.status}
            </Badge>
          </li>
        ))}
      </ul>
      {verification.warnings.length > 0 ? (
        <Alert tone="warning" title="Warnings">
          <ul className="fp-detail-warnings">
            {verification.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Alert>
      ) : null}
    </section>
  )
}

function RecordDetailView({
  detail,
  loading,
  error,
  onRetry,
}: {
  detail: RecordDetail | null
  loading: boolean
  error: string | null
  onRetry: () => void
}) {
  if (loading) {
    return (
      <Card className="fp-log-detail">
        <CardBody>
          <div className="fp-detail-loading" role="status">
            <Skeleton width="60%" height={22} />
            <Skeleton width="100%" height={70} />
            <Skeleton width="100%" height={140} />
            <Skeleton width="100%" height={90} />
          </div>
        </CardBody>
      </Card>
    )
  }
  if (error) {
    return (
      <Card className="fp-log-detail">
        <CardBody>
          <Alert tone="danger" title="Could not load the record">
            {error}
            <div className="fp-detail-actions">
              <Button variant="secondary" size="sm" iconBefore={<RefreshCw size={16} />} onClick={onRetry}>
                Retry
              </Button>
            </div>
          </Alert>
        </CardBody>
      </Card>
    )
  }
  if (!detail) {
    return (
      <Card className="fp-log-detail">
        <CardBody>
          <EmptyState
            icon={<FileCheck2 size={36} />}
            title="Select a record"
            message="Choose a row to inspect its tests, analysis, hash, signature and verification status."
          />
        </CardBody>
      </Card>
    )
  }

  const summary = detail.summary
  const analysis = detail.analysis
  const signature = detail.bundle.signature

  return (
    <Card className="fp-log-detail">
      <CardBody>
        <header className="fp-detail-head">
          <div className="fp-detail-head__row">
            <StatusPill status={summary.status} size="lg" />
            <span className="fp-detail-sample">{summary.sample_code}</span>
          </div>
          <span className="fp-hash" title={summary.id}>
            {summary.id}
          </span>
        </header>

        <section className="fp-detail-section" aria-label="Record summary">
          <h3 className="fp-detail-section__title">Summary</h3>
          <KeyValue
            items={[
              { label: 'Recorded (server time)', value: fmtTime(summary.server_timestamp) },
              { label: 'Operator', value: summary.operator_username ?? '—' },
              { label: 'Kits', value: summary.kit_codes.join(', ') || '—' },
              { label: 'Top match', value: summary.top_substance_name ?? '—' },
              { label: 'Engine', value: summary.engine_version },
              ...(detail.sample
                ? [
                    {
                      label: 'Sample appearance',
                      value: [
                        detail.sample.appearance,
                        detail.sample.colour,
                        detail.sample.approximate_weight,
                      ]
                        .filter(Boolean)
                        .join(' · '),
                    },
                  ]
                : []),
            ]}
          />
        </section>

        <section className="fp-detail-section" aria-label="Tests">
          <h3 className="fp-detail-section__title">
            Tests <span className="fp-detail-count">{detail.tests.length}</span>
          </h3>
          {detail.tests.length === 0 ? (
            <p className="fp-detail-muted">No tests recorded.</p>
          ) : (
            <ul className="fp-detail-tests">
              {detail.tests.map((test) => (
                <li key={test.test_id} className="fp-detail-test">
                  <span className="fp-detail-test__main">
                    <span className="fp-detail-test__kit">
                      {test.kit_name ?? test.kit_code ?? test.test_type}
                    </span>
                    <span className="fp-detail-test__outcome">
                      {test.outcome_label ?? test.outcome_code ?? '—'}
                    </span>
                  </span>
                  <span className="fp-detail-test__meta">
                    <Badge tone="neutral" mono>
                      {test.test_id.slice(0, 8)}
                    </Badge>
                    {test.kit_batch ? (
                      <Badge tone="info" mono>
                        batch {test.kit_batch}
                      </Badge>
                    ) : null}
                    {test.is_override ? <Badge tone="warning">Overridden</Badge> : null}
                    {test.entered_at ? (
                      <span className="fp-detail-muted">{fmtTime(test.entered_at)}</span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {analysis ? (
          <section className="fp-detail-section" aria-label="Analysis">
            <h3 className="fp-detail-section__title">Analysis</h3>
            <div className="fp-detail-analysis">
              <StatusPill status={analysis.status} />
              <span className="fp-detail-topmatch">
                Top match:{' '}
                <strong>
                  {analysis.top_match
                    ? `${analysis.top_match.name} (${Math.round(analysis.top_match.percentage)}%)`
                    : 'none'}
                </strong>
              </span>
            </div>
            <p className="fp-detail-muted">
              {analysis.counts.tests_entered} test{analysis.counts.tests_entered === 1 ? '' : 's'} ·{' '}
              {analysis.counts.informative} informative
            </p>
            <Disclaimer compact />
          </section>
        ) : null}

        <section className="fp-detail-section" aria-label="Hash and signature">
          <h3 className="fp-detail-section__title">Hash &amp; signature</h3>
          <KeyValue
            items={[
              {
                label: 'Record hash',
                value: <span className="fp-hash">{summary.record_hash}</span>,
              },
              {
                label: 'Previous hash',
                value: summary.previous_record_hash ? (
                  <span className="fp-hash">{summary.previous_record_hash}</span>
                ) : (
                  <span className="fp-detail-muted">—</span>
                ),
              },
              { label: 'Public key ID', value: summary.public_key_id ?? '—' },
              {
                label: 'Signature (base64 DER)',
                value: signature ? (
                  <span className="fp-hash">{signature}</span>
                ) : (
                  <span className="fp-detail-muted">—</span>
                ),
              },
            ]}
          />
        </section>

        <VerifyChecks detail={detail} />
      </CardBody>
    </Card>
  )
}

export default function LogPage() {
  const [q, setQ] = useState('')
  const [appliedQ, setAppliedQ] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [kitFilter, setKitFilter] = useState<string | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState<SortBy>('server_timestamp')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  // List data + errors are stored together with the request key they belong
  // to, so changing a filter derives a fresh loading/error state during render
  // instead of calling setState synchronously from an effect.
  const [data, setData] = useState<{ key: string; value: RecordListResponse } | null>(null)
  const [loadError, setLoadError] = useState<{ key: string; message: string } | null>(null)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailState, setDetailState] = useState<{
    id: string
    loading: boolean
    detail: RecordDetail | null
    error: string | null
  } | null>(null)

  const [kits, setKits] = useState<string[]>([])
  const [verif, setVerif] = useState<VerifMap>({})
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const verifRef = useRef<VerifMap>({})

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedQ(q.trim())
      setPage(1)
    }, 350)
    return () => window.clearTimeout(timer)
  }, [q])

  useEffect(() => {
    api
      .kits()
      .then((rows) => setKits(rows.map((kit) => kit.code)))
      .catch(() => setKits([]))
  }, [])

  const filtersActive = Boolean(
    appliedQ || statusFilter || kitFilter || dateFrom || dateTo,
  )

  const fetchList = useMemo(
    () => ({
      q: appliedQ || undefined,
      status_filter: statusFilter ?? undefined,
      kit: kitFilter ?? undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
      page_size: PAGE_SIZE,
      sort_by: sortBy,
      sort_dir: sortDir,
    }),
    [appliedQ, statusFilter, kitFilter, dateFrom, dateTo, page, sortBy, sortDir],
  )
  const fetchKey = `${JSON.stringify(fetchList)}#${reloadToken}`
  const listData = data && data.key === fetchKey ? data.value : null
  const loading = listData === null
  const error = loadError && loadError.key === fetchKey ? loadError.message : null

  useEffect(() => {
    let cancelled = false
    api
      .listRecordsQuery(fetchList)
      .then((result) => {
        if (cancelled) return
        setData({ key: fetchKey, value: result })
        // Per-row verified badge comes from the record's own verification run.
        // Results are cached so revisiting a page does not refetch them.
        result.items.forEach((item) => {
          if (verifRef.current[item.id]) return
          verifRef.current = { ...verifRef.current, [item.id]: 'checking' }
          setVerif(verifRef.current)
          api
            .getRecord(item.id)
            .then((detailRow) => {
              if (cancelled) return
              verifRef.current = {
                ...verifRef.current,
                [item.id]: detailRow.verification.overall === 'PASS' ? 'PASS' : 'FAIL',
              }
              setVerif(verifRef.current)
            })
            .catch(() => {
              if (cancelled) return
              verifRef.current = { ...verifRef.current, [item.id]: 'error' }
              setVerif(verifRef.current)
            })
        })
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setLoadError({
            key: fetchKey,
            message: err instanceof Error ? err.message : 'Could not load records.',
          })
      })
    return () => {
      cancelled = true
    }
  }, [fetchList, fetchKey, reloadToken])

  // Retry path (event handler): marks the pane as loading straight away.
  const fetchDetail = useCallback((recordId: string) => {
    setDetailState({ id: recordId, loading: true, detail: null, error: null })
    api
      .getRecord(recordId)
      .then((row) => {
        setDetailState({ id: recordId, loading: false, detail: row, error: null })
        verifRef.current = {
          ...verifRef.current,
          [recordId]: row.verification.overall === 'PASS' ? 'PASS' : 'FAIL',
        }
        setVerif(verifRef.current)
      })
      .catch((err: unknown) => {
        setDetailState({
          id: recordId,
          loading: false,
          detail: null,
          error: err instanceof Error ? err.message : 'Could not load the record.',
        })
      })
  }, [])

  // Selection path: the pane derives "loading" while no state exists for the
  // selected id; state is only written from the async callbacks below.
  useEffect(() => {
    if (!selectedId) return
    let cancelled = false
    api
      .getRecord(selectedId)
      .then((row) => {
        if (cancelled) return
        setDetailState({ id: selectedId, loading: false, detail: row, error: null })
        verifRef.current = {
          ...verifRef.current,
          [selectedId]: row.verification.overall === 'PASS' ? 'PASS' : 'FAIL',
        }
        setVerif(verifRef.current)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setDetailState({
          id: selectedId,
          loading: false,
          detail: null,
          error: err instanceof Error ? err.message : 'Could not load the record.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const activeDetail = detailState && detailState.id === selectedId ? detailState : null
  const detail = activeDetail?.detail ?? null
  const detailError = activeDetail?.error ?? null
  const detailLoading = Boolean(selectedId) && (!activeDetail || activeDetail.loading)

  const toggleSort = (key: SortBy) => {
    if (sortBy === key) setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'))
    else {
      setSortBy(key)
      setSortDir(key === 'server_timestamp' ? 'desc' : 'asc')
    }
  }

  const clearFilters = () => {
    setQ('')
    setAppliedQ('')
    setStatusFilter(null)
    setKitFilter(null)
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const onExport = () => {
    setExporting(true)
    setExportError(null)
    api
      .exportRecordsCsv(fetchList)
      .catch((err: unknown) =>
        setExportError(err instanceof Error ? err.message : 'CSV export failed.'),
      )
      .finally(() => setExporting(false))
  }

  const totalPages = listData
    ? Math.max(1, Math.ceil(listData.total / listData.page_size))
    : 1
  const items = listData?.items ?? []
  const hasFilters = filtersActive

  const renderSortIcon = (key: SortBy) =>
    sortBy === key ? (
      sortDir === 'asc' ? (
        <ArrowUp size={14} aria-hidden="true" />
      ) : (
        <ArrowDown size={14} aria-hidden="true" />
      )
    ) : (
      <ArrowDown size={14} aria-hidden="true" className="fp-sort-icon--idle" />
    )

  return (
    <>
      <PageHeader
        title="Records log"
        subtitle="Search and inspect append-only signed records. Every row can be opened for tests, analysis, hash, signature and verification status."
        actions={
          <Button
            variant="secondary"
            size="md"
            iconBefore={<Download size={18} />}
            onClick={onExport}
            loading={exporting}
          >
            Export CSV
          </Button>
        }
      />

      <div className="fp-log-toolbar">
        <div className="fp-log-search">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Record ID or sample ID"
            aria-label="Search records by record ID or sample ID"
            className="fp-log-search__input"
          />
        </div>

        <div className="fp-filters" role="group" aria-label="Filter by status">
          <button
            type="button"
            className={`fp-chip${statusFilter === null ? ' is-active' : ''}`}
            aria-pressed={statusFilter === null}
            onClick={() => {
              setStatusFilter(null)
              setPage(1)
            }}
          >
            All statuses
          </button>
          {RESULT_STATUSES.map((status) => (
            <button
              key={status}
              type="button"
              className={`fp-chip${statusFilter === status ? ' is-active' : ''}`}
              aria-pressed={statusFilter === status}
              onClick={() => {
                setStatusFilter((current) => (current === status ? null : status))
                setPage(1)
              }}
            >
              {statusMeta(status).label}
            </button>
          ))}
        </div>

        {kits.length > 0 ? (
          <div className="fp-filters" role="group" aria-label="Filter by kit">
            <button
              type="button"
              className={`fp-chip${kitFilter === null ? ' is-active' : ''}`}
              aria-pressed={kitFilter === null}
              onClick={() => {
                setKitFilter(null)
                setPage(1)
              }}
            >
              All kits
            </button>
            {kits.map((kitCode) => (
              <button
                key={kitCode}
                type="button"
                className={`fp-chip fp-chip--mono${kitFilter === kitCode ? ' is-active' : ''}`}
                aria-pressed={kitFilter === kitCode}
                onClick={() => {
                  setKitFilter((current) => (current === kitCode ? null : kitCode))
                  setPage(1)
                }}
              >
                {kitCode}
              </button>
            ))}
          </div>
        ) : null}

        <div className="fp-filters fp-filters--date">
          <label className="fp-datefilter">
            <span>From</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value)
                setPage(1)
              }}
              aria-label="Records from date"
            />
          </label>
          <label className="fp-datefilter">
            <span>To</span>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value)
                setPage(1)
              }}
              aria-label="Records up to date"
            />
          </label>
          {hasFilters ? (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear filters
            </Button>
          ) : null}
        </div>
      </div>

      {exportError ? (
        <Alert tone="danger" title="CSV export failed">
          {exportError}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Could not load records">
          {error}
          <div className="fp-detail-actions">
            <Button
              variant="secondary"
              size="sm"
              iconBefore={<RefreshCw size={16} />}
              onClick={() => setReloadToken((token) => token + 1)}
            >
              Retry
            </Button>
          </div>
        </Alert>
      ) : null}

      <div className={`fp-log-split${selectedId ? ' has-detail' : ''}`}>
        <Card className="fp-log-list">
          <CardBody>
            {loading && !error ? (
              <div className="fp-log-skeleton" aria-hidden="true">
                {Array.from({ length: 5 }, (_, index) => (
                  <div key={index} className="fp-log-skeleton__row">
                    <Skeleton width="22%" height={34} radius="var(--radius-md)" />
                    <Skeleton width="30%" height={34} radius="var(--radius-md)" />
                    <Skeleton width="24%" height={34} radius="var(--radius-md)" />
                    <Skeleton width="16%" height={34} radius="var(--radius-md)" />
                  </div>
                ))}
                <span className="sr-only">Loading records…</span>
              </div>
            ) : error ? null : !listData || (listData.total === 0 && !hasFilters) ? (
              <EmptyState
                icon={<FileCheck2 size={36} />}
                title="No records yet"
                message="Finalise a field test in the wizard to create your first signed, append-only record."
                actions={
                  <Link className="fp-btn fp-btn--primary fp-btn--md" to="/new-test">
                    Start a test
                  </Link>
                }
              />
            ) : listData.total === 0 ? (
              <EmptyState
                icon={<Search size={36} />}
                title="No records match"
                message="No record matches the current search and filters."
                actions={
                  <Button variant="secondary" size="md" onClick={clearFilters}>
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <div className={loading ? 'fp-log-content is-loading' : 'fp-log-content'}>
                {/* Desktop: sortable table */}
                <div className="fp-log-table">
                  <div className="fp-table-wrap">
                    <table className="fp-table">
                    <caption className="sr-only">Signed records</caption>
                    <thead>
                      <tr>
                        {SORTABLE.map((column) => (
                          <th
                            key={column.key}
                            scope="col"
                            aria-sort={
                              sortBy === column.key
                                ? sortDir === 'asc'
                                  ? 'ascending'
                                  : 'descending'
                                : 'none'
                            }
                          >
                            <button
                              type="button"
                              className="fp-table__sort"
                              onClick={() => toggleSort(column.key)}
                            >
                              {column.label}
                              {renderSortIcon(column.key)}
                            </button>
                          </th>
                        ))}
                        <th scope="col">Verified</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((row) => (
                        <tr
                          key={row.id}
                          className={selectedId === row.id ? 'is-selected' : undefined}
                          tabIndex={0}
                          aria-label={`Open record for sample ${row.sample_code}`}
                          onClick={() => setSelectedId(row.id)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              setSelectedId(row.id)
                            }
                          }}
                        >
                          <td>
                            <StatusPill status={row.status} />
                          </td>
                          <td>
                            <span className="fp-log-sample">{row.sample_code}</span>
                          </td>
                          <td>{fmtTime(row.server_timestamp)}</td>
                          <td>
                            <VerifiedBadge state={verif[row.id]} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                </div>

                {/* Mobile: card list */}
                <ul className="fp-log-cards">
                  {items.map((row) => (
                    <li key={row.id}>
                      <button
                        type="button"
                        className={`fp-log-card${selectedId === row.id ? ' is-selected' : ''}`}
                        onClick={() => setSelectedId(row.id)}
                        aria-label={`Open record for sample ${row.sample_code}`}
                      >
                        <span className="fp-log-card__row">
                          <StatusPill status={row.status} />
                          <VerifiedBadge state={verif[row.id]} />
                        </span>
                        <span className="fp-log-card__row">
                          <span className="fp-log-sample">{row.sample_code}</span>
                          <span className="fp-detail-muted">{fmtTime(row.server_timestamp)}</span>
                        </span>
                        <span className="fp-log-card__row">
                          <span className="fp-log-recordid fp-hash">{row.id}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>

                <nav className="fp-log-pager" aria-label="Records pagination">
                  <Button
                    variant="secondary"
                    size="sm"
                    iconBefore={<ChevronLeft size={16} />}
                    disabled={page <= 1}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                  >
                    Previous
                  </Button>
                  <span className="fp-log-pager__info" aria-live="polite">
                    Page {page} of {totalPages} · {listData.total} record
                    {listData.total === 1 ? '' : 's'}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    iconAfter={<ChevronRight size={16} />}
                    disabled={page >= totalPages}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Next
                  </Button>
                </nav>
              </div>
            )}
          </CardBody>
        </Card>

        <RecordDetailView
          detail={detail}
          loading={detailLoading}
          error={detailError}
          onRetry={() => selectedId && fetchDetail(selectedId)}
        />
      </div>
    </>
  )
}

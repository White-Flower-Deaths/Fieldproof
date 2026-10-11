/** Typed fetch client for the FieldProof API (no mock data - every call hits
 *  the real backend through the Vite /api proxy). */

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const TOKEN_KEY = 'fieldproof.token'

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function storeToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable */
  }
}

export type AuthUser = {
  id: string
  username: string
  full_name: string
  badge_number: string | null
  role: 'OFFICER' | 'LAB' | 'ADMIN'
  agency: string | null
  is_active: boolean
  last_login_at: string | null
}

export type TokenResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export type Meta = {
  app_name: string
  environment: string
  engine_version: string
  disclaimer: string
  concentration_note: string
  roles: string[]
  appearance_options: string[]
  test_types: string[]
  result_statuses: string[]
  demo_mode_default: boolean
}

export type KitOutcome = {
  code: string
  label: string
  hex: string | null
  interpretation: string | null
  sort_order: number
}

export type Kit = {
  code: string
  name: string
  test_type: string
  manufacturer: string | null
  description: string | null
  instructions: string | null
  reaction_time_seconds: number | null
  requires_photo: boolean
  is_demo: boolean
  source_citation: string
  outcomes: KitOutcome[]
}

export type SampleTest = {
  id: string
  test_type: string
  kit_code: string | null
  kit_name: string | null
  kit_batch: string | null
  outcome_code: string | null
  outcome_label: string | null
  input_json: Record<string, unknown>
  time_since_reaction_seconds: number | null
  image_sha256: string | null
  source: string
  is_override: boolean
  override_reason: string | null
  overridden_outcome_code: string | null
}

export type Sample = {
  id: string
  sample_code: string
  operator_id: string
  operator_username: string | null
  appearance: string
  colour: string | null
  approximate_weight: string | null
  notes: string | null
  photo_sha256: string | null
  gps_lat: number | null
  gps_lon: number | null
  gps_accuracy_m: number | null
  gps_mock_location: boolean
  device_timestamp: string | null
  status: string
  created_at: string
  updated_at: string
  tests: SampleTest[]
}

export type SampleCreate = {
  appearance: string
  colour?: string | null
  approximate_weight?: string | null
  notes?: string | null
  gps_lat?: number | null
  gps_lon?: number | null
  gps_accuracy_m?: number | null
}

export type TestCreate = {
  test_type: string
  kit_code?: string
  kit_batch?: string
  outcome_code?: string
  time_since_reaction_seconds?: number
  image_sha256?: string
  input?: Record<string, unknown>
  source?: 'MANUAL' | 'CAMERA'
  calibration?: Record<string, unknown> | null
  reading?: Record<string, unknown> | null
  is_override?: boolean
  override_reason?: string
  overridden_outcome_code?: string
}

/** GET /api/reference-card — printable card layout + known patch values
 *  (also used by the capture overlay). */
export type ReferenceCard = {
  name: string
  version: number
  card: { width_mm: number; height_mm: number; canonical_px_per_mm: number }
  aruco: {
    dictionary: string
    marker_size_mm: number
    markers: { id: number; corner: string; x_mm: number; y_mm: number }[]
  }
  patches: {
    code: string
    label: string
    hex: string
    lab: number[]
    x_mm: number
    y_mm: number
    w_mm: number
    h_mm: number
  }[]
  source_citation: string
}

/** POST /api/images/analyze — one quality gate (icon+text in the UI). */
export type QualityGate = {
  id: string
  label: string
  passed: boolean
  value: number | null
  threshold: string
  message: string
}

/** Reference patch sampled on the card: measured vs expected colour. */
export type CalibrationPatch = {
  code: string
  label: string
  expected_hex: string
  measured_hex: string
  expected_lab: number[]
  measured_lab: number[]
  delta_e: number
}

export type MatchOutcome = {
  code: string
  label: string
  ref_lab: number[]
  ref_hex: string | null
  delta_e: number
  interpretation: string | null
  cross_reactions: string[]
}

export type ImageMatch = {
  outcome: MatchOutcome | null
  delta_e: number | null
  second_outcome: MatchOutcome | null
  second_delta_e: number | null
  margin: number | null
  status: 'MATCH' | 'INCONCLUSIVE'
  reasons: string[]
  ranked: MatchOutcome[]
  thresholds: { max_delta_e: number; min_margin: number }
}

export type MeasuredColour = { hex: string; lab: number[]; rgb: number[] }

export type ImageReport = {
  status: 'OK' | 'INCONCLUSIVE'
  kit_code: string | null
  kit_name: string | null
  image: { width: number; height: number }
  roi: { x0: number; y0: number; x1: number; y1: number } | null
  quality: { passed: boolean; gates: QualityGate[] }
  calibration: {
    detected: boolean
    detection: { detected: boolean; marker_ids: number[]; dictionary: string; message: string }
    matrix: number[][] | null
    patches: CalibrationPatch[]
    rms_delta_e: number | null
    raw_rms_delta_e?: number | null
  }
  measured_colour: MeasuredColour | null
  corrected_colour: MeasuredColour | null
  match: ImageMatch | null
  reasons: string[]
  concentration?: string
  disclaimer?: string
  time_since_reaction_seconds?: number | null
}

export type ImageUploadResult = {
  sha256: string
  filename: string
  size_bytes: number
  content_type: string | null
}

export type RankedCandidate = {
  substance_id: string
  code: string
  name: string
  score: number
  percentage: number
}

export type EvidenceRow = {
  ref: string
  test_type: string
  kit_code: string
  kit_name: string
  outcome_label: string
  informative: boolean
  supports: boolean | null
  likelihood: number | null
  note: string
  cross_reactions: string[]
  source_citation?: string | null
}

export type ConfidenceBand = {
  low: number
  high: number
  width: number
  centre: number
  evidence_bits: number
  label: string
  method: string
}

export type Analysis = {
  engine_version: string
  computed_at: string
  status: string
  top_match: { substance_id: string; code: string; name: string; percentage: number } | null
  alternatives: RankedCandidate[]
  ranked: RankedCandidate[]
  evidence: EvidenceRow[]
  supporting_refs: string[]
  contradicting_refs: string[]
  flags: string[]
  rule_notes: string[]
  cross_reactions: { kit_code: string; outcome_label: string; substances: string[] }[]
  concentration: string
  disclaimer: string
  explanation: string
  confidence?: ConfidenceBand | null
  counts: {
    tests_entered: number
    informative: number
    presumptive_informative: number
    inconclusive: number
    non_informative: number
    candidates: number
  }
  lab_confirmation: Record<string, unknown> | null
  lab_confirmed: boolean
}

export type TestCreateOut = { test: SampleTest; analysis: Analysis }

export type FinalizeResponse = {
  record: {
    id: string
    sample_id: string
    status: string
    record_hash: string
    previous_record_hash: string | null
    signature: string
    public_key_id: string | null
    server_timestamp: string
  }
  bundle: Record<string, unknown>
  analysis: Analysis
  disclaimer: string
}

export type RecordSummary = {
  id: string
  sample_id: string
  sample_code: string
  status: string
  operator_username: string | null
  kit_codes: string[]
  top_substance_name: string | null
  server_timestamp: string
  record_hash: string
  previous_record_hash: string | null
  public_key_id: string | null
  engine_version: string
  disclaimer: string
}

export type RecordListParams = {
  q?: string
  status_filter?: string
  kit?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_dir?: string
}

export type RecordListResponse = {
  total: number
  page: number
  page_size: number
  items: RecordSummary[]
}

export type VerifyCheck = {
  id: string
  label: string
  status: 'PASS' | 'FAIL' | 'SKIPPED'
  detail: string
}

export type VerifyResult = {
  overall: 'PASS' | 'FAIL'
  record_id: string | null
  status?: string | null
  sample_id?: string | null
  sample_code?: string | null
  server_timestamp?: string | null
  checks: VerifyCheck[]
  warnings: string[]
  disclaimer?: string | null
  concentration?: string | null
  concentration_note?: string | null
}

export type RecordDetailTest = {
  test_id: string
  test_type: string
  kit_code: string | null
  kit_name: string | null
  kit_batch: string | null
  outcome_code: string | null
  outcome_label: string | null
  time_since_reaction_seconds: number | null
  source: string
  entered_at: string | null
  is_override: boolean
}

export type RecordBundle = {
  format?: string
  record?: Record<string, unknown>
  canonical_json?: string
  record_hash?: string
  signature?: string | null
  public_key_id?: string | null
  public_key_pem?: string | null
  disclaimer?: string
  concentration_note?: string
}

export type RecordDetail = {
  summary: RecordSummary
  operator: {
    id: string
    username: string
    full_name: string | null
    badge_number: string | null
    role: string
  } | null
  sample: {
    id: string
    sample_code: string
    appearance: string
    colour: string | null
    approximate_weight: string | null
    notes: string | null
    gps_lat: number | null
    gps_lon: number | null
    gps_accuracy_m: number | null
  } | null
  tests: RecordDetailTest[]
  analysis: Analysis | null
  calibration: Record<string, unknown> | null
  bundle: RecordBundle
  verification: VerifyResult
  audit_trail: {
    id: string
    action: string
    actor: string | null
    role: string | null
    detail: Record<string, unknown> | null
    ip: string | null
    created_at: string
  }[]
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await authFetch(path, { ...init, headers })
  if (!response.ok) throw await apiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** fetch with the auth bearer attached and NO forced Content-Type (multipart,
 *  blob downloads and FormData need their own boundary headers). */
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = getStoredToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  try {
    return await fetch(path, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Cannot reach the FieldProof server. Check that the API is running.')
  }
}

async function apiError(response: Response): Promise<ApiError> {
  let detail = response.statusText || `Request failed (${response.status})`
  try {
    const data = (await response.json()) as { detail?: unknown }
    if (typeof data.detail === 'string') detail = data.detail
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(response.status, detail)
}

/** GET a file through the auth proxy and save it via a download link. */
export async function downloadText(path: string, filename: string): Promise<void> {
  const response = await authFetch(path)
  if (!response.ok) throw await apiError(response)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

/** GET a CSV export through the auth proxy and save it via a download link. */
export const downloadCsv = downloadText

export const api = {
  login: (username: string, password: string) =>
    request<TokenResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  register: (username: string, password: string) =>
    request<TokenResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<AuthUser>('/api/auth/me'),

  meta: () => request<Meta>('/api/meta'),

  kits: () => request<Kit[]>('/api/kits'),

  createSample: (payload: SampleCreate) =>
    request<Sample>('/api/samples', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listSamples: (limit = 20) => request<Sample[]>(`/api/samples?limit=${limit}`),

  getSample: (sampleId: string) => request<Sample>(`/api/samples/${sampleId}`),

  addTest: (sampleId: string, payload: TestCreate) =>
    request<TestCreateOut>(`/api/samples/${sampleId}/tests`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getAnalysis: (sampleId: string) => request<Analysis>(`/api/samples/${sampleId}/analysis`),

  finalize: (sampleId: string) =>
    request<FinalizeResponse>(`/api/samples/${sampleId}/finalize`, { method: 'POST' }),

  listRecords: (query: string, pageSize = 10) =>
    request<{ total: number; items: RecordSummary[] }>(
      `/api/records?q=${encodeURIComponent(query)}&page_size=${pageSize}`,
    ),

  listRecordsQuery: (params: RecordListParams) => {
    const search = new URLSearchParams()
    const append = (key: string, value: string | number | undefined) => {
      if (value !== undefined && value !== '') search.set(key, String(value))
    }
    append('q', params.q)
    append('status_filter', params.status_filter)
    append('kit', params.kit)
    append('date_from', params.date_from)
    append('date_to', params.date_to)
    append('page', params.page)
    append('page_size', params.page_size)
    append('sort_by', params.sort_by)
    append('sort_dir', params.sort_dir)
    return request<RecordListResponse>(`/api/records?${search.toString()}`)
  },

  getRecord: (recordId: string) => request<RecordDetail>(`/api/records/${recordId}`),

  /** Exact bytes of the signed bundle (the same file a user downloads for
   *  offline verification). GET /api/records/{id} wraps the bundle in a
   *  detail envelope, so use the export endpoint. JS JSON round-trips would
   *  change Python floats (1.0 -> 1) and corrupt the canonical hash - never
   *  re-serialise before uploading to /api/verify. */
  getRecordText: async (recordId: string): Promise<string> => {
    const response = await authFetch(`/api/records/${recordId}/export?format=json`)
    if (!response.ok) throw await apiError(response)
    return response.text()
  },

  exportRecordsCsv: (params: RecordListParams) => {
    const search = new URLSearchParams()
    const append = (key: string, value: string | number | undefined) => {
      if (value !== undefined && value !== '') search.set(key, String(value))
    }
    append('q', params.q)
    append('status_filter', params.status_filter)
    append('kit', params.kit)
    append('date_from', params.date_from)
    append('date_to', params.date_to)
    return downloadCsv(`/api/records/export?${search.toString()}`, 'fieldproof-records.csv')
  },

  verifyUpload: async (record: File, image?: File | null) => {
    const form = new FormData()
    form.append('record', record, record.name || 'record.json')
    if (image) form.append('image', image, image.name || 'image')
    const response = await authFetch('/api/verify', { method: 'POST', body: form })
    if (!response.ok) throw await apiError(response)
    return (await response.json()) as VerifyResult
  },

  /** GET /api/reference-card — patch table + layout for the capture overlay. */
  referenceCard: () => request<ReferenceCard>('/api/reference-card'),

  /** POST /api/images/analyze — quality gates + calibration + outcome match.
   *  `roi` is the normalised sample-pouch guide box drawn over the camera view. */
  analyzeImage: async (
    file: File,
    kitCode: string,
    opts: { roi?: { x: number; y: number; w: number; h: number }; timeSeconds?: number } = {},
  ) => {
    const form = new FormData()
    form.append('file', file, file.name || 'capture.jpg')
    form.append('kit_code', kitCode)
    if (opts.roi) form.append('roi', JSON.stringify(opts.roi))
    if (opts.timeSeconds) form.append('time_since_reaction_seconds', String(opts.timeSeconds))
    const response = await authFetch('/api/images/analyze', { method: 'POST', body: form })
    if (!response.ok) throw await apiError(response)
    return (await response.json()) as ImageReport
  },

  /** POST /api/images — store the photo unmodified, named by its SHA-256.
   *  The server computes the digest; use it as the test's image_sha256. */
  uploadImage: async (file: File) => {
    const form = new FormData()
    form.append('file', file, file.name || 'capture.jpg')
    const response = await authFetch('/api/images', { method: 'POST', body: form })
    if (!response.ok) throw await apiError(response)
    return (await response.json()) as ImageUploadResult
  },

  /** Exact bytes of the signed record bundle (same file /api/verify accepts). */
  downloadRecordJson: (recordId: string) =>
    downloadText(
      `/api/records/${recordId}/export?format=json`,
      `fieldproof-record-${recordId}.json`,
    ),
}

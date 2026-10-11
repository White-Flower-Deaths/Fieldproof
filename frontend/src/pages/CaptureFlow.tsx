import { useEffect, useRef, useState } from 'react'
import {
  ArrowLeft,
  Camera,
  CircleCheck,
  CircleX,
  Printer,
  RotateCcw,
  ScanLine,
  Upload,
} from 'lucide-react'
import { Alert, Badge, Button, Disclaimer, Spinner, TextAreaField } from '../components'
import { api, ApiError } from '../lib/api'
import type { ImageReport, Kit, ReferenceCard, TestCreateOut } from '../lib/api'
import './pages.css'

/**
 * Normalised sample-pouch guide box. The same rectangle is drawn over the
 * camera view AND sent as the analysis ROI, so the quality gates and the
 * colour reading always sample inside the pouch zone the officer sees.
 * It sits inside the pouch area of the demo scenes in docs/images.
 */
const POUCH_ROI = { x: 0.12, y: 0.31, w: 0.26, h: 0.38 }

function cameraMessage(err: unknown): string {
  const name =
    err instanceof DOMException ? err.name : (err as { name?: string } | null)?.name
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'Camera permission denied. Allow camera access for this site, or upload a photo instead.'
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'No camera is available on this device. Upload a photo instead.'
  }
  if (name === 'NotReadableError' || name === 'AbortError') {
    return 'The camera is being used by another app. Upload a photo instead.'
  }
  return `Camera unavailable${name ? ` (${name})` : ''}. Upload a photo instead.`
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError || err instanceof Error) return err.message
  return 'Something went wrong.'
}

/** Apply the server's 3x3 correction matrix to the preview (canvas). */
async function buildCorrectedUrl(
  src: string,
  matrix: number[][],
): Promise<string | null> {
  const image = await new Promise<HTMLImageElement | null>((resolve) => {
    const element = new Image()
    element.onload = () => resolve(element)
    element.onerror = () => resolve(null)
    element.src = src
  })
  if (!image || matrix.length !== 3 || matrix.some((row) => row.length !== 3)) return null
  const maxSide = 1400
  const scale = Math.min(
    1,
    maxSide / Math.max(image.naturalWidth, image.naturalHeight),
  )
  const width = Math.max(1, Math.round(image.naturalWidth * scale))
  const height = Math.max(1, Math.round(image.naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.drawImage(image, 0, 0, width, height)
  const pixels = ctx.getImageData(0, 0, width, height)
  const data = pixels.data
  const [[m00, m01, m02], [m10, m11, m12], [m20, m21, m22]] = matrix
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i]
    const g = data[i + 1]
    const b = data[i + 2]
    data[i] = Math.min(255, Math.max(0, Math.round(r * m00 + g * m01 + b * m02)))
    data[i + 1] = Math.min(255, Math.max(0, Math.round(r * m10 + g * m11 + b * m12)))
    data[i + 2] = Math.min(255, Math.max(0, Math.round(r * m20 + g * m21 + b * m22)))
  }
  ctx.putImageData(pixels, 0, 0)
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob((result) => resolve(result), 'image/jpeg', 0.92),
  )
  return blob ? URL.createObjectURL(blob) : null
}

type Stage = 'capture' | 'analysing' | 'report'

/**
 * Wizard Result-step camera panel: live rear-camera view with a pouch/card
 * placement guide (or file-upload fallback), POST /api/images/analyze with the
 * selected kit, quality-gate results as icon+text, then the calibration
 * screen (original vs corrected, patch swatches, delta E + margin) with
 * Accept / Override. Saving goes through POST /api/images then
 * POST /api/samples/{id}/tests — no mock data anywhere.
 */
export default function CaptureFlow({
  kit,
  sampleId,
  timeSeconds,
  kitBatch,
  onBack,
  onSaved,
}: {
  kit: Kit
  sampleId: string
  timeSeconds: number
  kitBatch: string
  onBack: () => void
  onSaved: (out: TestCreateOut) => void
}) {
  const [stage, setStage] = useState<Stage>('capture')
  const [camLive, setCamLive] = useState(false)
  const [camError, setCamError] = useState<string | null>(null)
  const [photo, setPhoto] = useState<{ file: File; url: string } | null>(null)
  const [report, setReport] = useState<ImageReport | null>(null)
  const [correctedUrl, setCorrectedUrl] = useState<string | null>(null)
  const [analyseError, setAnalyseError] = useState<string | null>(null)
  const [overrideCode, setOverrideCode] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [refCard, setRefCard] = useState<ReferenceCard | null>(null)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const urlsRef = useRef<string[]>([])

  const cameraSupported =
    typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)

  const trackUrl = (url: string): string => {
    urlsRef.current.push(url)
    return url
  }

  // Rear-facing camera; errors fall back to the upload panel with a message.
  useEffect(() => {
    if (!cameraSupported) return
    let cancelled = false
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) videoRef.current.srcObject = stream
        setCamLive(true)
        setCamError(null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setCamError(cameraMessage(err))
      })
    return () => {
      cancelled = true
      const stream = streamRef.current
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
    }
  }, [cameraSupported])

  // Re-attach the live stream when the viewport remounts (e.g. after Retake).
  useEffect(() => {
    const video = videoRef.current
    if (video && streamRef.current && video.srcObject !== streamRef.current) {
      video.srcObject = streamRef.current
    }
  })

  // Printable reference card: name/size shown next to the Print link.
  useEffect(() => {
    let alive = true
    api
      .referenceCard()
      .then((card) => {
        if (alive) setRefCard(card)
      })
      .catch(() => {
        /* overlay still works without the metadata */
      })
    return () => {
      alive = false
    }
  }, [])

  // Revoke object URLs created for previews.
  useEffect(
    () => () => {
      urlsRef.current.forEach((url) => URL.revokeObjectURL(url))
    },
    [],
  )

  const handleFile = (file: File | null | undefined) => {
    if (!file) return
    if (file.type && !file.type.startsWith('image/')) {
      setAnalyseError('That file is not an image. Choose a photo (JPEG or PNG).')
      return
    }
    if (photo) URL.revokeObjectURL(photo.url)
    setPhoto({ file, url: trackUrl(URL.createObjectURL(file)) })
    setReport(null)
    setCorrectedUrl(null)
    setAnalyseError(null)
    setSaveError(null)
  }

  const captureFrame = () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => {
        if (blob) handleFile(new File([blob], 'capture.jpg', { type: 'image/jpeg' }))
      },
      'image/jpeg',
      0.92,
    )
  }

  const analyse = async () => {
    if (!photo) return
    setStage('analysing')
    setAnalyseError(null)
    setSaveError(null)
    try {
      const res = await api.analyzeImage(photo.file, kit.code, {
        roi: POUCH_ROI,
        timeSeconds,
      })
      setReport(res)
      setOverrideCode('')
      setOverrideReason('')
      setStage('report')
      if (res.status === 'OK' && res.calibration.matrix) {
        void buildCorrectedUrl(photo.url, res.calibration.matrix)
          .then((url) => {
            if (url) setCorrectedUrl(trackUrl(url))
          })
          .catch(() => setCorrectedUrl(null))
      } else {
        setCorrectedUrl(null)
      }
    } catch (err) {
      setAnalyseError(errorMessage(err))
      setStage('capture')
    }
  }

  const retake = () => {
    if (photo) URL.revokeObjectURL(photo.url)
    setPhoto(null)
    setReport(null)
    setCorrectedUrl(null)
    setAnalyseError(null)
    setSaveError(null)
    setOverrideCode('')
    setOverrideReason('')
    setStage('capture')
  }

  const save = async (isOverride: boolean) => {
    if (!photo || !report || !report.match) return
    const detected = report.match.outcome
    const chosenCode = isOverride ? overrideCode : detected?.code
    const reason = overrideReason.trim()
    if (!chosenCode || (isOverride && !reason)) return
    setSaving(true)
    setSaveError(null)
    try {
      // 1) store the photo bytes -> authoritative SHA-256 from the server
      const upload = await api.uploadImage(photo.file)
      // 2) save the test entry: chosen outcome + image hash + calibration
      const out = await api.addTest(sampleId, {
        test_type: kit.test_type,
        kit_code: kit.code,
        ...(kitBatch.trim() ? { kit_batch: kitBatch.trim() } : {}),
        outcome_code: chosenCode,
        ...(timeSeconds ? { time_since_reaction_seconds: timeSeconds } : {}),
        image_sha256: upload.sha256,
        source: 'CAMERA',
        input: {
          analysis_status: report.status,
          image: report.image,
          roi: report.roi ?? POUCH_ROI,
          ...(refCard
            ? { reference_card: { name: refCard.name, version: refCard.version } }
            : {}),
        },
        calibration: report.calibration,
        reading: {
          status: report.status,
          quality_passed: report.quality.passed,
          detected_outcome_code: detected?.code ?? null,
          detected_outcome_label: detected?.label ?? null,
          delta_e: report.match.delta_e,
          second_delta_e: report.match.second_delta_e,
          margin: report.match.margin,
          match_status: report.match.status,
          measured_hex: report.measured_colour?.hex ?? null,
          corrected_hex: report.corrected_colour?.hex ?? null,
          reasons: report.reasons,
          ...(report.concentration ? { concentration: report.concentration } : {}),
        },
        ...(isOverride
          ? {
              is_override: true,
              override_reason: reason,
              ...(detected ? { overridden_outcome_code: detected.code } : {}),
            }
          : {}),
      })
      onSaved(out)
    } catch (err) {
      setSaveError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const match = report?.match ?? null
  const detected = match?.outcome ?? null
  const canAccept = Boolean(detected) && match?.status === 'MATCH'
  const otherOutcomes = kit.outcomes.filter(
    (outcome) => outcome.code !== detected?.code,
  )
  const cameraWarning =
    camError ??
    (!cameraSupported
      ? 'Camera API unavailable in this context (needs https or localhost). Upload a photo instead.'
      : null)

  return (
    <div className="fp-capture">
      {/* ---------------------------------------------------------- capture */}
      {stage === 'capture' ? (
        <>
          {cameraWarning ? (
            <Alert tone="warning" title="Camera unavailable">
              {cameraWarning}
            </Alert>
          ) : null}

          <div className="fp-capture__grid">
            <div className="fp-capture__viewport">
              {photo ? (
                <img
                  className="fp-capture__preview"
                  src={photo.url}
                  alt="Selected test photo"
                />
              ) : camLive && !camError ? (
                <>
                  <video
                    ref={videoRef}
                    className="fp-capture__video"
                    autoPlay
                    playsInline
                    muted
                  />
                  <div className="fp-capture__guide" aria-hidden="true">
                    <span className="fp-capture__zone fp-capture__zone--pouch">
                      <span className="fp-capture__zonelabel">Sample pouch</span>
                    </span>
                    <span className="fp-capture__zone fp-capture__zone--card">
                      <span className="fp-capture__zonelabel">Reference card</span>
                    </span>
                  </div>
                </>
              ) : (
                <div className="fp-capture__viewport-empty">
                  <ScanLine size={26} aria-hidden="true" />
                  <span>
                    {cameraSupported && !camError ? 'Starting camera…' : 'Camera not active'}
                  </span>
                </div>
              )}
            </div>

            <div className="fp-capture__side">
              <p className="fp-capture__instruct">
                Place the reacted test pouch inside the left guide box and lay the
                printed reference card flat in the right box. Keep the surface even
                and avoid shadows.
              </p>

              <a
                className="fp-printlink"
                href="/reference-card.pdf"
                target="_blank"
                rel="noreferrer"
              >
                <Printer size={16} aria-hidden="true" />
                Print reference card
              </a>
              {refCard ? (
                <span className="fp-capture__cardhint">
                  {refCard.name} v{refCard.version} · {refCard.card.width_mm}×
                  {refCard.card.height_mm} mm · {refCard.aruco.markers.length} markers
                </span>
              ) : null}

              {!photo && camLive && !camError ? (
                <Button
                  variant="primary"
                  onClick={captureFrame}
                  iconBefore={<Camera size={18} />}
                >
                  Capture photo
                </Button>
              ) : null}

              <div
                className={`fp-dropzone fp-capture__dropzone${photo ? ' has-file' : ''}`}
              >
                <input
                  id="capture-file"
                  type="file"
                  className="fp-dropzone__input"
                  accept="image/*"
                  onChange={(event) => {
                    handleFile(event.target.files?.item(0) ?? null)
                    event.target.value = ''
                  }}
                />
                <span className="fp-dropzone__icon" aria-hidden="true">
                  <Upload size={22} />
                </span>
                <span className="fp-dropzone__title">Upload a photo instead</span>
                <span className="fp-dropzone__hint">
                  JPEG or PNG — use this when the camera is unavailable or permission
                  was denied.
                </span>
                <label
                  className="fp-btn fp-btn--secondary fp-btn--sm fp-dropzone__cta"
                  htmlFor="capture-file"
                >
                  Choose photo
                </label>
              </div>

              {photo ? (
                <div className="fp-capture__actions">
                  <Button
                    variant="primary"
                    onClick={() => void analyse()}
                    iconBefore={<ScanLine size={18} />}
                  >
                    Analyse photo
                  </Button>
                  <Button variant="ghost" onClick={retake}>
                    Choose a different photo
                  </Button>
                </div>
              ) : (
                <div className="fp-capture__actions">
                  <Button
                    variant="secondary"
                    onClick={onBack}
                    iconBefore={<ArrowLeft size={16} />}
                  >
                    Back
                  </Button>
                </div>
              )}
            </div>
          </div>

          {analyseError ? (
            <Alert tone="danger" title="Analysis failed">
              {analyseError}
            </Alert>
          ) : null}
        </>
      ) : null}

      {/* -------------------------------------------------------- analysing */}
      {stage === 'analysing' ? (
        <div className="fp-capture__analysing" role="status">
          <Spinner />
          <span>Analysing photo — running quality gates and colour correction…</span>
        </div>
      ) : null}

      {/* ----------------------------------------------- report / calibration */}
      {stage === 'report' && report ? (
        <div className="fp-capture__report">
          <div className="fp-capture__shot">
            <img src={photo?.url} alt="Analysed test photo" />
            <div className="fp-capture__shot-meta">
              <Badge tone={report.status === 'OK' ? 'success' : 'danger'}>
                {report.status === 'OK' ? 'Photo accepted' : 'INCONCLUSIVE'}
              </Badge>
              <span className="fp-detail-muted">
                {kit.name} · {report.image.width}×{report.image.height}px
                {timeSeconds ? ` · read at ${timeSeconds} s` : ''}
              </span>
            </div>
          </div>

          {/* quality gates: icon + text, always */}
          <section className="fp-gates" aria-label="Photo quality gates">
            <h4 className="fp-detail-section__title">
              Quality gates —{' '}
              {report.quality.gates.filter((gate) => gate.passed).length}/
              {report.quality.gates.length} passed
            </h4>
            {report.quality.gates.map((gate) => (
              <div
                key={gate.id}
                className={`fp-gate${gate.passed ? ' is-pass' : ' is-fail'}`}
              >
                <span className="fp-gate__icon" aria-hidden="true">
                  {gate.passed ? <CircleCheck size={18} /> : <CircleX size={18} />}
                </span>
                <span className="fp-gate__body">
                  <span className="fp-gate__label">
                    {gate.label} — {gate.passed ? 'Passed' : 'Failed'}
                  </span>
                  <span className="fp-gate__msg">{gate.message}</span>
                  <span className="fp-gate__threshold">Threshold: {gate.threshold}</span>
                </span>
              </div>
            ))}
          </section>

          <Disclaimer />

          {report.status === 'INCONCLUSIVE' ? (
            <Alert tone="danger" title="INCONCLUSIVE — this photo cannot be read">
              <ul className="fp-capture__reasons">
                {report.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              <div className="fp-capture__actions">
                <Button
                  variant="primary"
                  onClick={retake}
                  iconBefore={<RotateCcw size={16} />}
                >
                  Retake
                </Button>
                <span className="fp-detail-muted">
                  Retake with better lighting, focus and framing — or upload a
                  different photo.
                </span>
              </div>
            </Alert>
          ) : (
            <>
              {/* --------------------------------- original vs corrected */}
              <section className="fp-calib" aria-label="Colour calibration">
                <h4 className="fp-detail-section__title">Calibration — original vs corrected</h4>
                <div className="fp-calib__imgs">
                  <figure className="fp-calib__img">
                    <img src={photo?.url} alt="Original captured photo" />
                    <figcaption>Original</figcaption>
                  </figure>
                  {correctedUrl ? (
                    <figure className="fp-calib__img">
                      <img src={correctedUrl} alt="Colour-corrected photo" />
                      <figcaption>Corrected (reference-card matrix)</figcaption>
                    </figure>
                  ) : (
                    <figure className="fp-calib__img fp-calib__img--empty">
                      <figcaption>
                        No colour correction applied — the reference card matrix was
                        not available.
                      </figcaption>
                    </figure>
                  )}
                </div>

                {/* reference patch swatches: measured vs expected */}
                <h4 className="fp-detail-section__title">
                  Reference patches — measured vs expected
                </h4>
                {report.calibration.patches.length === 0 ? (
                  <p className="fp-detail-muted">
                    No patches were sampled (reference card not detected).
                  </p>
                ) : (
                  <div className="fp-patches">
                    {report.calibration.patches.map((patch) => (
                      <div className="fp-patch" key={patch.code}>
                        <span className="fp-patch__swatches" aria-hidden="true">
                          <span
                            className="fp-patch__swatch"
                            style={{ background: patch.measured_hex }}
                          />
                          <span
                            className="fp-patch__swatch"
                            style={{ background: patch.expected_hex }}
                          />
                        </span>
                        <span className="fp-patch__label">{patch.label}</span>
                        <span className="fp-patch__de">ΔE {patch.delta_e}</span>
                      </div>
                    ))}
                  </div>
                )}
                <p className="fp-detail-muted">
                  Post-fit RMS ΔE {report.calibration.rms_delta_e ?? '—'}
                  {report.calibration.raw_rms_delta_e !== null &&
                  report.calibration.raw_rms_delta_e !== undefined
                    ? ` (before correction ${report.calibration.raw_rms_delta_e})`
                    : ''}
                  {' · '}measured swatch left, expected right.
                </p>

                {/* detected colour beside nearest reference outcomes */}
                <div className="fp-detect">
                  <div className="fp-detect__col">
                    <span className="fp-stat__label">Detected colour (corrected)</span>
                    <span className="fp-detect__row">
                      <span
                        className="fp-patch__swatch fp-patch__swatch--lg"
                        style={{
                          background: report.corrected_colour?.hex ?? 'transparent',
                        }}
                        aria-hidden="true"
                      />
                      <span className="fp-mono">
                        {report.corrected_colour?.hex ?? '—'}
                      </span>
                    </span>
                  </div>
                  <div className="fp-detect__col">
                    <span className="fp-stat__label">
                      Nearest reference outcome{match?.second_outcome ? 's' : ''}
                    </span>
                    {match?.outcome ? (
                      <span className="fp-detect__row">
                        <span
                          className="fp-patch__swatch"
                          style={{ background: match.outcome.ref_hex ?? 'transparent' }}
                          aria-hidden="true"
                        />
                        <span>
                          {match.outcome.label}
                          <span className="fp-detail-muted">
                            {' '}
                            · ΔE {match.delta_e}
                          </span>
                        </span>
                      </span>
                    ) : (
                      <span className="fp-detail-muted">No reference colours.</span>
                    )}
                    {match?.second_outcome ? (
                      <span className="fp-detect__row">
                        <span
                          className="fp-patch__swatch"
                          style={{
                            background: match.second_outcome.ref_hex ?? 'transparent',
                          }}
                          aria-hidden="true"
                        />
                        <span className="fp-detail-muted">
                          {match.second_outcome.label} · ΔE {match.second_delta_e} (2nd)
                        </span>
                      </span>
                    ) : null}
                  </div>
                  <div className="fp-detect__col">
                    <span className="fp-stat__label">Delta E & margin</span>
                    <span className="fp-detect__row">
                      ΔE {match?.delta_e ?? '—'}
                      {match?.margin !== null && match?.margin !== undefined
                        ? ` · margin ${match.margin}`
                        : ''}
                    </span>
                    <span className="fp-detail-muted">
                      Limits: ΔE ≤ {match?.thresholds.max_delta_e ?? '—'} · margin ≥{' '}
                      {match?.thresholds.min_margin ?? '—'}
                    </span>
                    {match ? (
                      <Badge tone={match.status === 'MATCH' ? 'success' : 'warning'}>
                        {match.status === 'MATCH'
                          ? `Colour matches ${detected?.label ?? 'the nearest outcome'}`
                          : 'Colour reading inconclusive'}
                      </Badge>
                    ) : null}
                  </div>
                </div>

                {match && match.status !== 'MATCH' ? (
                  <Alert tone="warning" title="Camera colour reading inconclusive">
                    <ul className="fp-capture__reasons">
                      {match.reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                    The camera cannot confirm an outcome from colour alone — record
                    the outcome you observed yourself using an override below.
                  </Alert>
                ) : null}
              </section>

              {/* --------------------------------------- accept / override */}
              <div className="fp-verdict">
                <div className="fp-verdict__accept">
                  <Button
                    variant="primary"
                    onClick={() => void save(false)}
                    disabled={!canAccept || saving}
                    loading={saving}
                  >
                    {detected ? `Accept ${detected.label} (camera)` : 'Accept detected'}
                  </Button>
                  <p className="fp-detail-muted">
                    {canAccept
                      ? 'Saves the detected outcome with this photo, its calibration and the image hash.'
                      : 'Accept is disabled while the colour reading is inconclusive — use an override with your own observation.'}
                  </p>
                </div>

                <fieldset className="fp-verdict__override">
                  <legend>Override — choose another outcome</legend>
                  {otherOutcomes.length === 0 ? (
                    <p className="fp-detail-muted">
                      No other outcomes are configured for this kit.
                    </p>
                  ) : (
                    <div className="fp-choices">
                      {otherOutcomes.map((outcome) => (
                        <label
                          key={outcome.code}
                          className={`fp-choice${overrideCode === outcome.code ? ' is-selected' : ''}`}
                        >
                          <input
                            type="radio"
                            name="capture-override"
                            className="fp-choice__radio"
                            checked={overrideCode === outcome.code}
                            disabled={saving}
                            onChange={() => setOverrideCode(outcome.code)}
                          />
                          <span
                            className="fp-choice__swatch"
                            aria-hidden="true"
                            style={{ background: outcome.hex ?? 'transparent' }}
                          />
                          <span className="fp-choice__body">
                            <span className="fp-choice__title">
                              {outcome.label}
                              <span className="fp-choice__code">{outcome.code}</span>
                            </span>
                          </span>
                        </label>
                      ))}
                    </div>
                  )}

                  {overrideCode ? (
                    <TextAreaField
                      label="Override reason"
                      required
                      maxLength={1000}
                      rows={3}
                      value={overrideReason}
                      placeholder="Why the camera reading does not match what you observed…"
                      hint="Required. Saved with the test entry and written to the audit trail."
                      onChange={(event) => setOverrideReason(event.target.value)}
                    />
                  ) : null}

                  <Button
                    variant="secondary"
                    onClick={() => void save(true)}
                    disabled={!overrideCode || !overrideReason.trim() || saving}
                    loading={saving && Boolean(overrideCode)}
                  >
                    Save override
                  </Button>
                </fieldset>
              </div>

              {saveError ? (
                <Alert tone="danger" title="Could not save the test">
                  {saveError}
                </Alert>
              ) : null}

              <div className="fp-capture__actions">
                <Button
                  variant="secondary"
                  onClick={retake}
                  disabled={saving}
                  iconBefore={<RotateCcw size={16} />}
                >
                  Retake photo
                </Button>
              </div>
            </>
          )}
        </div>
      ) : null}
    </div>
  )
}

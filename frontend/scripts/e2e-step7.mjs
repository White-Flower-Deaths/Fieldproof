/* Headless E2E for step 7: camera-capture result step (upload fallback in
 * headless), quality gates (INCONCLUSIVE on scene_dark, all-pass on
 * scene_ideal), calibration screen, override + accept save paths, and the
 * signed record screen (GPS, hash, signature, copy, record-JSON download).
 * Requires backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-step7.mjs   (SHOT_DIR=../docs/screenshots for shots)
 */
import { mkdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const BASE = 'http://localhost:5173'
// Short distinctive phrase from lib/constants DISCLAIMER (uppercased by the
// component's label styles, so match case-insensitively).
const DISC = /not a substitute for laboratory confirmatory testing/i
const CONCENTRATION = 'Concentration: not determinable from presumptive tests'
const SHOT_DIR = process.env.SHOT_DIR ?? ''
const IMAGES = fileURLToPath(new URL('../../docs/images/', import.meta.url))
if (SHOT_DIR) mkdirSync(SHOT_DIR, { recursive: true })

const results = []
const check = (name, ok, extra = '') => {
  results.push({ name, ok: !!ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? `  [${extra}]` : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const context = await browser.newContext({
  permissions: ['geolocation', 'clipboard-read', 'clipboard-write'],
  geolocation: { latitude: 51.5007, longitude: -0.1246, accuracy: 12 },
  viewport: { width: 390, height: 844 },
})
const page = await context.newPage()
page.setDefaultTimeout(15000)

const shot = async (name) => {
  if (SHOT_DIR) await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}
const stepTitle = (text) => page.locator('.fp-card__title', { hasText: text })

const apiGet = async (path) => {
  const token = await page.evaluate(() => localStorage.getItem('fieldproof.token'))
  const response = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error(`API ${path} -> ${response.status}`)
  return response.json()
}

const overflowPx = () =>
  page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )

try {
  // ------------------------------------------------------- login + metadata
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  await page.fill('input[name="username"]', 'officer1')
  await page.fill('input[name="password"]', 'FieldProof#Demo1')
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('login lands on dashboard', true)

  const pdf = await context.request.get(`${BASE}/reference-card.pdf`)
  check('reference-card.pdf served from /reference-card.pdf', pdf.status() === 200, `status ${pdf.status()}`)

  const kits = await apiGet('/api/kits')
  const marquis = kits.find((kit) => kit.code === 'MARQUIS')
  const overrideOutcome = marquis?.outcomes.find((o) => o.code !== 'PURPLE_BLACK')
  check(
    'MARQUIS kit has an override candidate outcome',
    Boolean(overrideOutcome),
    overrideOutcome?.code ?? 'none',
  )

  // ------------------------------------------------- sample step (GPS + continue)
  await page.click('a.fp-header__link[href="/new-test"]')
  await page.waitForSelector('.fp-stepper')
  await page.getByLabel('Colour').fill('Step7 E2E run')
  await page.getByLabel('Notes').fill('Camera capture E2E: gates, calibration, override, sign')
  await page.getByText('Location saved for this record').waitFor({ timeout: 10000 })
  const gpsText = (await page.locator('.fp-gps').innerText()).replace(/\s+/g, ' ')
  check(
    'gps captured with coordinates + accuracy',
    /-?\d+\.\d+.*±\d+ m/.test(gpsText),
    gpsText.slice(0, 90),
  )
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Choose the kit').waitFor()

  await page.locator('label.fp-choice', { hasText: 'MARQUIS' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()

  // -------------------------------------------------- camera capture surface
  const cameraModeBtn = page.getByRole('button', { name: 'Camera capture' })
  check('camera capture mode offered (colour-reagent kit)', await cameraModeBtn.isVisible())
  await cameraModeBtn.click()
  await page.locator('.fp-capture').waitFor()
  check(
    'print reference card link present',
    (await page.locator('a.fp-printlink').getAttribute('href')) === '/reference-card.pdf',
  )
  await page.locator('.fp-capture__cardhint').waitFor({ timeout: 8000 })
  check('reference card hint (from GET /reference-card)', await page.locator('.fp-capture__cardhint').isVisible())
  check('upload fallback offered', await page.getByText('Upload a photo instead').isVisible())

  await page.waitForTimeout(1500) // let the headless camera attempt settle
  const live = (await page.locator('.fp-capture__video').count()) > 0
  if (live) {
    check(
      'guide overlay drawn on live camera view',
      (await page.locator('.fp-capture__zone').count()) === 2,
      'zones',
    )
  } else {
    const fallback =
      (await page.locator('.fp-alert__title', { hasText: 'Camera unavailable' }).count()) +
      (await page.locator('.fp-capture__viewport-empty').count())
    check('headless has no camera -> fallback message shown', fallback >= 1, 'no camera in headless')
  }
  await shot('07-1-capture-fallback')

  // --------------------------------------------- inconclusive: dark scene
  await page.setInputFiles('#capture-file', join(IMAGES, 'scene_dark.png'))
  await page.getByRole('button', { name: 'Analyse photo' }).click()
  await page.locator('.fp-capture__report').waitFor({ timeout: 20000 })
  const darkBadge = await page.locator('.fp-capture__shot .fp-badge').innerText()
  check('dark scene -> INCONCLUSIVE badge', darkBadge.includes('INCONCLUSIVE'), darkBadge.trim())
  const gateCount = await page.locator('.fp-gate').count()
  const failCount = await page.locator('.fp-gate.is-fail').count()
  check('failed quality gates reported', failCount >= 1, `${failCount}/${gateCount} failed`)
  const gateHeading = (await page.locator('.fp-gates h4').innerText()).replace(/\s+/g, ' ')
  check('gate heading shows counts', /quality gates — \d+\/\d+ passed/i.test(gateHeading), gateHeading)
  const failLabel = await page.locator('.fp-gate.is-fail .fp-gate__label').first().innerText()
  const failThreshold = await page
    .locator('.fp-gate.is-fail .fp-gate__threshold')
    .first()
    .innerText()
  check(
    'failed gate shows icon + label + threshold',
    failLabel.includes('Failed') && failThreshold.startsWith('Threshold:'),
    `${failLabel} | ${failThreshold}`,
  )
  check(
    'gate icons rendered for every gate',
    (await page.locator('.fp-gate__icon svg').count()) === gateCount,
    `${gateCount} gates`,
  )
  check(
    'concentration line on gate screen',
    (await page.locator('.fp-disclaimer').first().innerText()).includes(CONCENTRATION),
  )
  await shot('07-2-gates-inconclusive')

  // --------------------------------------- retake + ideal scene (all green)
  await page.getByRole('button', { name: 'Retake' }).click()
  await page.setInputFiles('#capture-file', join(IMAGES, 'scene_ideal.png'))
  await page.getByRole('button', { name: 'Analyse photo' }).click()
  await page.locator('.fp-capture__report').waitFor({ timeout: 20000 })
  const okBadge = await page.locator('.fp-capture__shot .fp-badge').innerText()
  check('ideal scene -> Photo accepted', okBadge.includes('Photo accepted'), okBadge.trim())
  check('all gates pass on ideal scene', (await page.locator('.fp-gate.is-fail').count()) === 0)

  // ----------------------------------------------- calibration screen
  await page.getByText('Calibration — original vs corrected').waitFor()
  await page.getByText('Corrected (reference-card matrix)').waitFor({ timeout: 8000 })
  check('original + corrected images side by side', (await page.locator('.fp-calib__img').count()) === 2)
  const patchCount = await page.locator('.fp-patch').count()
  const deCount = await page.locator('.fp-patch__de').count()
  check(
    'reference patches with measured/expected + delta E',
    patchCount >= 4 && deCount === patchCount,
    `${patchCount} patches`,
  )
  const detectText = (await page.locator('.fp-detect').innerText()).replace(/\s+/g, ' ')
  check(
    'detected colour + delta E + margin + limits',
    /detected colour/i.test(detectText) &&
      /ΔE \d/.test(detectText) &&
      /margin \d/i.test(detectText) &&
      /limits: ΔE ≤/i.test(detectText),
    detectText.slice(0, 120),
  )
  check(
    'match badge names the nearest outcome',
    (await page.locator('.fp-detect .fp-badge').innerText()).includes('Colour matches'),
  )
  const acceptBtn = page.getByRole('button', { name: /Accept .* \(camera\)/ })
  check('accept enabled on MATCH', await acceptBtn.isEnabled())
  await shot('07-3-calibration')

  // --------------------------------------------- override requires a reason
  const choiceCount = await page.locator('.fp-verdict__override .fp-choice').count()
  check('override lists the other outcomes', choiceCount >= 1, `${choiceCount} options`)
  await page
    .locator(`.fp-verdict__override .fp-choice:has-text("${overrideOutcome.code}")`)
    .click()
  const saveOverride = page.getByRole('button', { name: 'Save override' })
  check('save override blocked without reason', await saveOverride.isDisabled())
  await page
    .getByLabel(/^Override reason/)
    .fill('Camera colour reading checked against the chart by two officers.')
  check('save override enabled with reason', await saveOverride.isEnabled())
  await saveOverride.click()
  await stepTitle('Review the analysis').waitFor()
  const reviewText = (await page.locator('.fp-wizard__body').first().innerText()).replace(/\s+/g, ' ')
  check(
    'review shows the overridden outcome label',
    reviewText.includes(overrideOutcome.label),
    overrideOutcome.label,
  )
  check('disclaimer on review step', DISC.test(reviewText))

  // ---------------------------------------------------------- finalize + sign
  await page.getByRole('button', { name: /Continue to sign/ }).click()
  await stepTitle('Sign the record').waitFor()
  await page.locator('.fp-checkbox input').click()
  await page.getByRole('button', { name: /Finalize and sign record/ }).click()
  await page.locator('.fp-signed-record').waitFor({ timeout: 20000 })
  check('signed record screen shown', true)

  const signed = page.locator('.fp-signed-record')
  const recordId = (await signed.locator('.fp-mono').first().innerText()).trim()
  check('record id rendered', recordId.length >= 16, recordId)
  const timeText = (await signed.locator('.fp-signed-record__time').innerText()).trim()
  check('server timestamp rendered', timeText !== '—' && timeText.includes('T'), timeText)
  const signedText = (await signed.innerText()).replace(/\s+/g, ' ')
  check(
    'gps on signed screen (coords + accuracy)',
    /51\.50070, -0\.12460 ±12 m/.test(signedText),
    signedText.match(/-?\d+\.\d{5}, -?\d+\.\d{5}[^ ]* ?±\d+ m/)?.[0] ?? 'no gps text',
  )
  const hash = (await signed.locator('.fp-hash').innerText()).trim()
  check('record hash is 64-hex', /^[0-9a-f]{64}$/.test(hash), `${hash.slice(0, 10)}…`)
  check('exactly one .fp-hash in signed panel', (await signed.locator('.fp-hash').count()) === 1)
  const signature = (await signed.locator('.fp-signature').innerText()).trim()
  check(
    'ECDSA signature shown (base64 DER)',
    /^[A-Za-z0-9+/]+={0,2}$/.test(signature) && signature.length >= 64,
    `${signature.length} chars`,
  )
  check('disclaimer on signed screen', DISC.test(signedText))
  check('concentration line on signed screen', signedText.includes(CONCENTRATION))

  const copyBtn = page.locator('button[aria-label="Copy record hash"]')
  await copyBtn.click()
  await page.waitForTimeout(600)
  const copyState = (await copyBtn.innerText()).trim()
  check('copy record hash -> Copied', copyState.includes('Copied'), copyState)

  const dlPromise = page.waitForEvent('download', { timeout: 10000 })
  await signed.getByRole('button', { name: 'Download record JSON' }).click()
  const dl = await dlPromise
  const dlName = dl.suggestedFilename()
  check(
    'record JSON download named for the record id',
    dlName === `fieldproof-record-${recordId}.json`,
    dlName,
  )
  const dlText = readFileSync(await dl.path(), 'utf8')
  check('downloaded bundle contains the displayed hash', dlText.includes(hash))
  await shot('07-4-signed-record')

  // ------------------------------------------- server-side record assertions
  const detail = await apiGet(`/api/records/${recordId}`)
  const test1 = detail.tests[0]
  check('test stored with image sha256', /^[0-9a-f]{64}$/.test(test1.image_sha256 ?? ''), test1.image_sha256 ? 'ok' : 'missing')
  check('test source is CAMERA', test1.source === 'CAMERA', String(test1.source))
  check(
    'override saved with reason',
    test1.is_override === true && Boolean(test1.override_reason),
    `${test1.outcome_code} (overrode ${test1.overridden_outcome_code})`,
  )
  check(
    'chosen outcome differs from camera-detected outcome',
    test1.outcome_code === overrideOutcome.code && test1.overridden_outcome_code === 'PURPLE_BLACK',
    `${test1.outcome_code} vs ${test1.overridden_outcome_code}`,
  )
  check(
    'calibration stored with the test',
    Array.isArray(test1.calibration?.patches) && test1.calibration.patches.length >= 4,
    `patches ${test1.calibration?.patches?.length ?? 0}`,
  )
  check(
    'camera reading stored with the test',
    Boolean(test1.reading) && test1.reading.match_status === 'MATCH',
    String(test1.reading?.match_status),
  )
  check(
    'sample row has gps columns saved',
    typeof detail.sample.gps_lat === 'number' && typeof detail.sample.gps_accuracy_m === 'number',
    `${detail.sample.gps_lat} ±${detail.sample.gps_accuracy_m} m`,
  )

  // -------------------------------------------------- result screen (signed)
  await signed.getByRole('button', { name: 'View analysis' }).click()
  await page.waitForURL(/\/samples\/.+\/analysis/)
  await page.locator('.fp-signed').waitFor()
  check(
    'signed panel on analysis screen',
    (await page.locator('.fp-signed').count()) === 1 &&
      (await page.locator('.fp-signed .fp-hash').count()) === 1,
  )
  const disclaimerText = (await page.locator('.fp-disclaimer').first().innerText()).replace(/\s+/g, ' ')
  check(
    'disclaimer + concentration on analysis screen',
    DISC.test(disclaimerText) && disclaimerText.includes(CONCENTRATION),
  )
  const ov390 = await overflowPx()
  check('no horizontal overflow on analysis screen (390px)', ov390 <= 1, `overflow ${ov390}px`)
  await shot('07-5-analysis-signed')

  // ------------------------------------------------------ accept path (run 2)
  await page.click('a.fp-header__link[href="/new-test"]')
  await page.waitForSelector('.fp-stepper')
  await page.getByLabel('Colour').fill('Accept-path run')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Choose the kit').waitFor()
  await page.locator('label.fp-choice', { hasText: 'MARQUIS' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  await page.getByRole('button', { name: 'Camera capture' }).click()
  await page.locator('.fp-capture').waitFor()
  await page.setInputFiles('#capture-file', join(IMAGES, 'scene_ideal.png'))
  await page.getByRole('button', { name: 'Analyse photo' }).click()
  await page.locator('.fp-capture__report').waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: /Accept .* \(camera\)/ }).click()
  await stepTitle('Review the analysis').waitFor()
  check('accept path reaches review', true)

  await page.getByRole('button', { name: /Continue to sign/ }).click()
  await stepTitle('Sign the record').waitFor()
  await page.locator('.fp-checkbox input').click()
  await page.getByRole('button', { name: /Finalize and sign record/ }).click()
  await page.locator('.fp-signed-record').waitFor({ timeout: 20000 })
  const recordId2 = (await page.locator('.fp-signed-record .fp-mono').first().innerText()).trim()
  check('second record finalized', recordId2.length >= 16, recordId2)

  const detail2 = await apiGet(`/api/records/${recordId2}`)
  const test2 = detail2.tests[0]
  check(
    'accept path stores detected outcome, not an override',
    test2.outcome_code === 'PURPLE_BLACK' && test2.is_override === false,
    `${test2.outcome_code} / is_override=${test2.is_override}`,
  )
  check('accept path stores image sha256', /^[0-9a-f]{64}$/.test(test2.image_sha256 ?? ''))
  check('second sample gps saved', typeof detail2.sample.gps_lat === 'number')
  await shot('07-6-accept-signed')

  // --------------------------------------------------------------- 360 px
  await page.setViewportSize({ width: 360, height: 800 })
  await page.waitForTimeout(300)
  const ov360 = await overflowPx()
  check('no horizontal overflow on signed screen (360px)', ov360 <= 1, `overflow ${ov360}px`)
} catch (err) {
  check('unhandled error (script aborted)', false, err instanceof Error ? err.message : String(err))
} finally {
  await context.close().catch(() => {})
  await browser.close().catch(() => {})
}

const passed = results.filter((r) => r.ok).length
console.log(`\nstep7 e2e: ${passed}/${results.length} checks passed`)
if (SHOT_DIR) console.log(`screenshots: ${SHOT_DIR}`)
process.exit(passed === results.length ? 0 : 1)

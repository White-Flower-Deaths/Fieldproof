/* Regression E2E: wizard back-navigation after a test is recorded.
 * Covers the fixed dead-Back bug on the Review step and the read-only
 * descent chain Review -> Result -> Kit (Sample stays locked).
 * Requires: backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-back.mjs   (add SHOT_DIR=../docs/screenshots for shots)
 */
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = 'http://localhost:5173'
const SHOT_DIR = process.env.SHOT_DIR ?? ''
if (SHOT_DIR) mkdirSync(SHOT_DIR, { recursive: true })

const results = []
const check = (name, ok, extra = '') => {
  results.push({ name, ok: !!ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? `  [${extra}]` : ''}`)
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
page.setDefaultTimeout(15000)

const shot = async (name) => {
  if (SHOT_DIR) await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

const stepTitle = (text) => page.locator('.fp-card__title', { hasText: text })
const backBtn = () => page.getByRole('button', { name: 'Back' })
const stepperChip = (label) =>
  page.locator('.fp-stepper__item', { hasText: label }).locator('button')

try {
  // ------------------------------------------------------------ login
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  await page.fill('input[name="username"]', 'officer1')
  await page.fill('input[name="password"]', 'FieldProof#Demo1')
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('login lands on dashboard', await page.getByText('Field dashboard').isVisible())

  // ------------------------------------------------ record a test
  await page.click('a.fp-header__link[href="/new-test"]')
  await page.waitForSelector('.fp-stepper')
  await page.getByLabel('Colour').fill('off-white')
  await page.getByLabel('Approximate weight').fill('~1.5 g')
  await page.getByLabel('Notes').fill('E2E back-nav run')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Choose the kit').waitFor()
  check('sample created -> kit step', true)

  await page.locator('label.fp-choice', { hasText: 'MARQUIS' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  check('kit chosen -> result step', true)

  await page.locator('label.fp-choice', { hasText: 'PURPLE_BLACK' }).click()
  await page.locator('input[placeholder*="4471"]').fill('E2E-BACK')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Review the analysis').waitFor()
  check(
    'test recorded -> review step with engine summary',
    await page.locator('.fp-alert', { hasText: 'Engine summary' }).isVisible(),
  )

  // ------------------------------------- Back from Review (the old bug)
  await backBtn().click()
  await stepTitle('Record the outcome').waitFor()
  check('Back from Review lands on Result step', true)
  await shot('15-back-result')

  const radios = page.locator('input[name="outcome"]')
  check(
    'recorded outcome radios are disabled',
    (await radios.count()) > 0 && (await radios.first()).isDisabled(),
  )
  check(
    'time select and kit batch locked',
    (await page.locator('.fp-wizard select').first()).isDisabled() &&
      (await page.locator('input[placeholder*="4471"]').isDisabled()),
  )
  check(
    'entry-mode control hidden once recorded',
    (await page.locator('.fp-segmented').count()) === 0,
  )
  const cont = page.getByRole('button', { name: /Continue/ })
  check(
    'Continue relabelled to review',
    (await cont.innerText()).includes('Continue to review'),
    await cont.innerText(),
  )

  await page.getByRole('button', { name: 'Continue to review' }).click()
  await stepTitle('Review the analysis').waitFor()
  check('Continue to review returns to Review', true)

  // no duplicate test from the round trip
  await page.waitForFunction(
    () => Boolean(JSON.parse(localStorage.getItem('fieldproof.draft.newtest.v1') ?? 'null')?.sampleId),
    undefined,
    { timeout: 5000 },
  )
  const draft = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('fieldproof.draft.newtest.v1')),
  )
  const sample = await page.evaluate(async (id) => {
    const token = localStorage.getItem('fieldproof.token')
    const res = await fetch(`/api/samples/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.json()
  }, draft.sampleId)
  check('exactly one test recorded', sample.tests?.length === 1, `tests=${sample.tests?.length}`)

  // ------------------------------------- Result -> Kit, read-only Kit
  await backBtn().click()
  await stepTitle('Record the outcome').waitFor()
  await backBtn().click()
  await stepTitle('Choose the kit').waitFor()
  check('Back chain Review -> Result -> Kit', true)
  const anyKitInput = page.locator('.fp-choices input[type=radio]')
  check(
    'recorded kit choices are disabled',
    (await anyKitInput.count()) > 0 && (await anyKitInput.first()).isDisabled(),
  )

  const kitBack = page.locator('.fp-wizard__actions button').first()
  check('Kit Back button disabled once recorded', await kitBack.isDisabled())
  check(
    'Kit Back explains the lock',
    ((await kitBack.getAttribute('title')) ?? '').includes('locked'),
    await kitBack.getAttribute('title'),
  )
  check(
    'stepper Sample chip locked once recorded',
    await stepperChip('Sample').isDisabled(),
  )

  // forward via Continue (locked selection retained), then stepper descent
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  check('Continue from locked Kit re-enters Result', true)
  check('stepper Kit chip reachable from Result', !(await stepperChip('Kit').isDisabled()))
  await stepperChip('Kit').click()
  await stepTitle('Choose the kit').waitFor()
  check('stepper descends Result -> Kit read-only', true)

  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  await page.getByRole('button', { name: 'Continue to review' }).click()
  await stepTitle('Review the analysis').waitFor()
  await page.getByRole('button', { name: /Continue to sign/ }).click()
  await stepTitle('Sign the record').waitFor()
  check('reached Sign step', true)

  await page.locator('.fp-checkbox input').click()
  await page.getByRole('button', { name: /Finalize and sign record/ }).click()
  await page.waitForSelector('.fp-hash')
  const hash = (await page.locator('.fp-hash').first().innerText()).trim()
  check('finalize produced 64-hex hash', /^[0-9a-f]{64}$/.test(hash))

  // ------------------------- post-sign descent still works, still 1 test
  await stepperChip('Review').click()
  await stepTitle('Review the analysis').waitFor()
  check('stepper returns to Review after signing', true)
  await backBtn().click()
  await stepTitle('Record the outcome').waitFor()
  check('Back still works after signing', true)

  const sampleAfter = await page.evaluate(async (id) => {
    const token = localStorage.getItem('fieldproof.token')
    const res = await fetch(`/api/samples/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.json()
  }, draft.sampleId)
  check(
    'still exactly one test after full back-and-forth',
    sampleAfter.tests?.length === 1,
    `tests=${sampleAfter.tests?.length}`,
  )

  // ------------------------------------------- narrow screen regression
  await page.setViewportSize({ width: 360, height: 740 })
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('no horizontal overflow at 360px', overflow <= 1, `overflow=${overflow}px`)
  await shot('16-back-360')
} catch (err) {
  check(`unexpected error: ${err.message}`, false)
} finally {
  await browser.close()
}

const failed = results.filter((r) => !r.ok)
console.log(`\nE2E-BACK: ${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)

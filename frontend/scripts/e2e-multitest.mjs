/* Regression E2E: multi-test reports (Run another test / Cancel adding a
 * test) + the decorative gutter backdrop.
 * Requires: backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-multitest.mjs   (SHOT_DIR=../docs/screenshots for shots)
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
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
page.setDefaultTimeout(15000)

const shot = async (name) => {
  if (SHOT_DIR) await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

const stepTitle = (text) => page.locator('.fp-card__title', { hasText: text })
const countB = async (label) =>
  page
    .locator('.fp-count', { hasText: label })
    .locator('b')
    .innerText()

try {
  // ------------------------------------------------------------ login
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  await page.fill('input[name="username"]', 'officer1')
  await page.fill('input[name="password"]', 'FieldProof#Demo1')
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('login lands on dashboard', true)

  // ------------------------------------------------------- backdrop art
  check('backdrop art visible @1280', await page.locator('.fp-backdrop').isVisible())
  const figCount = await page.locator('.fp-backdrop__fig').count()
  check('backdrop has 10 figures', figCount === 10, `figures=${figCount}`)
  const figOpacity = await page
    .locator('.fp-backdrop__fig')
    .first()
    .evaluate((el) => Number(getComputedStyle(el).opacity))
  check('figure opacity is decorative (<0.3)', figOpacity > 0 && figOpacity < 0.3, `opacity=${figOpacity}`)
  await shot('40-dashboard-backdrop')

  // ------------------------------------------- record the first test
  await page.click('a.fp-header__link[href="/new-test"]')
  await page.waitForSelector('.fp-stepper')
  await page.getByLabel('Colour').fill('off-white')
  await page.getByLabel('Approximate weight').fill('~1.2 g')
  await page.getByLabel('Notes').fill('E2E multi-test run')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Choose the kit').waitFor()
  check('sample created -> kit step', true)

  await page.locator('label.fp-choice', { hasText: 'MARQUIS' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  check('kit chosen -> result step', true)

  await page.locator('label.fp-choice', { hasText: 'PURPLE_BLACK' }).click()
  await page.locator('input[placeholder*="4471"]').fill('E2E-MT-1')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Review the analysis').waitFor()
  check('first test recorded -> review', true)
  check('review counts 1 test', (await countB('tests')) === '1', `tests=${await countB('tests')}`)

  // ----------------------------------- Run another test -> Kit (unlocked)
  await page.getByRole('button', { name: 'Run another test' }).click()
  await stepTitle('Choose the kit').waitFor()
  check('Run another test returns to Kit step', true)
  check(
    'Cancel adding a test offered',
    await page.getByRole('button', { name: 'Cancel adding a test' }).isVisible(),
  )
  const kitRadio = page.locator('.fp-choices input[type=radio]').first()
  check('kit choices editable while re-entering', !(await kitRadio.isDisabled()))
  const sampleChip = page
    .locator('.fp-stepper__item', { hasText: 'Sample' })
    .locator('button')
  check('Sample chip stays locked', await sampleChip.isDisabled())
  await shot('41-multitest-kit')

  // ------------------------------------------------- cancel the re-entry
  await page.getByRole('button', { name: 'Cancel adding a test' }).click()
  await stepTitle('Review the analysis').waitFor()
  check('Cancel returns to Review', true)
  check('cancel keeps 1 test', (await countB('tests')) === '1', `tests=${await countB('tests')}`)

  // --------------------------------------------- now really add test 2
  await page.getByRole('button', { name: 'Run another test' }).click()
  await stepTitle('Choose the kit').waitFor()
  await page.locator('label.fp-choice', { hasText: 'MECKE' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  const outcomeRadio = page.locator('input[name="outcome"]').first()
  check('outcome radios editable for test 2', !(await outcomeRadio.isDisabled()))
  await page.locator('label.fp-choice').first().click()
  await page.locator('input[placeholder*="4471"]').fill('E2E-MT-2')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Review the analysis').waitFor()
  check('second test recorded -> review', true)
  check('review counts 2 tests', (await countB('tests')) === '2', `tests=${await countB('tests')}`)
  const testsLabel = await page.locator('.fp-kv dt', { hasText: 'Tests' }).count()
  check('Review shows plural "Tests" label', testsLabel >= 1, `matches=${testsLabel}`)
  await shot('42-multitest-review')

  // ------------------------------------------------------- API truth
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
  const kits = [...new Set((sample.tests ?? []).map((t) => t.kit_code))].sort()
  check(
    'sample holds exactly 2 tests from 2 kits',
    (sample.tests ?? []).length === 2 && kits.join(',') === 'MARQUIS,MECKE',
    `tests=${sample.tests?.length} kits=${kits.join(',')}`,
  )

  // --------------------------------------------- sign the 2-test record
  await page.getByRole('button', { name: /Continue to sign/ }).click()
  await stepTitle('Sign the record').waitFor()
  check('reached Sign step', true)
  await page.locator('.fp-checkbox input').click()
  await page.getByRole('button', { name: /Finalize and sign record/ }).click()
  await page.waitForSelector('.fp-hash')
  const hash = (await page.locator('.fp-hash').first().innerText()).trim()
  check('finalize produced 64-hex hash', /^[0-9a-f]{64}$/.test(hash))

  // ------------------------------------------- narrow screen regression
  await page.setViewportSize({ width: 360, height: 740 })
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('no horizontal overflow at 360px', overflow <= 1, `overflow=${overflow}px`)
  check('backdrop hidden at 360px', !(await page.locator('.fp-backdrop').isVisible()))
  await shot('43-multitest-360')
} catch (err) {
  check(`unexpected error: ${err.message}`, false)
} finally {
  await browser.close()
}

const failed = results.filter((r) => !r.ok)
console.log(`\nE2E-MULTITEST: ${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)

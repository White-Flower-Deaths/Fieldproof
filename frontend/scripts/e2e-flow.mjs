/* Headless E2E for the step-6 flow: login -> wizard -> result -> finalize.
 * Requires: backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-flow.mjs            (add SHOT_DIR=../docs/screenshots for shots)
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

// Scoped to card titles - the page subtitle repeats the same words, so bare
// getByText would match before the step actually changes.
const stepTitle = (text) => page.locator('.fp-card__title', { hasText: text })

try {
  // ---------------------------------------------------------------- login
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  await shot('01-login')

  await page.fill('input[name="username"]', 'officer1')
  await page.fill('input[name="password"]', 'FieldProof#Demo1')
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('login lands on dashboard', await page.getByText('Field dashboard').isVisible())
  await shot('02-dashboard')

  // --------------------------------------------------------------- wizard
  await page.click('a.fp-header__link[href="/new-test"]')
  await page.waitForSelector('.fp-stepper')
  check('stepper has 5 steps', (await page.locator('.fp-stepper__item').count()) === 5)
  check(
    'autosave indicator present',
    /Draft (saved|saves)/.test(await page.locator('.fp-wizard__autosave').innerText()),
  )

  await page.getByLabel('Colour').fill('off-white')
  await page.getByLabel('Approximate weight').fill('~1.5 g')
  await page.getByLabel('Notes').fill('E2E wizard run')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Choose the kit').waitFor()
  check('sample created -> kit step', true)

  await page.locator('label.fp-choice', { hasText: 'MARQUIS' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  check('kit chosen -> result step', true)

  await page.locator('label.fp-choice', { hasText: 'PURPLE_BLACK' }).click()
  await page.locator('input[placeholder*="4471"]').fill('E2E-1')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Review the analysis').waitFor()
  check(
    'test recorded -> review step with engine summary',
    await page
      .locator('.fp-alert', { hasText: 'Engine summary' })
      .isVisible(),
  )
  await shot('03-review')

  await page.getByRole('button', { name: /Continue to sign/ }).click()
  await stepTitle('Sign the record').waitFor()
  check('review -> sign step', true)

  // sign step 1: disclaimer + acknowledgement gate
  check(
    'concentration line in sign step',
    (await page
      .getByText('Concentration: not determinable from presumptive tests')
      .count()) >= 1,
  )
  const signBtn = page.getByRole('button', { name: /Finalize and sign record/ })
  check('finalize disabled before acknowledgement', await signBtn.isDisabled())
  await page.locator('.fp-checkbox input').click()
  check('finalize enabled after acknowledgement', !(await signBtn.isDisabled()))
  await signBtn.click()
  await page.waitForSelector('.fp-hash')
  const hash1 = (await page.locator('.fp-hash').first().innerText()).trim()
  check('record hash is 64-hex', /^[0-9a-f]{64}$/.test(hash1), hash1.slice(0, 12) + '…')
  check('record id shown', (await page.locator('.fp-mono').count()) > 0)
  await shot('04-signed')

  // ------------------------------------------------------- result screen
  await page.getByRole('button', { name: /View analysis/ }).click()
  await page.waitForURL(/\/samples\/[0-9a-f-]+\/analysis/)
  await page.locator('.fp-result__topname').waitFor()
  check('hero top match visible', await page.locator('.fp-result__topname').isVisible())
  check(
    'status chip (icon + text) in hero',
    (await page.locator('.fp-result__hero .fp-badge__icon').count()) > 0 &&
      (await page.locator('.fp-result__hero .fp-badge').first().innerText()).trim().length > 2,
  )
  check('confidence gauge visible', await page.locator('.fp-gauge svg').isVisible())
  await page.locator('li.fp-evidence__item').first().waitFor()
  check('alternatives bars', (await page.locator('.fp-alt').count()) >= 1)
  check('evidence list items', (await page.locator('li.fp-evidence__item').count()) >= 1)
  check(
    'evidence supports/contradicts icons',
    (await page.locator('.fp-evidence__icon').count()) >= 1,
  )
  await page.locator('.fp-why summary').click()
  check('why-this-result expands', await page.locator('.fp-why__body').isVisible())
  check(
    'disclaimer on result screen',
    (await page.getByText('PRESUMPTIVE FIELD RESULT ONLY').count()) >= 1,
  )
  check(
    'exact concentration line on result screen',
    (await page
      .getByText('Concentration: not determinable from presumptive tests')
      .count()) >= 1,
  )
  check(
    'signed record panel with hash',
    (await page.locator('.fp-signed .fp-hash').count()) === 1,
  )
  const fonts = await page.evaluate(() => ({
    inter: document.fonts.check('16px Inter'),
    mono: getComputedStyle(document.querySelector('.fp-hash')).fontFamily,
  }))
  check('Inter font loaded', fonts.inter)
  check('JetBrains Mono on hashes', /JetBrains Mono/.test(fonts.mono), fonts.mono)
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('no horizontal overflow at 390px', overflow <= 1, `overflow=${overflow}px`)
  await shot('05-result')

  // ------------------------------------- second sample: finalize on result
  await page.goto(`${BASE}/new-test`)
  await page.waitForSelector('.fp-stepper')
  await page.click('.fp-wizard form button[type=submit]') // sample
  await stepTitle('Choose the kit').waitFor()
  await page.locator('label.fp-choice', { hasText: 'MECKE' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()
  await page.locator('label.fp-choice').first().click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Review the analysis').waitFor()

  await page.waitForFunction(
    () => Boolean(JSON.parse(localStorage.getItem('fieldproof.draft.newtest.v1') ?? 'null')?.sampleId),
    undefined,
    { timeout: 5000 },
  )
  const draft = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('fieldproof.draft.newtest.v1')),
  )
  check('draft auto-saved with sample id', Boolean(draft && draft.sampleId))
  await page.goto(`${BASE}/samples/${draft.sampleId}/analysis`)
  await page.getByRole('button', { name: /Finalize and sign record/ }).waitFor()
  check('unsigned sample shows finalize button on result screen', true)
  await page.getByRole('button', { name: /Finalize and sign record/ }).click()
  await page.waitForSelector('.fp-signed .fp-hash')
  const hash2 = (await page.locator('.fp-hash').first().innerText()).trim()
  check('result-screen finalize produced hash', /^[0-9a-f]{64}$/.test(hash2))
  await shot('06-finalize-on-result')

  // ------------------------------------------------------- narrow screen
  await page.setViewportSize({ width: 360, height: 740 })
  const overflow360 = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('no horizontal overflow at 360px', overflow360 <= 1, `overflow=${overflow360}px`)
  await shot('07-360-result')

  // -------------------------------------------------------- theme toggle
  await page.locator('.fp-icon-btn[aria-label*="dark theme"]').click()
  check(
    'dark theme applies',
    (await page.getAttribute('html', 'data-theme')) === 'dark',
  )
  await page.locator('.fp-icon-btn[aria-label*="light theme"]').click()
  check(
    'light theme restored',
    (await page.getAttribute('html', 'data-theme')) === 'light',
  )
} catch (err) {
  check(`unexpected error: ${err.message}`, false)
} finally {
  await browser.close()
}

const failed = results.filter((r) => !r.ok)
console.log(`\nE2E: ${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)

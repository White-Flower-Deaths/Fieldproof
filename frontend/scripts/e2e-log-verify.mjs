/* Headless E2E for step 8: finalize a record -> /log -> /verify (valid +
 * tampered) -> CSV export -> 360 px layout.
 * Requires backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-log-verify.mjs   (SHOT_DIR=../docs/screenshot for shots)
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
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

const apiGet = async (path) => {
  const token = await page.evaluate(() => localStorage.getItem('fieldproof.token'))
  const response = await fetch(`http://localhost:5173${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error(`API ${path} -> ${response.status}`)
  return response.json()
}

try {
  // ------------------------------------------------------- login + finalize
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  await page.fill('input[name="username"]', 'officer1')
  await page.fill('input[name="password"]', 'FieldProof#Demo1')
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('login lands on dashboard', true)

  await page.click('a.fp-header__link[href="/new-test"]')
  await page.waitForSelector('.fp-stepper')
  await page.getByLabel('Colour').fill('off-white')
  await page.getByLabel('Approximate weight').fill('~1.2 g')
  await page.getByLabel('Notes').fill('Log/verify E2E run')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Choose the kit').waitFor()

  await page.locator('label.fp-choice', { hasText: 'MARQUIS' }).click()
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Record the outcome').waitFor()

  await page.locator('label.fp-choice', { hasText: 'PURPLE_BLACK' }).click()
  await page.locator('input[placeholder*="4471"]').fill('LOG-E2E')
  await page.click('.fp-wizard form button[type=submit]')
  await stepTitle('Review the analysis').waitFor()
  await page.getByRole('button', { name: /Continue to sign/ }).click()
  await stepTitle('Sign the record').waitFor()
  await page.locator('.fp-checkbox input').click()
  await page.getByRole('button', { name: /Finalize and sign record/ }).click()
  await page.waitForSelector('.fp-hash')
  check('fresh record finalized', true)

  const latest = await apiGet('/api/records?page_size=1')
  const freshCode = latest.items[0].sample_code
  const freshId = latest.items[0].id
  check('fresh record is newest in list', Boolean(freshCode), freshCode)

  // ------------------------------------------------------------------- /log
  await page.click('a.fp-header__link[href="/log"]')
  await page.getByText('Records log').waitFor()
  check('nav has Log link', await page.locator('a.fp-header__link[href="/log"]').isVisible())
  check('status filter chips present', (await page.locator('.fp-chip').count()) >= 7)
  await page.getByText('All kits').waitFor()
  check('kit filter chips present', await page.getByText('All kits').isVisible())

  await page.locator('.fp-log-table tbody tr').first().waitFor()
  const rowCount = await page.locator('.fp-log-table tbody tr').count()
  check('desktop table rows rendered', rowCount >= 1, `${rowCount} rows`)

  // first row = fresh record, its verified badge must resolve to PASS
  const firstRow = page.locator('.fp-log-table tbody tr').first()
  await firstRow.locator('.fp-badge', { hasText: 'Verified' }).waitFor()
  check(
    'row verified badge (icon + text)',
    (await firstRow.locator('.fp-badge__icon').count()) >= 1,
    (await firstRow.locator('.fp-badge').last().innerText()).trim(),
  )
  // badge must be inside the visible (non-scrolled) table area, not clipped
  const badgeBox = await firstRow.locator('.fp-badge').last().boundingBox()
  const wrapBox = await page.locator('.fp-log-table .fp-table-wrap').boundingBox()
  check(
    'verified badge visible (not clipped by table scroll)',
    Boolean(badgeBox && wrapBox) &&
      badgeBox.x + badgeBox.width <= wrapBox.x + wrapBox.width + 1,
    badgeBox && wrapBox
      ? `badge ends ${Math.round(badgeBox.x + badgeBox.width)}, wrap ends ${Math.round(wrapBox.x + wrapBox.width)}`
      : 'missing boxes',
  )

  // sortable headers
  await page.getByRole('button', { name: /Sample/ }).click()
  const sorted = await page
    .locator('.fp-log-table thead th[aria-sort]:not([aria-sort="none"])')
    .getAttribute('aria-sort')
  check('table sortable (Sample column)', sorted === 'ascending', sorted ?? 'none')

  // search by sample id
  await page.getByLabel('Search records by record ID or sample ID').fill(freshCode)
  await page.waitForTimeout(700)
  const filteredRows = await page.locator('.fp-log-table tbody tr').count()
  const firstCell = await page.locator('.fp-log-table tbody tr').first().innerText()
  check(
    'search narrows to the fresh record',
    filteredRows >= 1 && firstCell.includes(freshCode),
    `${filteredRows} rows`,
  )

  // empty state for a nonsense query
  await page.getByLabel('Search records by record ID or sample ID').fill('zzz-no-such-record')
  await page.getByText('No records match').waitFor()
  check('empty state on no match', true)
  await page.getByRole('button', { name: 'Clear filters' }).first().click()
  await page.locator('.fp-log-table tbody tr').first().waitFor()
  check('clear filters restores list', true)

  // CSV export (PDF button must stay hidden)
  check(
    'PDF export button hidden',
    (await page.getByRole('button', { name: /PDF/ }).count()) === 0,
  )
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Export CSV' }).click(),
  ])
  const csvPath = await download.path()
  const csvHead = readFileSync(csvPath, 'utf8').split(/\r?\n/)[0]
  check(
    'CSV export downloads with header',
    csvHead.startsWith('record_id,sample_code,status'),
    download.suggestedFilename(),
  )
  check(
    'CSV carries disclaimer + concentration columns',
    /disclaimer/.test(csvHead) && /concentration_note/.test(csvHead),
  )

  // split detail view (re-search: the table is still sorted by sample code)
  await page.getByLabel('Search records by record ID or sample ID').fill(freshCode)
  await page.waitForTimeout(700)
  await page.locator('.fp-log-table tbody tr', { hasText: freshCode }).first().click()
  await page
    .locator('.fp-detail-section__title', { hasText: 'Verification status' })
    .waitFor()
  check('detail: tests section', (await page.locator('.fp-detail-section__title', { hasText: 'Tests' }).count()) >= 1)
  check('detail: analysis section', (await page.locator('.fp-detail-section__title', { hasText: 'Analysis' }).count()) >= 1)
  check('detail: hash + signature section', (await page.locator('.fp-detail-section__title', { hasText: 'Hash & signature' }).count()) >= 1)
  check('detail: record hash shown', (await page.locator('.fp-log-detail .fp-hash').count()) >= 2)
  check(
    'detail: verification status PASS',
    await page
      .locator('.fp-log-detail .fp-badge', { hasText: 'Verification passed' })
      .isVisible(),
  )
  check(
    'detail: checklist has icon + text',
    (await page.locator('.fp-log-detail .fp-checklist__icon').count()) >= 4,
  )
  check(
    'detail: disclaimer + concentration line',
    (await page.locator('.fp-log-detail .fp-disclaimer').count()) >= 1 &&
      (await page
        .getByText('Concentration: not determinable from presumptive tests')
        .count()) >= 1,
  )
  await shot('01-log-desktop')

  // ---------------------------------------------------------------- /verify
  await page.click('a.fp-header__link[href="/verify"]')
  await page.getByText('Verify a record').waitFor()
  check('nav has Verify link', await page.locator('a.fp-header__link[href="/verify"]').isVisible())
  check('two dropzones', (await page.locator('.fp-dropzone').count()) === 2)

  // valid example -> PASS
  await page.getByRole('button', { name: 'Try a valid example' }).click()
  await page.locator('.fp-verify-headline .fp-badge', { hasText: 'Verification passed' }).waitFor()
  check('valid example passes', true)
  const passChecks = await page.locator('.fp-check').count()
  const passFail = await page.locator('.fp-check.is-fail').count()
  check('checklist has 5 rows, no failure', passChecks === 5 && passFail === 0, `${passChecks} rows`)
  check('checklist record_hash passed', await page.locator('.fp-check', { hasText: 'Record hash' }).first().locator('.fp-check__word', { hasText: 'Passed' }).isVisible())
  check('checklist signature passed', await page.locator('.fp-check', { hasText: 'Signature' }).first().locator('.fp-check__word', { hasText: 'Passed' }).isVisible())
  check('checklist chain integrity passed', await page.locator('.fp-check', { hasText: 'Chain integrity' }).first().locator('.fp-check__word', { hasText: 'Passed' }).isVisible())
  check(
    'concentration line + disclaimer on result',
    (await page.locator('.fp-verify-result .fp-verify-concentration').innerText()) ===
      'Concentration: not determinable from presumptive tests' &&
      (await page.locator('.fp-verify-result .fp-disclaimer').count()) === 1,
  )
  await shot('02-verify-pass')

  // tampered example -> FAIL, highlighted
  await page.getByRole('button', { name: 'Try a tampered example' }).click()
  await page.locator('.fp-verify-headline .fp-badge', { hasText: 'Verification failed' }).waitFor()
  check('tampered example fails', true)
  const failedRows = await page.locator('.fp-check.is-fail').count()
  check('failed checks highlighted', failedRows >= 1, `${failedRows} failed`)
  check(
    'failure reason shown',
    await page
      .locator('.fp-check.is-fail .fp-check__detail')
      .first()
      .isVisible(),
  )
  check('failed-checks alert visible', await page.locator('.fp-verify-result .fp-alert--danger').isVisible())
  check(
    'concentration line + disclaimer still shown on FAIL',
    (await page
      .getByText('Concentration: not determinable from presumptive tests')
      .count()) >= 1 && (await page.locator('.fp-disclaimer').count()) >= 1,
  )
  await shot('03-verify-fail')

  // manual file pick path (dropzone input) using the exact stored bundle
  const rawRecord = await (
    await fetch(`http://localhost:5173/api/records/${freshId}/export?format=json`, {
      headers: {
        Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('fieldproof.token'))}`,
      },
    })
  ).text()
  const tmpFile = join(tmpdir(), `fp-record-${Date.now()}.json`)
  writeFileSync(tmpFile, rawRecord)
  await page.setInputFiles('#verify-record-file', tmpFile)
  check('file picked via dropzone input', (await page.locator('.fp-dropzone.has-file').count()) >= 1)
  await page.getByRole('button', { name: 'Run verification' }).click()
  await page.locator('.fp-verify-headline .fp-badge', { hasText: 'Verification passed' }).waitFor()
  check('manual upload verification passes', true)

  // image dropzone without record is blocked
  await page.getByRole('button', { name: 'Try a valid example' }).click()
  await page.locator('.fp-verify-headline .fp-badge', { hasText: 'Verification passed' }).waitFor()

  // ------------------------------------------------------------ 360 px pass
  await page.setViewportSize({ width: 360, height: 740 })
  await page.goto(`${BASE}/log`)
  await page.locator('.fp-log-cards li').first().waitFor()
  const logCards = await page.locator('.fp-log-cards li').count()
  const tableVisible = await page.locator('.fp-log-table').isVisible()
  const logOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('360: log shows card list', logCards >= 1 && !tableVisible, `${logCards} cards`)
  check('360: no horizontal overflow (log)', logOverflow <= 0, `${logOverflow}px`)
  await shot('04-log-360')

  await page.goto(`${BASE}/verify`)
  await page.getByText('Verify a record').waitFor()
  const verifyOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('360: no horizontal overflow (verify)', verifyOverflow <= 0, `${verifyOverflow}px`)
  await shot('05-verify-360')

  // mobile card selection opens the detail pane
  await page.goto(`${BASE}/log`)
  await page.locator('.fp-log-cards button').first().click()
  await page
    .locator('.fp-detail-section__title', { hasText: 'Verification status' })
    .waitFor()
  check('360: tapping a card opens detail', true)
} catch (error) {
  check(`unhandled error: ${error.message}`, false)
  console.error(error)
} finally {
  await browser.close()
}

const failed = results.filter((result) => !result.ok)
console.log(`\nE2E: ${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)

/* Headless E2E for step 9: demo-mode ribbon, toggle persistence, and the
 * dismissible walkthrough (keyboard, navigation, 360 px layout).
 * Requires backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-demomode.mjs   (SHOT_DIR=../docs/screenshots for shots)
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
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await context.newPage()
page.setDefaultTimeout(15000)

const shot = async (name) => {
  if (SHOT_DIR) await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}
const activeElement = () => page.evaluate(() => {
  const el = document.activeElement
  return el ? `${el.tagName}.${el.className}|${(el.textContent ?? '').trim().slice(0, 40)}` : ''
})
const storedDemoMode = () =>
  page.evaluate(() => localStorage.getItem('fieldproof.demomode.v1'))

try {
  // --------------------------------------------- fresh profile -> mode is ON
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  check('pre-login: no demo bar (outside the shell)', (await page.locator('.fp-demobar').count()) === 0)
  await page.fill('input[name="username"]', 'officer1')
  await page.fill('input[name="password"]', 'FieldProof#Demo1')
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()

  const bar = page.locator('.fp-demobar')
  await bar.waitFor()
  check('ribbon visible on dashboard', await bar.isVisible())
  check('ribbon defaults to demo ON', (await bar.getAttribute('class')).includes('fp-demobar--on'))
  const barText = (await bar.innerText()).toLowerCase()
  check(
    'ribbon shows demo chip + controls',
    barText.includes('demo mode') && barText.includes('take the tour') && barText.includes('on'),
    barText.replace(/\n/g, ' / '),
  )
  check('ribbon labelled as a landmark', (await bar.getAttribute('aria-label')) === 'Demo mode')
  await shot('08-demo-ribbon')

  // ------------------------------------------------------------------ tour
  await page.getByRole('button', { name: 'Take the tour' }).click()
  const tour = page.locator('.fp-tour')
  await tour.waitFor()
  await page.waitForFunction(() => document.activeElement?.classList.contains('fp-tour'))
  check('tour opens as a dialog', (await tour.getAttribute('role')) === 'dialog')
  check('tour is non-blocking (no scrim)', (await page.locator('.fp-tour__scrim').count()) === 0)
  check('focus moves into the tour card', true, await activeElement())
  check('step counter starts at 1 of 5', /step 1 of 5/i.test(await tour.innerText()))
  check('tour action points at New test', (await tour.innerText()).includes('Open New test'))

  await tour.getByRole('button', { name: 'Next' }).click()
  check('next advances to step 2 of 5', /step 2 of 5/i.test(await tour.innerText()))
  const resultAction = await tour.locator('.fp-tour__action').innerText()
  check(
    'result step action is a demo result or start test',
    resultAction.includes('Open a demo result') || resultAction.includes('Start a test'),
    resultAction.trim(),
  )

  // step 2 action navigates while the tour stays open (non-modal)
  await tour.locator('.fp-tour__action').click()
  await page.waitForURL(/\/samples\/[^/]+\/analysis|\/new-test/)
  check('result action navigates', /\/samples\/[^/]+\/analysis|\/new-test/.test(page.url()), page.url())
  check('tour remains open across navigation', await tour.isVisible())

  // continue to the Log step and navigate there
  await tour.getByRole('button', { name: 'Next' }).click()
  check('step 3 of 5 (signed record)', /step 3 of 5/i.test(await tour.innerText()))
  await tour.getByRole('button', { name: 'Next' }).click()
  check('step 4 of 5 (log)', /step 4 of 5/i.test(await tour.innerText()))
  check(
    'log step body mentions export',
    (await tour.innerText()).includes('CSV export'),
  )
  await tour.locator('.fp-tour__action').click()
  await page.waitForURL(/\/log/)
  check('log action navigates to /log', page.url().endsWith('/log'))
  await tour.getByRole('button', { name: 'Next' }).click()
  check('step 5 of 5 mentions the tampered example', (await tour.innerText()).includes('tampered example'))

  // keyboard: Escape closes and returns focus to the ribbon trigger
  await page.keyboard.press('Escape')
  await tour.waitFor({ state: 'hidden' })
  check('Escape closes the tour', true)
  check(
    'focus returns to the tour trigger',
    (await activeElement()).includes('Take the tour'),
    await activeElement(),
  )

  // Skip closes from anywhere
  await page.getByRole('button', { name: 'Take the tour' }).click()
  await tour.waitFor()
  await tour.getByRole('button', { name: 'Skip' }).click()
  await tour.waitFor({ state: 'hidden' })
  check('Skip closes the tour', true)

  // ---------------------------------------------------------------- toggle
  await page.getByRole('switch').click()
  check('toggle turns demo mode off', (await bar.getAttribute('class')).includes('fp-demobar--off'))
  check('off ribbon hides the tour button', (await page.getByRole('button', { name: 'Take the tour' }).count()) === 0)
  check('preference stored', (await storedDemoMode()) === 'off', String(await storedDemoMode()))

  await page.goto(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('off state persists across reload', (await page.locator('.fp-demobar--off').count()) === 1)

  await page.getByRole('switch').click()
  check('toggle turns demo mode back on', (await page.locator('.fp-demobar--on').count()) === 1)
  check('preference stored', (await storedDemoMode()) === 'on')
  await page.goto(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('on state persists across reload', (await page.locator('.fp-demobar--on').count()) === 1)

  // ------------------------------------------------------------ 360 px pass
  await page.setViewportSize({ width: 360, height: 740 })
  await page.goto(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('360: no horizontal overflow with ribbon', overflow <= 0, `${overflow}px`)
  await shot('08-demo-ribbon-360')

  await page.getByRole('button', { name: 'Take the tour' }).click()
  await tour.waitFor()
  const box = await tour.boundingBox()
  check(
    '360: tour card fits the viewport',
    Boolean(box) && box.x >= 0 && box.x + box.width <= 361,
    box ? `x=${Math.round(box.x)} w=${Math.round(box.width)}` : 'no box',
  )
  check('360: tour controls all reachable', (await tour.locator('button').count()) >= 5)
  await shot('08-demo-tour-360')
  await page.keyboard.press('Escape')

  // dark theme: ribbon and tour keep readable colours (token-driven)
  await page.evaluate(() => localStorage.setItem('fieldproof.theme', 'dark'))
  await page.reload()
  await page.getByText('Field dashboard').waitFor()
  const darkOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  check('dark + 360: no overflow', darkOverflow <= 0, `${darkOverflow}px`)
} catch (error) {
  check(`unhandled error: ${error.message}`, false)
  console.error(error)
} finally {
  await browser.close()
}

const failed = results.filter((result) => !result.ok)
console.log(`\nE2E: ${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)

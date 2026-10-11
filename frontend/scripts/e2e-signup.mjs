/* Headless E2E for account sign-up: link navigation both ways, client and
 * server validation errors, auto-login, logout, duplicate rejection, login
 * with the new credentials, and a 360 px layout check.
 * Requires backend on :8000 and `npm run dev` on :5173.
 *   node scripts/e2e-signup.mjs   (SHOT_DIR=../docs/screenshots for shots)
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
const alertText = async () =>
  (await page.locator('.fp-alert').first().innerText().catch(() => '')).replace(/\n/g, ' ')

const USER = `qa_${Date.now()}`
const PASS = 'SignupPass!9'

try {
  // ------------------------------------------------- login <-> signup links
  await page.goto(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  const toSignup = page.locator('a[href="/signup"]')
  check('login: has "Create one" link', await toSignup.isVisible())
  await toSignup.click()
  await page.waitForURL(`${BASE}/signup`)
  await page.waitForSelector('input[name="password_confirm"]')
  check('signup: page loads with confirm field', true)
  const toLogin = page.locator('a[href="/login"]')
  check('signup: has "Sign in" link', await toLogin.isVisible())
  await toLogin.click()
  await page.waitForURL(`${BASE}/login`)
  await page.waitForSelector('input[name="username"]')
  check('signup -> login link navigates back', true)
  await page.click('a[href="/signup"]')
  await page.waitForURL(`${BASE}/signup`)
  await page.waitForSelector('input[name="password_confirm"]')

  // --------------------------------------------------------- client-side check
  await page.fill('input[name="username"]', USER)
  await page.fill('input[name="password"]', PASS)
  await page.fill('input[name="password_confirm"]', 'DifferentPass1')
  await page.click('button[type=submit]')
  await page.locator('.fp-alert').waitFor()
  const mismatch = await alertText()
  check(
    'mismatched passwords blocked client-side',
    mismatch.toLowerCase().includes('do not match'),
    mismatch,
  )
  check('stays on /signup after mismatch', page.url().endsWith('/signup'))

  // ------------------------------------------- server-side weak-password check
  await page.fill('input[name="password"]', 'abc')
  await page.fill('input[name="password_confirm"]', 'abc')
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/api/auth/register') && r.status() === 422,
    ),
    page.click('button[type=submit]'),
  ])
  await page.locator('.fp-alert').waitFor()
  const weak = await alertText()
  check(
    'weak password rejected by server',
    weak.includes('8-128 characters'),
    weak,
  )
  check('stays on /signup after 422', page.url().endsWith('/signup'))

  // ----------------------------------------------------------- successful signup
  await page.fill('input[name="password"]', PASS)
  await page.fill('input[name="password_confirm"]', PASS)
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('sign-up auto-logs in to dashboard', true, `user=${USER}`)
  check('demo ribbon visible for new account', await page.locator('.fp-demobar').isVisible())
  const token = await page.evaluate(() => localStorage.getItem('fieldproof.token'))
  check('JWT stored after sign-up', !!token)
  const me = await page.evaluate(async () => {
    const res = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${localStorage.getItem('fieldproof.token')}` },
    })
    return res.ok ? res.json() : null
  })
  check(
    'new account is OFFICER role',
    me && me.role === 'OFFICER' && me.username === USER,
    me ? `role=${me.role} username=${me.username}` : 'me=null',
  )
  await shot('09-signup-dashboard')

  // ---------------------------------------------------------------- logout
  await page.click('button[aria-label="Sign out"]')
  await page.waitForURL(`${BASE}/login`)
  check('logout returns to login', true)

  // ------------------------------------------------- duplicate signup (409)
  await page.click('a[href="/signup"]')
  await page.waitForURL(`${BASE}/signup`)
  await page.fill('input[name="username"]', USER)
  await page.fill('input[name="password"]', 'OtherPass!23')
  await page.fill('input[name="password_confirm"]', 'OtherPass!23')
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/api/auth/register') && r.status() === 409,
    ),
    page.click('button[type=submit]'),
  ])
  await page.locator('.fp-alert').waitFor()
  const dup = await alertText()
  check('duplicate username shows 409 error', dup.toLowerCase().includes('taken'), dup)
  check('stays on /signup after 409', page.url().endsWith('/signup'))
  await shot('09-signup-duplicate')

  // ------------------------------------- login with the freshly created account
  await page.click('a[href="/login"]')
  await page.waitForURL(`${BASE}/login`)
  await page.fill('input[name="username"]', USER)
  await page.fill('input[name="password"]', PASS)
  await page.click('button[type=submit]')
  await page.waitForURL(`${BASE}/`)
  await page.getByText('Field dashboard').waitFor()
  check('login with new credentials works', true)
  await page.click('button[aria-label="Sign out"]')
  await page.waitForURL(`${BASE}/login`)

  // ------------------------------------------------------------ 360 px layout
  await page.setViewportSize({ width: 360, height: 800 })
  await page.goto(`${BASE}/signup`)
  await page.waitForSelector('input[name="password_confirm"]')
  const overflow = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    inner: window.innerWidth,
  }))
  check(
    'signup: no horizontal overflow at 360px',
    overflow.scroll <= overflow.inner + 1,
    `scrollW=${overflow.scroll} innerW=${overflow.inner}`,
  )
  const btnBox = await page.locator('button[type=submit]').boundingBox()
  check(
    'signup: submit button >= 48px tall at 360px',
    !!btnBox && btnBox.height >= 48,
    btnBox ? `h=${btnBox.height}` : 'no box',
  )
  await shot('09-signup-360')
} catch (err) {
  check('script completed without exception', false, String(err).slice(0, 200))
} finally {
  await browser.close()
}

const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length === 0 ? 0 : 1)

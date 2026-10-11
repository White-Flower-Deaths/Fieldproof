/** Demo-mode preference: persisted in localStorage, on by default. */
const STORAGE_KEY = 'fieldproof.demomode.v1'

export function getStoredDemoMode(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'off') return false
    if (stored === 'on') return true
  } catch {
    /* storage unavailable */
  }
  return true
}

export function storeDemoMode(on: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off')
  } catch {
    /* storage unavailable */
  }
}

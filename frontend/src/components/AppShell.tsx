import { useState } from 'react'
import type { ReactNode } from 'react'
import { ClipboardList, LogOut, Moon, Plus, ScrollText, ShieldCheck, Sun } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/auth-context'
import { applyTheme, getStoredTheme } from '../lib/theme'
import type { Theme } from '../lib/theme'
import { DemoMode } from './DemoMode'
import { Logo } from './Logo'

/** Persistent app chrome: navy header, page content. */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme())

  const toggleTheme = () => {
    const next: Theme = theme === 'light' ? 'dark' : 'light'
    applyTheme(next)
    setTheme(next)
  }

  const onLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="fp-shell">
      <DemoMode />
      <header className="fp-header">
        <div className="fp-header__inner">
          <Logo href="/" tagline="Field records" />
          <nav className="fp-header__nav" aria-label="Main">
            <NavLink
              to="/"
              end
              aria-label="Dashboard"
              className={({ isActive }) =>
                `fp-header__link${isActive ? ' is-active' : ''}`
              }
            >
              <ClipboardList size={16} aria-hidden="true" />
              <span>Dashboard</span>
            </NavLink>
            <NavLink
              to="/new-test"
              aria-label="New test"
              className={({ isActive }) =>
                `fp-header__link${isActive ? ' is-active' : ''}`
              }
            >
              <Plus size={16} aria-hidden="true" />
              <span>New test</span>
            </NavLink>
            <NavLink
              to="/log"
              aria-label="Log"
              className={({ isActive }) =>
                `fp-header__link${isActive ? ' is-active' : ''}`
              }
            >
              <ScrollText size={16} aria-hidden="true" />
              <span>Log</span>
            </NavLink>
            <NavLink
              to="/verify"
              aria-label="Verify"
              className={({ isActive }) =>
                `fp-header__link${isActive ? ' is-active' : ''}`
              }
            >
              <ShieldCheck size={16} aria-hidden="true" />
              <span>Verify</span>
            </NavLink>
            <button
              type="button"
              className="fp-icon-btn"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
              title="Toggle theme"
            >
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            {user ? (
              <span className="fp-header__user" title={user.full_name || user.username}>
                <span className="fp-header__user-name">{user.username}</span>
                <span className="fp-header__user-role">{user.role}</span>
              </span>
            ) : null}
            <button
              type="button"
              className="fp-icon-btn"
              onClick={onLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={18} />
            </button>
          </nav>
        </div>
      </header>
      <main className="fp-container fp-main">{children}</main>
    </div>
  )
}

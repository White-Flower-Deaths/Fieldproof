import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, getStoredToken, storeToken } from '../lib/api'
import type { AuthUser } from '../lib/api'
import { AuthContext } from './auth-context'
import type { AuthContextValue } from './auth-context'

const USER_KEY = 'fieldproof.user'

function readStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

function writeStoredUser(user: AuthUser | null): void {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(USER_KEY)
  } catch {
    /* storage unavailable */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())
  // No stored token -> session checks are already done on the first render.
  const [ready, setReady] = useState<boolean>(() => !getStoredToken())

  // Validate any stored token once on boot; drop it if the server rejects it.
  useEffect(() => {
    const token = getStoredToken()
    if (!token) return
    let cancelled = false
    api
      .me()
      .then((me) => {
        if (cancelled) return
        setUser(me)
        writeStoredUser(me)
      })
      .catch(() => {
        if (cancelled) return
        storeToken(null)
        writeStoredUser(null)
        setUser(null)
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password)
    storeToken(res.access_token)
    setUser(res.user)
    writeStoredUser(res.user)
  }, [])

  const register = useCallback(async (username: string, password: string) => {
    const res = await api.register(username, password)
    storeToken(res.access_token)
    setUser(res.user)
    writeStoredUser(res.user)
  }, [])

  const logout = useCallback(() => {
    storeToken(null)
    writeStoredUser(null)
    setUser(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, ready, login, register, logout }),
    [user, ready, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

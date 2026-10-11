import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { useAuth } from './auth/auth-context'
import { AppShell, BackdropArt, LoadingBlock } from './components'
import DesignPage from './design/DesignPage'
import AnalysisResultPage from './pages/AnalysisResultPage'
import DashboardPage from './pages/DashboardPage'
import LogPage from './pages/LogPage'
import LoginPage from './pages/LoginPage'
import NewTestWizard from './pages/NewTestWizard'
import SignupPage from './pages/SignupPage'
import VerifyPage from './pages/VerifyPage'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <LoadingBlock label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <>{children}</>
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth()
  if (!ready) return <LoadingBlock label="Checking your session…" />
  if (user) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <BackdropArt />
        <Routes>
          <Route
            path="/login"
            element={
              <PublicOnly>
                <LoginPage />
              </PublicOnly>
            }
          />
          <Route
            path="/signup"
            element={
              <PublicOnly>
                <SignupPage />
              </PublicOnly>
            }
          />
          <Route path="/design" element={<DesignPage />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <AppShell>
                  <DashboardPage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/new-test"
            element={
              <RequireAuth>
                <AppShell>
                  <NewTestWizard />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/samples/:id/analysis"
            element={
              <RequireAuth>
                <AppShell>
                  <AnalysisResultPage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/log"
            element={
              <RequireAuth>
                <AppShell>
                  <LogPage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route
            path="/verify"
            element={
              <RequireAuth>
                <AppShell>
                  <VerifyPage />
                </AppShell>
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

import { useState } from 'react'
import type { FormEvent } from 'react'
import { LogIn } from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/auth-context'
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  Logo,
  TextField,
} from '../components'
import './pages.css'

export default function LoginPage() {
  const { user, ready, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (ready && user) return <Navigate to="/" replace />

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fp-shell">
      <div className="fp-container fp-auth">
        <aside className="fp-auth__panel" aria-label="About FieldProof">
          <span className="fp-auth__panel-stripe" aria-hidden="true" />
          <div>
            <p className="fp-auth__panel-title">FieldProof</p>
            <p className="fp-auth__panel-tag">
              Explainable colourimetric field testing with tamper-evident records.
            </p>
          </div>
          <ul className="fp-auth__panel-specs">
            <li>
              <span>Records</span>
              <b>ECDSA P-256 + SHA-256 chain</b>
            </li>
            <li>
              <span>Colour</span>
              <b>sRGB to CIELAB, CIEDE2000</b>
            </li>
            <li>
              <span>Analysis</span>
              <b>Explainable scoring engine</b>
            </li>
            <li>
              <span>Result</span>
              <b>Presumptive only</b>
            </li>
          </ul>
          <p className="fp-auth__panel-foot">
            Not a substitute for laboratory confirmation.
          </p>
        </aside>
        <div className="fp-auth__card">
          <div className="fp-auth__brand">
            <Logo tagline="signed field test records" />
          </div>
          <Card raised>
            <CardHeader title="Operator sign-in" subtitle="Records are signed with your account." />
            <CardBody>
              <form className="fp-auth__form" onSubmit={onSubmit} noValidate>
                {error ? <Alert tone="danger" title="Sign-in failed">{error}</Alert> : null}
                <TextField
                  label="Operator ID"
                  name="username"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
                <TextField
                  label="Password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <Button type="submit" size="lg" fullWidth loading={submitting} iconBefore={<LogIn size={18} />}>
                  Sign in
                </Button>
              </form>

              <p className="fp-auth__switch">
                No account yet? <Link to="/signup">Create one</Link>
              </p>

              <details className="fp-auth__demo">
                <summary>Demo accounts</summary>
                <ul className="fp-auth__demo-list">
                  <li>
                    <code>officer1 / FieldProof#Demo1</code> — officer
                  </li>
                  <li>
                    <code>officer2 / FieldProof#Demo2</code> — officer
                  </li>
                  <li>
                    <code>lab1 / FieldProof#Lab1</code> — laboratory
                  </li>
                  <li>
                    <code>admin / FieldProof#Admin1</code> — administrator
                  </li>
                </ul>
              </details>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
